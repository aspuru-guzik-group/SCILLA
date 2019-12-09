#!/usr/bin/env python 

#==============================================================

import warnings

from Utilities.decorators import thread

#==============================================================

class FileLogger(object):

	def __init__(self, action, path = './', pattern = '*'):
		self.action  = action
		self.path    = path
		self.pattern = pattern

		with warnings.catch_warnings():
			warnings.filterwarnings('error')
			try:
#				from Utilities.watchdog_event_handler import FileEventHandler
				from Utilities.native_event_handler import FileEventHandler
			except Warning:
				print('WARNING: Watchdog module not working. Falling back to native event handler.')
				from Utilities.native_event_handler import FileEventHandler

		self.event_handler = FileEventHandler(action, self.pattern)

	def start(self):
		self.event_handler.stream(self.path)

	def stop(self):
		self.event_handler.stop()

#==============================================================

