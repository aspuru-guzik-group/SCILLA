#!/usr/bin/env python 

__author__ = 'Florian Hase'

#========================================================================

import uuid
import time
import copy
import sqlalchemy as sql

from DatabaseHandler  import AddEntry, FetchEntries, UpdateEntries
from Utilities.decorators import thread

#========================================================================

class SQLiteDatabase(object):

	SQLITE_COLUMNS = {'bool':    sql.Boolean(),
					  'float':   sql.Float(),
					  'integer': sql.Integer(),
					  'pickle':  sql.PickleType(),
					  'string':  sql.String(512),}

	def __init__(self, path, attributes, name = 'table', verbosity = 0):

		self.WRITING_REQUESTS = []
		self.READING_REQUESTS = {}
		self.UPDATE_REQUESTS  = []

		self.db_path              = 'sqlite:///%s' % path
		self.attributes           = attributes
		self.name                 = name

		# create database 
		self.db       = sql.create_engine(self.db_path)
		self.db.echo  = False		
		self.metadata = sql.MetaData(self.db)

		# create table in database
		self.table = sql.Table(self.name, self.metadata)
		for name, att_type in self.attributes.items():
			self.table.append_column(sql.Column(name, self.SQLITE_COLUMNS[att_type]))
		self.table.create(checkfirst = True)

		# start request processor
		self._process_requests()

	#====================================================================

	def _return_dict(function):
		def wrapper(self, *args, **kwargs):
			entries    = function(self, *args, **kwargs)
			info_dicts = [{key: entry[key] for key in self.attributes} for entry in entries]
			return info_dicts
		return wrapper

	#====================================================================

	@thread
	def _process_requests(self):
		self._processing_requests = True
		keep_processing           = True
		iteration_index           = 0
		while keep_processing:
			num_reading_requests = len(self.READING_REQUESTS)
			num_writing_requests = len(self.WRITING_REQUESTS)
			num_update_requests  = len(self.UPDATE_REQUESTS)

			iteration_index += 1

			# run all reading request
			request_keys = copy.deepcopy(list(self.READING_REQUESTS.keys()))
			for request_key in request_keys:
				if not self.READING_REQUESTS[request_key].executed:
					self.READING_REQUESTS[request_key].execute()
				
			# run all update requests
			with self.db.connect() as conn:

				# run all update requests
				for update_index in range(num_update_requests):
					update_request = self.UPDATE_REQUESTS.pop(0)
					if isinstance(update_request.updates, list):
						for update in update_request.updates:
							has_updated = False
							while not has_updated:
								try:
									updated = conn.execute(update)
									has_updated = True
								except sql.exc.OperationalError:
									time.sleep(0.1)
									updated = conn.execute(update)
					else:
						has_updated = False
						while not has_updated:
							try:
								updated = conn.execute(update_request.updates)
								has_updated = True
							except sql.exc.OperationalError:
								time.sleep(0.1)
								updated = conn.execute(update_request.updates)				

				# run all writing requests
				master_entry = []
				for writing_index in range(num_writing_requests):
					writing_request = self.WRITING_REQUESTS.pop(0)
					if isinstance(writing_request.entry, list):
						master_entry.extend(writing_request.entry)
					else:
						master_entry.append(writing_request.entry)
				has_updated = False
				while not has_updated:
					try:
						conn.execute(self.table.insert(), master_entry)
						has_updated = True
					except sql.exc.OperationalError:
						time.sleep(0.1)

				conn.close()

			# clean reading requests
			request_keys = copy.deepcopy(list(self.READING_REQUESTS.keys()))
			delete_keys  = []
			for request_key in request_keys:
				if self.READING_REQUESTS[request_key].entries_fetched:
					delete_keys.append(request_key)
			for request_key in delete_keys:
				del self.READING_REQUESTS[request_key]

			keep_processing = len(self.WRITING_REQUESTS) > 0 or len(self.UPDATE_REQUESTS) > 0 or len(self.READING_REQUESTS) > 0
		self._processing_requests = False

	#====================================================================


	def add(self, info_dict):
		if len(info_dict) == 0: return None
		
		add_entry = AddEntry(self.db, self.table, info_dict)
		self.WRITING_REQUESTS.append(add_entry)
		if not self._processing_requests:
			self._process_requests()
		

	@_return_dict
	def fetch_all(self, condition_dict):
		condition_keys   = list(condition_dict.keys())
		condition_values = list(condition_dict.values())

		# define the selection
		selection = sql.select([self.table])
		for index, key in enumerate(condition_keys):
			if isinstance(condition_values[index], list):
				# with a list, we need to combine all possibilities with _or
				if len(condition_values[index]) == 0:
					return []
				filters   = [getattr(self.table.c, key) == value for value in condition_values[index]]
				condition = sql.or_(*filters)
			else:
				condition = getattr(self.table.c, key) == condition_values[index]
			selection = selection.where(condition)

		fetch_entries = FetchEntries(self.db, self.table, selection, name = self.name)
		fetch_keys    = str(uuid.uuid4())
		self.READING_REQUESTS[fetch_keys] = fetch_entries
		if not self._processing_requests:
			self._process_requests()

		entries = fetch_entries.get_entries()
		return entries


	def update_all(self, condition_dict, update_dict):

		if isinstance(condition_dict, list):

			updates = []
			for cond_dict_index, cond_dict in enumerate(condition_dict):

				up_dict = update_dict[cond_dict_index]
				condition_keys   = list(cond_dict.keys())
				condition_values = list(cond_dict.values())

				update = sql.update(self.table).values(up_dict)
				for index, key in enumerate(condition_keys):
					update = update.where(getattr(self.table.c, key) == condition_values[index])
				updates.append(update)

		else:
			
			condition_keys   = list(condition_dict.keys())
			condition_values = list(condition_dict.values())

			update = sql.update(self.table).values(update_dict)
			for index, key in enumerate(condition_keys):
				update = update.where(getattr(self.table.c, key) == condition_values[index])
			updates = update

		# submitting the update
		update_entries = UpdateEntries(self.db, self.table, updates)
		self.UPDATE_REQUESTS.append(update_entries)
		if not self._processing_requests:
			self._process_requests()





