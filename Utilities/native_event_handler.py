#!/usr/bin/env python 


#==============================================================

import os
import time
import uuid
import fnmatch

from Utilities.decorators import thread, process

#==============================================================

class FileEventHandler(object):

	def __init__(self, action, pattern):
		self.pattern = pattern
		self.action  = action
		self.stopped = True
		self.ident   = str(uuid.uuid4())[:8]

	@thread
	def execute(self, found_file):
		self.action(found_file)

	@thread
	def stream(self, path):
		executed_matches = []
		self.run         = True
		self.stopped     = False
		while True:
			matches = []
			for root, dir_name, file_names in os.walk(path):
				for file_name in fnmatch.filter(file_names, self.pattern):
					matches.append(os.path.join(root, file_name))
			for match in matches:
				if match in executed_matches: continue
				time.sleep(0.005)
				executed_matches.append(match)
				self.execute(match)
			if not self.run: break
		self.stopped = True

	def stop(self):
		self.run = False
		while not self.stopped:
			time.sleep(0.05)

