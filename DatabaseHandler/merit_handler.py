#!/usr/bin/env python 

#====================================================

import uuid
import numpy as np 

from DatabaseHandler import DB_Werkzeug

#====================================================

class MeritHandler(DB_Werkzeug):

	DB_ATTRIBUTES = {'merit_id':     'string',
			 'merit_value':  'pickle',
			 'measurements': 'pickle',}

	ALL_MERITS    = {}

	def __init__(self, db_settings):
		DB_Werkzeug.__init__(self)
		self.create_database(db_settings, self.DB_ATTRIBUTES)


	def add_losses_for_invalid_circuits(self, n_iter = 1):
			
		print('***************************************************')
		print('***************************************************')
		print('***************************************************')
		print('ADDING', n_iter, '\n'*5)

		info_dicts = []
		for x_iter in range(n_iter):
			merit_id = str(uuid.uuid4())
			info_dict = {'merit_id': merit_id, 'merit_value': np.nan}
			info_dicts.append(info_dict)
			self.ALL_MERITS[merit_id] = {'merit_id': merit_id, 'merit_value': np.nan, 'measurements': np.nan}
		self.db_add(info_dicts)


	def add_losses_for_circuits(self, circuits):

		print('#####################################')
		print('#####################################')
		print('#####################################')
		print('ADDING', len(circuits))

		info_dicts = []
		for circuit in circuits:
			merit_id = str(uuid.uuid4())
			info_dict = {'merit_id': merit_id, 'merit_value': {'loss': circuit['loss']}, 'measurements': circuit['measurements']}
			info_dicts.append(info_dict)
			self.ALL_MERITS[merit_id] = {'merit_id': merit_id, 'merit_value': {'loss': circuit['loss']}, 'measurements': circuit['measurements']}
		self.db_add(info_dicts)
		return info_dicts


	def select_merits(self, merit_ids):
		try:
			merits = [self.ALL_MERITS[merit_id] for merit_id in merit_ids]
		except KeyError:
			return self.db_fetch_all({'merit_id': merit_ids})
		return merits
