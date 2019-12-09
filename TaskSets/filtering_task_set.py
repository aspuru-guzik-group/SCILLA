#!/usr/bin/env python 

from TaskSets import TaskSet 

#====================================================

class FilteringTaskSet(TaskSet):

	def __init__(self, settings):

		TaskSet.__init__(self, settings['name'])
		self.settings              = settings
		self.settings['task_type'] = 'filtering'
		self.task_type             = 'filtering'
		self.max_exec              = 1