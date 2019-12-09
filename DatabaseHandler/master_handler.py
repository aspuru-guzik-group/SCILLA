#!/usr/bin/env python 

#====================================================

import time

from DatabaseHandler import DB_Werkzeug

#====================================================

class MasterHandler(DB_Werkzeug):

	DB_ATTRIBUTES = {'task_set_id':     'string',
					 'task_id':         'string',
					 'circuit_id':      'string',
					 'merit_id':        'string',
					 'primer_index':    'integer',
					 'execution_index': 'integer',
					 'interest_score': 'string'}

	LINKED_LOSSES_AND_CIRCUITS = {}

	def __init__(self, db_settings):

		DB_Werkzeug.__init__(self)
		self.MASTER_DICT = {key: [] for key in self.DB_ATTRIBUTES}
		self.num_dict_entries = 0
		self.create_database(db_settings, self.DB_ATTRIBUTES)
		self.dict_busy = False


	def dict_add(self, info_dicts):
		self.dict_busy = True
		if not isinstance(info_dicts, list):
			info_dicts = [info_dicts]
		for info_dict in info_dicts:
			for key in self.DB_ATTRIBUTES:
				if key in info_dict: 
					self.MASTER_DICT[key].append(info_dict[key])
				else:
					self.MASTER_DICT[key].append(None)
			self.num_dict_entries += 1
		self.dict_busy = False


	def dict_update_all(self, conditions, updates):
		self.dict_busy = True

		if not isinstance(conditions, list):
			conditions = [conditions]
			updates    = [updates]

		for index in range(self.num_dict_entries):
			for condition_index, condition in enumerate(conditions):
				update = updates[condition_index]
				for cond_key, cond_value in condition.items():
					if self.MASTER_DICT[cond_key][index] != cond_value:
						break
				else:
					for up_key, up_value in update.items():
						self.MASTER_DICT[up_key][index] = up_value
		self.dict_busy = False


	def get(self, condition):
		# attempt a recovery from the dictionary
		self.dict_busy = True
		return_dicts   = []
		for entry_index in range(self.num_dict_entries):
			
			if len(condition) == 0:
				return_dict = {key: self.MASTER_DICT[key][entry_index] for key in self.DB_ATTRIBUTES}
				return_dicts.append(return_dict)
				continue

			for cond_key, cond_value in condition.items():
				if not self.MASTER_DICT[cond_key][entry_index] in cond_value:
					break
			else:
				return_dict = {key: self.MASTER_DICT[key][entry_index] for key in self.DB_ATTRIBUTES}
				return_dicts.append(return_dict)

		self.dict_busy = False
		return return_dicts

	#======================================================


	def add_tasks(self, info_dicts):
		for info_dict in info_dicts:
			info_dict['interest_score'] = 'n/a'
		self.dict_add(info_dicts)
		self.db_add(info_dicts)


	def add_invalid_circuit(self, circuit_id, loss_id):
		info_dict = {'circuit_id': circuit_id, 'loss_id': loss_id, 'interest_score': 'invalid'}
		self.dict_add(info_dict)
		self.db_add(info_dict)
		self.LINKED_LOSSES_AND_CIRCUITS[circuit['circuit_id']] = [None, loss_id]


	def add_invalid_circuits(self, circuit_ids, loss_ids):
		info_dicts = []
		for circuit_index, circuit_id in enumerate(circuit_ids):
			try:
				loss_id = loss_ids[circuit_index]
			except TypeError:
				continue
			info_dict = {'circuit_id': circuit_id, 'loss_id': loss_id, 'interest_score': 'invalid'}
			info_dicts.append(info_dict)
		self.dict_add(info_dicts)
		self.db_add(info_dicts)


	def link_submission(self, task, circuit):
		condition = {key: task[key] for key in ['task_id', 'primer_index', 'execution_index']}
		while len(self.db_fetch_all(condition)) == 0:
			time.sleep(0.01)
		_ = self.db_fetch_all(condition)[0]
		update    = {'circuit_id': circuit['circuit_id']}
		self.dict_update_all(condition, update)
		self.db_update_all(condition, update)


	def link_submissions(self, tasks, circuits):

		conditions, updates = [], []
		for task_index, task in enumerate(tasks):
			circuit = circuits[task_index]
			condition = {key: task[key] for key in ['task_id', 'primer_index', 'execution_index']}
			update    = {'circuit_id': circuit['circuit_id']}
			conditions.append(condition)
			updates.append(update)

			self.LINKED_LOSSES_AND_CIRCUITS[circuit['circuit_id']] = [task['task_set_id'], None]

		self.dict_update_all(conditions, updates)
		self.db_update_all(conditions, updates)


	def link_losses_to_circuits(self, circuits, merits):
		conditions, updates = [], []
		for circuit_index, circuit in enumerate(circuits):
			merit = merits[circuit_index]
			condition = {'circuit_id': circuit['circuit_id']}
			update    = {'merit_id':   merit['merit_id']}
			conditions.append(condition)
			updates.append(update)

			self.LINKED_LOSSES_AND_CIRCUITS[circuit['circuit_id']][1] = merit['merit_id']

		self.dict_update_all(conditions, updates)
		self.db_update_all(conditions, updates)


	def get_linked_losses_and_circuits(self, task_set_id):
		identifier_sets = []
		for circuit_id, values in self.LINKED_LOSSES_AND_CIRCUITS.items():
			if values[0] == task_set_id:
				identifier_sets.append({'circuit_id': circuit_id, 'merit_id': values[1]})
		return identifier_sets


	def label_relevant(self, info_dict):
		condition = {'merit_id': info_dict['merit_id']}
		update    = {'interest_score': 'relevant'}
		self.dict_update_all(condition, update)
		self.db_update_all(condition, update)


	def label_irrelevant(self, info_dict):
		condition = {'merit_id': info_dict['merit_id']}
		update    = {'interest_score': 'irrelevant'}
		self.dict_update_all(condition, update)
		self.db_update_all(condition, update)
