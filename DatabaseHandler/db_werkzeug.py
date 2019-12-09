#!/usr/bin/env python 

#========================================================================

import copy

from Utilities.decorators import thread

#========================================================================

class DB_Werkzeug(object):

	def __init__(self):
		pass


	def create_database(self, db_settings, db_attributes):
	
		self.db_settings   = db_settings
		self.db_attributes = db_attributes
		if db_settings.db_type == 'sqlite':
			from DatabaseHandler import SQLiteDatabase
			try:
				self.database = SQLiteDatabase(db_settings.db_path, db_attributes, db_settings.db_name)	
			except OSError:
				print('path to database %s does not exist:\n\t%s' % (db_settings.db_name, db_settings.db_path))
		else:
			print('database type %s for database %s unknown' % (db_settings.db_type, db_settings.db_name))
		

	def _get(self, condition):
		entries = self.db_fetch_all(condition)
		return entries


	def db_add(self, info_dict):
		try:
			self.database.add(info_dict)
		except AttributeError:
			info_dict_str = ''
			for key, item in info_dict.items():
				info_dict_str = '%s:\t%s\n' % (str(key), str(item))


	def db_fetch_all(self, condition_dict):		
		try:
			return self.database.fetch_all(condition_dict)
		except OSError:
			condition_dict_str = ''
			for key, item in condition_dict.items():
				condition_dict_str = '%s:\t%s\n' % (str(key), str(item))


	@thread
	def db_fetch_async(self, condition_dict):
		self.CACHE = None
		self.CACHE = self.database.fetch_all(condition_dict)		


	def collect_from_cache(self):
		while self.CACHE is None:
			pass
		cache = copy.deepcopy(self.CACHE)
		self.CACHE = None
		return cache


	def db_update_all(self, condition_dict, update_dict):
		try:
			self.database.update_all(condition_dict, update_dict)
		except OSError:
			condition_dict_str = ''
			for key, item in condition_dict.items():
				condition_dict_str = '%s:\t%s\n' % (str(key), str(item))

