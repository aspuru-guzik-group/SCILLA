#!/usr/bin/env python 

__author__ = 'Florian Hase'

#========================================================================

import time
import sqlalchemy as sql

#========================================================================

class AddEntry(object):
		
	def __init__(self, database, table, entry):
		self.db    = database
		self.table = table
		self.entry = entry

	def execute(self):
		start = time.time()
		with self.db.connect() as conn:
			conn.execute(self.table.insert(), self.entry)
			conn.close()
		end = time.time()

#========================================================================

class FetchEntries(object):

	def __init__(self, database, table, selection, name = 'test'):
		self.db              = database
		self.table           = table
		self.selection       = selection
		self.entries         = None
		self.executed        = False
		self.entries_fetched = False 
		self.name            = name

	def execute(self):
		start = time.time()
		with self.db.connect() as conn:
			selected = conn.execute(self.selection)
			entries  = selected.fetchall()
			conn.close()
		self.entries  = entries
		self.executed = True
		end = time.time()

	def get_entries(self):
		iteration_index = 0
		while not self.executed:
			pass
		self.entries_fetched = True
		return self.entries

#========================================================================

class UpdateEntries(object):

	def __init__(self, database, table, updates):
		self.db      = database
		self.table   = table		
		self.updates = updates

	def execute(self):
		start = time.time()
		if isinstance(self.updates, list):
			with self.db.connect() as conn:
				for updates in self.updates:
					updated = conn.execute(updates)
				conn.close()
		else:

			with self.db.connect() as conn:
				updated = conn.execute(self.updates)
				conn.close()
		end = time.time()
