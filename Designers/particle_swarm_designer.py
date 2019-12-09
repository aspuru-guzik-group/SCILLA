#!/usr/bin/env python 

#====================================================

import copy
import time
import uuid
import pickle
import threading
import numpy as np 
import pyswarms as ps

np.set_printoptions(precision = 3)

from Utilities.decorators import thread, process, delayed
from Designers            import AbstractDesigner

#====================================================

class ParticleSwarmDesigner(AbstractDesigner):

	PROPOSED_CIRCUITS      = []
	RECEIVED_OBSERVATIONS  = {}
	TASK_ID_EXECUTION      = {}
	PS_OPTIMIZERS_FINISHED = {}

	n_particles    = 2
	social_options = {'c1': 0.5, 'c2': 0.3, 'w': 0.9} 


	def __init__(self, general_settings, param_settings, options, *args, **kwargs):

		AbstractDesigner.__init__(self, general_settings, param_settings, options)
		self.running_instance_ids = []
		self.optimizers           = {}
		self.sim_info_dicts       = {}


	def _create_loss_wrapper(self, sim_id, task_dict):
		def _loss_wrapper(x_batch_squeezed):
			info_dict            = self.sim_info_dicts[sim_id]
			current_task_id      = info_dict['remaining_tasks'][0]
			proposed_circuit_ids = []

			# look at each point and broaden the parameters
			for x_index, x_squeezed in enumerate(x_batch_squeezed):
				circuit = self._construct_dict_from_array(x_squeezed, info_dict)
				proposed_circuit_ids.append(circuit['circuit_id'])
				self.PROPOSED_CIRCUITS.append(circuit)
				
				# assemble a new task
				if info_dict['observation_index'] > 0 or len(info_dict['remaining_tasks']) < 2 * len(task_dict) or True:
					new_task = copy.deepcopy(task_dict[current_task_id])
					new_task['execution_index'] = len(x_batch_squeezed) * len(info_dict['remaining_tasks']) + x_index
					new_task['primer_index']    = info_dict['observation_index']
					new_task['from_optimizer']  = True
					self.NEW_TASKS.append(new_task)

			info_dict['remaining_tasks'].pop(0)

			# catch losses
			loss_batch = np.zeros(len(proposed_circuit_ids)) - np.inf
			while len(np.where(loss_batch < -10**300)[0]) > 0.:

				for proposed_circuit_index, proposed_circuit_id in enumerate(proposed_circuit_ids):
					if proposed_circuit_id in self.RECEIVED_OBSERVATIONS:
						loss = self.RECEIVED_OBSERVATIONS[proposed_circuit_id]['loss']
						loss_batch[proposed_circuit_index] = loss
						del self.RECEIVED_OBSERVATIONS[proposed_circuit_id]

				loss_batch = np.where(np.isnan(loss_batch), 10**6, loss_batch)

			self.sim_info_dicts[sim_id]['task_id_index'] += 1
			return loss_batch
		return _loss_wrapper


	def prepare_optimizer_instance(self, task_ids, observation_index, observation = None):

		if observation:
			x_init, x_mask = self._construct_array_from_dict(observation)
			if 'phiOffs' in observation:
				phiOffs  = observation['phiOffs']['samples']
			else:
				phiOffs  = None
		else:
			circuit        = self._design_random_circuit()
			x_init, x_mask = self._construct_array_from_dict(circuit)
			if 'phiOffs' in circuit:
				phiOffs  = circuit['phiOffs']
			else:
				phiOffs  = None
		x_init_squeezed    = x_init[np.where(x_mask > 0.)[0]]

		# create bounds 
		bounds_squeezed   = self.bounds[np.where(x_mask > 0.)[0]]
		lower_squeezed    = np.array([bounds_squeezed[i][0] for i in range(len(bounds_squeezed))])
		upper_squeezed    = np.array([bounds_squeezed[i][1] for i in range(len(bounds_squeezed))])
		bounds_collection = (lower_squeezed, upper_squeezed)

		remaining_tasks = []
		for task_id in task_ids:
			remaining_tasks.extend([task_id, task_id])

		# assemble simulation
		sim_id = str(uuid.uuid4())
		sim_info_dict = {'x_init': x_init, 'x_init_squeezed': x_init_squeezed, 'x_mask': x_mask, 
						 'bounds_squeezed': bounds_squeezed, 'bounds_collection': bounds_collection,
						 'lower_squeezed': lower_squeezed, 'upper_squeezed': upper_squeezed, 
						 'sim_id': sim_id, 'observation_index': observation_index, 'task_id_index': 0,
						 'remaining_tasks': copy.deepcopy(remaining_tasks)}
		if phiOffs is not None:
			sim_info_dict['phiOffs'] = phiOffs
		self.sim_info_dicts[sim_id] = sim_info_dict
		self.running_instance_ids.append(sim_info_dict)


	# NOTE: This needs to be a thread, not a process (!)
	@thread
	def run_optimizer(self, optimizer, loss_wrapper, max_iter, sim_id, **kwargs):
		optimizer.optimize(loss_wrapper, iters = max_iter, verbose = 1, print_step = 1)
		self.PS_OPTIMIZERS_FINISHED[sim_id] = True


	def initialize_optimizers(self, task_set, observations):
		print('# LOG | ... initializing particle swarms optimizer (%d) ...' % len(observations))
		settings  = task_set.settings['designer_options']
		task_dict = {task['task_id']: task for task in task_set.generated_tasks}
		task_ids  = [task['task_id'] for task in task_set.generated_tasks]

		# generate one optimizer for each observation
		if len(observations) == 0:
			self.prepare_optimizer_instance(task_ids, 0)
		else:
			for observation_index, observation in enumerate(observations):
				self.prepare_optimizer_instance(task_ids, observation_index, observation = observation)

		for sim_info_dict_index, sim_info_dict in enumerate(self.running_instance_ids):
			sim_id = sim_info_dict['sim_id']
			print('# LOG | ... starting %d (%d) particle swarms optimizer' % (sim_info_dict_index + 1, len(self.sim_info_dicts)))

			init_pos = np.array([sim_info_dict['x_init_squeezed'] for i in range(self.n_particles)]) 

			# Perturb initial positions of particles (except keep first instance at sampled parameters)
			init_pos_mod     = np.copy(init_pos)
			init_pos_mod    += np.random.normal(0., 0.1 * (sim_info_dict['upper_squeezed'] - sim_info_dict['lower_squeezed']), size = init_pos.shape)
			init_pos_mod[0]  = init_pos[0]
			init_pos_mod     = np.minimum(init_pos_mod, sim_info_dict['upper_squeezed'])
			init_pos_mod     = np.maximum(init_pos_mod, sim_info_dict['lower_squeezed'])

			optimizer    = ps.single.GlobalBestPSO(n_particles = self.n_particles, dimensions = len(sim_info_dict['x_init_squeezed']),
								 				   options = self.social_options, bounds = sim_info_dict['bounds_collection'], init_pos = init_pos_mod)
			# create loss wrapper for optimizer
			loss_wrapper = self._create_loss_wrapper(sim_id, task_dict)

			self.PS_OPTIMIZERS_FINISHED[sim_id] = False
			if 'init' in self.PS_OPTIMIZERS_FINISHED:
				del self.PS_OPTIMIZERS_FINISHED['init']
			self.run_optimizer(optimizer, loss_wrapper, settings['max_iters'], sim_id)

			content = open('LOG', 'a')
			content.write('starting optimizer for %s (%d)\n' % (sim_id, len(self.running_instance_ids)))
			content.close()


	@thread
	def _draw_circuit(self, condition_file):
		if len(self.PROPOSED_CIRCUITS) > 0:
			proposed_circuit = self.PROPOSED_CIRCUITS.pop(0)
		else:
			proposed_circuit = {}
		pickle.dump([proposed_circuit], open(condition_file, 'wb'))


	@thread
	def _control_optimizers(self, task_set, observations):
		# check if optimizers are initialized
		if len(self.running_instance_ids) == 0:
			self.initialize_optimizers(task_set, observations)
		else:
			for observation in observations:
				if not 'circuit_id' in observation: continue
				if isinstance(observation['circuit_id'], dict):
					observation['circuit_id'] = observation['circuit_id']['samples']

				self.RECEIVED_OBSERVATIONS[observation['circuit_id']] = observation


	def submit(self, *args, **kwargs):
		task_set     = kwargs['task_set']
		observations = kwargs['observations']
		self._control_optimizers(task_set, observations)
		return self._submit(*args, **kwargs)


#====================================================



