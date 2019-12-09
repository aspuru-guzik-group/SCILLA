#!/usr/bin/env python 

from TaskSets import TaskSet 

#====================================================

class CalculationTaskSet(TaskSet):

	def __init__(self, settings):

		TaskSet.__init__(self, settings['name'])
		self.settings              = settings
		self.settings['task_type'] = 'calculation'
		self.task_type             = 'calculation'
		self.max_exec              = self.settings['designer_options']['max_iters']