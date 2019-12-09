#!/usr/bin/env python 

import os
import copy
import time
import uuid
import pickle

from Utilities import FileLogger
from Utilities.decorators import thread

#========================================================================

class CircuitDesigner(object):

	# declare containers

	ACTIVE_DESIGNERS      = {}
	FILE_LOGGERS          = {}
	OBSERVATION_CONTAINER = {}
	DESIGNED_CIRCUITS     = []

	def __init__(self, settings_general, settings_params):

		self.designers        = {}
		self.settings_general = settings_general
		self.settings_params  = settings_params


	def add_designer(self, name_id, keyword, options):
		if keyword == 'particle_swarms':
			from Designers import ParticleSwarmDesigner as SelectedDesigner
		elif keyword == 'scipy':
			from Designers import ScipyMinimizeDesigner as SelectedDesigner
		elif keyword == 'random':
			from Designers import RandomDesigner as SelectedDesigner
		else:
			raise NotImplementedError()

		if SelectedDesigner is None:
			print('# FATAL | ... could not import %s designer; please install the required package ...' % keyword)
			import sys
			sys.exit()

		self.designers[name_id] = SelectedDesigner(self.settings_general, self.settings_params, options, kind = keyword)


	def is_busy(self, task_set_dict):
		name_id = task_set_dict.settings['name']
		return self.designers[name_id].is_busy()


	def get_circuits(self):
		circuits = copy.deepcopy(self.DESIGNED_CIRCUITS)
		for circuit in circuits:
			self.DESIGNED_CIRCUITS.pop(0)
		return circuits


	def _parse_new_circuits(self, conditions_file):

		# for windows machines
		conditions_file = conditions_file.replace('\\', '/')

		# parse the job_id and stop file logger
		job_id = conditions_file.split('_')[-1].split('.')[0]
		self.FILE_LOGGERS[job_id].stop()

		# save conditions
		try:
			conditions = pickle.load(open(conditions_file, 'rb'))
		except EOFError:
			time.sleep(1)
			conditions = pickle.load(open(conditions_file, 'rb'))
		if len(conditions[0]) > 0:
			for condition in conditions:
				condition_dict = {'circuit_values': condition}
				self.DESIGNED_CIRCUITS.append(condition_dict)

		# clean up
		os.remove(conditions_file)
		self.designers[self.ACTIVE_DESIGNERS[job_id]].set_available()
		del self.ACTIVE_DESIGNERS[job_id]
		del self.FILE_LOGGERS[job_id]


	def get_requested_tasks(self, task_set):
		name_id  = task_set.settings['name']
		designer = self.designers[name_id]
		new_tasks = copy.deepcopy(designer.NEW_TASKS)
		for new_task in new_tasks:
			designer.NEW_TASKS.pop(0)
		return new_tasks


	@thread
	def provide_observations(self, task_set, observations): 
		self.OBSERVATION_CONTAINER[task_set.settings['name']] = observations
		designer = self.designers[task_set.settings['name']]
		for observation in observations:
			if not 'circuit_id' in observation: continue
			if isinstance(observation['circuit_id'], dict):
				observation['circuit_id'] = observation['circuit_id']['samples']
			designer.RECEIVED_OBSERVATIONS[observation['circuit_id']] = observation


	def designer_terminated(self, task_set):
		if hasattr(self.designers[task_set.settings['name']], 'SCIPY_OPTIMIZERS_FINISHED'):
			result = True
			for index, element in self.designers[task_set.settings['name']].SCIPY_OPTIMIZERS_FINISHED.items():
				result = result and element 
			return result
		if hasattr(self.designers[task_set.settings['name']], 'PS_OPTIMIZERS_FINISHED'):
			result = True
			for index, element in self.designers[task_set.settings['name']].PS_OPTIMIZERS_FINISHED.items():
				result = result and element 
			return result
		else:
			return self.designers[task_set.settings['name']].OPTIMIZERS_FINISHED


	@thread
	def design_new_circuits(self, task_set, observations = None, tasks = None):
		start = time.time()
		if observations: self.provide_observations(task_set, observations)

		# reserve designer
		name_id  = task_set.settings['name']
		designer = self.designers[name_id]
		designer.set_busy()

		# create circuit listener
		job_id      = str(uuid.uuid4())
		self.ACTIVE_DESIGNERS[job_id]   = name_id
		file_logger = FileLogger(action = self._parse_new_circuits, path = self.settings_general.scratch_dir, pattern = '*conditions*%s*' % job_id)
		self.FILE_LOGGERS[job_id]       = file_logger
		file_logger.start()

		# submit circuit
		conditions_file = designer.submit(job_id = job_id, task_set = task_set, observations = observations, tasks = tasks)

		end = time.time()
		content = open('TIME_design_submission', 'a')
		content.write('%.5f\t%d\n' % (end - start, len(observations)))
		content.close()
