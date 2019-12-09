#!/usr/bin/env python 

import copy
import uuid

#====================================================

class TaskSet(object):

	def __init__(self, name):
		self.max_exec      = 1
		self.task_set_name = name
		self.task_set_id   = str(uuid.uuid4())


	def generate_all_tasks(self):
		tasks = []
		for single_exec in range(self.max_exec):
			info_dict = copy.deepcopy(self.settings)
			info_dict['task_set_id']     = self.task_set_id
			info_dict['task_set_name']   = self.task_set_name
			info_dict['task_id']         = str(uuid.uuid4())
			info_dict['execution_index'] = 0
			info_dict['primer_index']    = 0
			info_dict['num_exec']        = single_exec
			info_dict['from_optimizer']  = False
			tasks.append(info_dict)
		self.generated_tasks = copy.deepcopy(tasks)
		return tasks