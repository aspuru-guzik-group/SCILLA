#!/usr/bin/env python 

#====================================================

import uuid
import copy

from DatabaseHandler import DB_Werkzeug

#====================================================

class CircuitHandler(DB_Werkzeug):

	DB_ATTRIBUTES = {'circuit_id':       'string',
					 'circuit_status':   'string',
					 'circuit_values':   'pickle',
					 'is_valid':         'bool',
					 'context_circuits': 'pickle'}

	NEW_CIRCUITS       = {}
	VALIDATED_CIRCUITS = {}
	ALL_CIRCUITS       = {}

	def __init__(self, db_settings):

		DB_Werkzeug.__init__(self)
		self.create_database(db_settings, self.DB_ATTRIBUTES)


	def add_new_circuits(self, info_dicts):
		for info_dict in info_dicts:
			info_dict['circuit_id']     = str(uuid.uuid4())
			info_dict['circuit_status'] = 'new'
			info_dict['is_valid']       = False
			self.NEW_CIRCUITS[info_dict['circuit_id']] = info_dict
			self.ALL_CIRCUITS[info_dict['circuit_id']] = info_dict
		self.db_add(info_dicts)


	def get_new_circuits(self):
		return list(self.NEW_CIRCUITS.values())


	def get_validated_circuits(self):
		return list(self.VALIDATED_CIRCUITS.values())


	def select_circuits(self, circuit_ids):
		try:
			circuit = [self.ALL_CIRCUITS[circuit_id] for circuit_id in circuit_ids]
		except KeyError:
			return self.db_fetch_all({'circuit_id': circuit_ids})
		return circuit


	def reserve_circuits(self, info_dicts):
		conditions, updates = [], []
		for index, info_dict in enumerate(info_dicts):
			condition = {'circuit_id':     info_dict['circuit_id']}
			update    = {'circuit_status': 'processing'}
			conditions.append(condition)
			updates.append(update)
			del self.VALIDATED_CIRCUITS[info_dict['circuit_id']]
		self.db_update_all(conditions, updates)


	def release_circuits(self, info_dicts):
		conditions, updates = [], []
		for index, info_dict in enumerate(info_dicts):
			condition = {'circuit_id':     info_dict['circuit_id']}
			update    = {'circuit_status': 'validated'}
			conditions.append(condition)
			updates.append(update)
			self.VALIDATED_CIRCUITS[info_dict['circuit_id']] = info_dict
		self.db_update_all(conditions, updates)


	def set_circuits_to_unused(self):
		conditions = [{'circuit_status': 'validated'}, {'circuit_status': 'new'}]
		updates    = [{'circuit_status': 'unused'}, {'circuit_status': 'unused'}]
		self.NEW_CIRCUITS       = {}
		self.VALIDATED_CIRCUITS = {}
		self.db_update_all(conditions, updates)
		

	def store_validated_circuits(self, circuits):
		conditions, updates = [], []
		for circuit in circuits:
			condition = {'circuit_id': circuit['circuit_id']}
			update    = {'is_valid': circuit['is_valid'],
						 'circuit_status': 'validated'}
			conditions.append(condition)
			updates.append(update)

			try:
				del self.NEW_CIRCUITS[circuit['circuit_id']]
			except KeyError:
				pass

			if circuit['is_valid']:
				self.VALIDATED_CIRCUITS[circuit['circuit_id']] = circuit

		self.db_update_all(conditions, updates)


	def update_circuits_with_contexts(self, circuits):
		conditions, updates = [], []
		for circuit in circuits:
			condition = {'circuit_id': circuit['circuit']['circuit_id']}
			update    = {'context_circuits': circuit['context_circuits']}
			conditions.append(condition)
			updates.append(update)
		self.db_update_all(conditions, updates)
