#!/usr/bin/env python 

#====================================================

from DatabaseHandler import DB_Werkzeug

#====================================================

class TaskHandler(DB_Werkzeug):

	DB_ATTRIBUTES = {'designer':           'string',
					 'designer_options':   'pickle',
					 'from_optimizer':     'bool',
					 'observations':       'pickle', 
					 'use_library':        'bool',
					 'computing_resource': 'string',
					 'computing_options':  'pickle',
					 'task_id':            'string',
					 'task_set_id':        'string',
					 'task_set_name':      'string',
					 'task_status':        'string',
					 'task_type':          'string',
					 'primer_index':       'integer',
					 'execution_index':    'integer',}

	TASK_SETS_COMPLETED         = {}
	TASK_SETS_COMPLETED_CHANGED = {}
	TASK_SETS_REMAINING         = {}
	TASK_SETS_REMAINING_CHANGED = {}
	NOT_YET_COMPLETED           = {}

	def __init__(self, db_settings):

		DB_Werkzeug.__init__(self)
		self.create_database(db_settings, self.DB_ATTRIBUTES)
		self.REMAINING_TASKS = {}
		self.COUNTER = {'statuses': 0, 'new': 0, 'submitted': 0, 'computed': 0, 'completed': 0}

	#====================================================================

	def refresh(self):
		self.COUNTER = {'statuses': 0, 'new': 0, 'submitted': 0, 'computed': 0, 'completed': 0}


	def add_tasks(self, info_dicts):
		for info_dict in info_dicts:
			info_dict['task_status'] = 'new'
			if not 'from_optimizer' in info_dict:
				info_dict['from_optimizer'] = False
			try:
				self.REMAINING_TASKS[info_dict['task_set_id']].append(info_dict)
				self.NOT_YET_COMPLETED[info_dict['task_set_id']].append(info_dict)
			except KeyError:
				self.REMAINING_TASKS[info_dict['task_set_id']] = [info_dict]
				self.NOT_YET_COMPLETED[info_dict['task_set_id']] = [info_dict]
			self.TASK_SETS_REMAINING_CHANGED[info_dict['task_set_id']] = True
			self.COUNTER['statuses'] += 1
			self.COUNTER['new'] += 1
		self.db_add(info_dicts)


	def fetch_remaining_tasks(self, task_set_id):
		try:
			return self.REMAINING_TASKS[task_set_id]
		except KeyError:
			condition = {'task_set_id': task_set_id, 'task_status': 'new'}
			entries   = self.db_fetch_all(condition)
			return entries


	def task_set_completed(self, task_set_id):
		return len(self.NOT_YET_COMPLETED[task_set_id]) == 0


	#====================================================================

	def report_circuit_submission(self):
		self.COUNTER['submitted'] += 1


	def report_circuit_computation(self):
		self.COUNTER['submitted'] -= 1	
	

	def set_tasks_to_submitted(self, tasks):
		conditions = []
		updates    = []
		for task in tasks:
			condition = {key: task[key] for key in ['task_id', 'primer_index', 'execution_index']}
			update    = {'task_status': 'submitted'}
			conditions.append(condition)
			updates.append(update)
			self.TASK_SETS_REMAINING_CHANGED[task['task_set_id']] = True
			self.COUNTER['new'] -= 1
			self.COUNTER['submitted'] += 1

			remaining_tasks = self.REMAINING_TASKS[task['task_set_id']]
			for index, info_dict in enumerate(remaining_tasks):
				identical = True
				for key in ['task_id', 'primer_index', 'execution_index']:
					identical = identical and info_dict[key] == task[key]
				if identical:
					del self.REMAINING_TASKS[task['task_set_id']][index]
					break

		self.db_update_all(conditions, updates)


	def set_tasks_to_redundant(self, tasks):
		conditions = []
		updates    = []
		for task in tasks:
			condition = {key: task[key] for key in ['task_id', 'primer_index', 'execution_index']}
			update    = {'task_status': 'redundant'}
			conditions.append(condition)
			updates.append(update)
			self.TASK_SETS_REMAINING_CHANGED[task['task_set_id']] = True
			self.TASK_SETS_COMPLETED_CHANGED[task['task_set_id']] = True

			remaining_tasks = self.REMAINING_TASKS[task['task_set_id']]
			for index, info_dict in enumerate(remaining_tasks):
				identical = True
				for key in ['task_id', 'primer_index', 'execution_index']:
					identical = identical and info_dict[key] == task[key]
				if identical:
					del self.REMAINING_TASKS[task['task_set_id']][index]
					break

			not_yet_completed_tasks = self.NOT_YET_COMPLETED[task['task_set_id']]
			for index, info_dict in enumerate(not_yet_completed_tasks):
				identical = True
				for key in ['task_id', 'primer_index', 'execution_index']:
					identical = identical and info_dict[key] == task[key]
				if identical:
					del self.NOT_YET_COMPLETED[task['task_set_id']][index]
					break

		self.db_update_all(conditions, updates)


	def set_tasks_to_computed(self, tasks):
		conditions = []
		updates    = []
		for task in tasks:
			condition = {key: task[key] for key in ['task_id', 'primer_index', 'execution_index']}
			update    = {'task_status': 'computed'}
			conditions.append(condition)
			updates.append(update)
			self.TASK_SETS_REMAINING_CHANGED[task['task_set_id']] = True
			self.COUNTER['submitted'] -= 1
			self.COUNTER['computed'] += 1
		self.db_update_all(conditions, updates)


	def set_tasks_to_completed(self, tasks):
		conditions = []
		updates    = []
		for task in tasks:
			condition = {key: task[key] for key in ['task_id', 'primer_index', 'execution_index']}
			update    = {'task_status': 'completed'}
			conditions.append(condition)
			updates.append(update)
			self.TASK_SETS_REMAINING_CHANGED[task['task_set_id']] = True
			self.TASK_SETS_COMPLETED_CHANGED[task['task_set_id']] = True
			self.COUNTER['computed'] -= 1
			self.COUNTER['completed'] += 1

			not_yet_completed_tasks = self.NOT_YET_COMPLETED[task['task_set_id']]
			for index, info_dict in enumerate(not_yet_completed_tasks):
				identical = True
				for key in ['task_id', 'primer_index', 'execution_index']:
					identical = identical and info_dict[key] == task[key]
				if identical:
					del self.NOT_YET_COMPLETED[task['task_set_id']][index]
					break

		self.db_update_all(conditions, updates)

	#====================================================================

	def check_resource_availability(self, info_dict):
		# get number of running jobs
		condition = {'task_set_id': info_dict['task_set_id'], 'task_status': 'submitted'}
		entries   = self.db_fetch_all(condition)
		return len(entries) < info_dict['designer_options']['max_concurrent']

	def get_num_available_resources(self, task_set):
		info_dict = task_set.generated_tasks[0]
		return info_dict['designer_options']['max_concurrent'] - self.COUNTER['submitted']
