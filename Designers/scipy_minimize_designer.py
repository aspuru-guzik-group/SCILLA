#!/usr/bin/env python 

#====================================================

import sys
import copy
import time
import uuid
import pickle
import threading
import numpy as np 

from scipy.optimize import minimize as sp_minimize

from Designers            import AbstractDesigner
from Utilities.decorators import thread, process, delayed

np.set_printoptions(precision = 3)

#====================================================

class ScipyMinimizeDesigner(AbstractDesigner):

	PROPOSED_CIRCUITS         = []
	RECEIVED_OBSERVATIONS     = {}
	TASK_ID_EXECUTION         = {}
	SCIPY_OPTIMIZERS_FINISHED = {}

	def __init__(self, general_settings, param_settings, options, method = 'L-BFGS-B', *args, **kwargs):

		AbstractDesigner.__init__(self, general_settings, param_settings, options)
		self.method               = method
		self.running_instance_ids = []
		self.sim_info_dicts       = {}


	def _create_loss_wrapper(self, sim_id, task_dict):

		def _loss_wrapper(x_squeezed):

			info_dict = self.sim_info_dicts[sim_id]			
			info_dict['num_executed'] += 1
			execution_index = info_dict['num_executed']
			current_task_id = info_dict['task_ids'][info_dict['task_id_index']]

			assert(info_dict['sim_id'] == sim_id)

			circuit = self._construct_dict_from_array(x_squeezed, info_dict)
			proposed_circuit_id = circuit['circuit_id']
			self.PROPOSED_CIRCUITS.append(circuit)

			start = time.time()
			loss  = np.inf
			while np.isinf(loss):
				# wait for response
				for wait_iter in range(10000): # corresponds to a maximum wait time of 100 s
					if proposed_circuit_id in self.RECEIVED_OBSERVATIONS:
						loss = self.RECEIVED_OBSERVATIONS[proposed_circuit_id]['loss']
						if np.isinf(loss):
							loss = 10**6
						del self.RECEIVED_OBSERVATIONS[proposed_circuit_id]
						break
					time.sleep(0.01)
				else:
					# submit circuit again in case we missed it
					self.PROPOSED_CIRCUITS.append(circuit)
					loss = 10**6
			end = time.time()
	
			if np.isnan(loss): loss = 10**6			

			# assemble new task - needed for any designer that spawns new task
			new_task                    = copy.deepcopy(task_dict[current_task_id])
			new_task['execution_index'] = execution_index
			new_task['primer_index']    = info_dict['observation_index']
			new_task['from_optimizer']  = True
			self.NEW_TASKS.append(new_task)

			return loss
		return _loss_wrapper


	def prepare_optimizer_instance(self, task_ids, observation_index, observation = None):
		
		# create initial position
		if observation:
			x_init, x_mask = self._construct_array_from_dict(observation)
		else:
			circuit        = self._design_random_circuit()
			x_init, x_mask = self._construct_array_from_dict(circuit)
		x_init_squeezed    = x_init[np.where(x_mask > 0.)[0]]

		# create bounds 
		bounds_squeezed   = self.bounds[np.where(x_mask > 0.)[0]]

		# assemble simulation
		sim_id = str(uuid.uuid4())
		sim_info_dict = {'x_init': x_init, 'x_init_squeezed': x_init_squeezed, 'x_mask': x_mask,
						 'bounds_squeezed': bounds_squeezed,
						 'sim_id': sim_id, 'task_id_index': 0,
						 'task_ids': task_ids, 'observation_index': observation_index, 'num_executed': 0}

		self.sim_info_dicts[sim_id] = copy.deepcopy(sim_info_dict)
		self.running_instance_ids.append(sim_info_dict)


	@thread
	def run_optimizer(self, loss_wrapper, sim_id, init_pos, bounds, max_iter, **kwargs):
		def local_callback(_):
			self.sim_info_dicts[sim_id]['task_id_index'] += 1
		res = sp_minimize(loss_wrapper, init_pos, method = self.method, bounds = bounds, options = {'maxiter': max_iter}, callback = local_callback)
		content = open('TIME_res_report', 'a')
		content.write('completed %s\n' % sim_id)
		for prop in dir(res):
			try:
				content.write('%s\t%s\n' % (prop, str(getattr(res, prop))))
			except:
				pass
		content.write('===============\n')
		content.close()
		self.SCIPY_OPTIMIZERS_FINISHED[sim_id] = True
		

	def initialize_optimizers(self, task_set, observations):
		print('# LOG | ... initializing {0} optimizer ({1}) ...'.format(self.method, len(observations)))
		settings = task_set.settings['designer_options']

		task_dict = {task['task_id']: task for task in task_set.generated_tasks}
		task_ids  = [task['task_id'] for task in task_set.generated_tasks]

		# generate optimizer for each observation
		if len(observations) == 0:
			self.prepare_optimizer_instance(task_ids, 0)
		else:
			for observation_index, observation in enumerate(observations):
				self.prepare_optimizer_instance(task_ids, observation_index, observation = observation)

		for sim_info_dict_index, sim_info_dict in enumerate(self.running_instance_ids):
			sim_id = sim_info_dict['sim_id']
			print('# LOG | ... starting {0} ({1}) {2} optimizer {3}'.format(sim_info_dict_index + 1, len(self.sim_info_dicts), self.method, sim_info_dict['observation_index']))

			# create loss wrapper and submit optimizer on separate thread
			loss_wrapper = self._create_loss_wrapper(sim_id, task_dict)

			self.SCIPY_OPTIMIZERS_FINISHED[sim_id] = False
			if 'init' in self.SCIPY_OPTIMIZERS_FINISHED:
				del self.SCIPY_OPTIMIZERS_FINISHED['init']
			self.run_optimizer(loss_wrapper, sim_id, sim_info_dict['x_init_squeezed'], sim_info_dict['bounds_squeezed'], settings['max_iters'])


	@thread 
	def _draw_circuit(self, condition_file, **kwargs):
		proposed_circuits = []
		copied_circuits = copy.deepcopy(self.PROPOSED_CIRCUITS)
		for copied_circuit in copied_circuits:
			proposed_circuits.append(self.PROPOSED_CIRCUITS.pop(0))
		if len(proposed_circuits) == 0:
			proposed_circuits = [{}]
		pickle.dump(proposed_circuits, open(condition_file, 'wb'))


	@thread 
	def _control_optimizers(self, task_set, observations):
		# check if optimizers are initialized
		
		if len(self.running_instance_ids) == 0:
			self.initialize_optimizers(task_set, observations)


	def submit(self, *args, **kwargs):
		task_set     = kwargs['task_set']
		observations = copy.deepcopy(kwargs['observations'])
		self._control_optimizers(task_set, observations)

		# get number of optimizers which have completed
		comp, not_comp = 0, 0
		for key, has_finished in self.SCIPY_OPTIMIZERS_FINISHED.items():
			if has_finished:
				comp += 1
			else:
				not_comp += 1

		return self._submit(*args, **kwargs)


#====================================================
