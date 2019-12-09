#!/usr/bin/env python 

#====================================================

import copy
import uuid
import numpy as np 
import threading

from Utilities.decorators import thread

#====================================================

class CircuitCritic(object):

	def __init__(self, circuit_params):
		self.circuit_params             = circuit_params
		self.CRITICIZED_CIRCUITS        = []
		self.EXTRA_TASKS                = []
		self.RECEIVED_EXTRA_EVALUATIONS = {}

		import CircuitQuantifier.critics as critics
		self.merit_functions = {}
		for merit in dir(critics):
			if merit.startswith('__'): continue
			self.merit_functions[merit.split('_')[-1]] = getattr(critics, merit)

	##############################################################

	def report_reevaluations(self, circuits):
		for circuit in circuits:
			self.RECEIVED_EXTRA_EVALUATIONS[circuit['circuit']['circuit_id']] = circuit
		

	def run_merit_evaluation(self, merit_func, circuit_dict, merit_options, task):
		merit_eval_dict = merit_func(circuit_dict, merit_options, circuit_params = self.circuit_params)

		if len(merit_eval_dict['extra_tasks']) > 0:

			# check if the merit evaluation requests new tasks
			remaining_extra_circuit_ids     = []
			received_extra_task_evaluations = {}

			for extra_task in merit_eval_dict['extra_tasks']:
				# we need to modify the circuit_id of the proposed circuit parameters
				new_circuit_id = str(uuid.uuid4())
				extra_task['circuit']['circuit_id'] = new_circuit_id
				self.EXTRA_TASKS.append(extra_task)
				remaining_extra_circuit_ids.append(new_circuit_id)

			while len(received_extra_task_evaluations) < len(remaining_extra_circuit_ids):
				# check if we have any new evaluated circuits
				extra_circuit_ids = list(self.RECEIVED_EXTRA_EVALUATIONS.keys())
				for extra_circuit_id in extra_circuit_ids:
					# memorize received evaluations
					if extra_circuit_id in remaining_extra_circuit_ids:
						received_extra_task_evaluations[extra_circuit_id] = self.RECEIVED_EXTRA_EVALUATIONS[extra_circuit_id]
						del self.RECEIVED_EXTRA_EVALUATIONS[extra_circuit_id]


			# call evaluator again
			merit_eval_dict = merit_func(circuit_dict, merit_options, 
										 circuit_params = self.circuit_params,
										 context_circuits = received_extra_task_evaluations.values())

			circuit_dict['loss']             = merit_eval_dict['loss']
			circuit_dict['context_circuits'] = list(received_extra_task_evaluations.values())

		else:

			circuit_dict['loss'] = merit_eval_dict['loss']
			circuit_dict['context_circuits'] = None

		self.CRITICIZED_CIRCUITS.append([circuit_dict, task])

	##############################################################

	@thread
	def criticize_circuit(self, circuit, task_set, task):
		# circuit: dict       | information about circuit

		merit         = task_set.settings['merit']
		merit_options = task_set.settings['merit_options']

		# check if simulation timed out
		if 'PLACEHOLDER' in circuit['measurements']:
			loss = np.nan

		# use specified merit function to calculate loss
		else:

			if not merit in self.merit_functions:
				print('# ERROR | ... could not find merit function: %s' % merit)
				return None

			# merit function needs to be put on a separate thread in case it likes to launch new tasks
			merit_func = self.merit_functions[merit]
			self.run_merit_evaluation(merit_func, circuit, merit_options, task)


	def get_requested_tasks(self):
		new_tasks = copy.deepcopy(self.EXTRA_TASKS)
		for new_task in new_tasks:
			self.EXTRA_TASKS.pop(0)
		return new_tasks


	def criticize_circuits(self, circuits, task_set, tasks):
		for circuit_index, circuit in enumerate(circuits):
			self.criticize_circuit(circuit, task_set, tasks[circuit_index])


	def get_criticized_circuits(self):
		circuits = copy.deepcopy(self.CRITICIZED_CIRCUITS)
		for circuit in circuits:
			self.CRITICIZED_CIRCUITS.pop(0)
		return circuits


	def get_extra_tasks(self):
		circuits = copy.deepcopy(self.EXTRA_TASKS)
		for circuit in circuits:
			self.EXTRA_TASKS.pop(0)
		return circuits























