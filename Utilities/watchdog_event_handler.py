#!/usr/bin/env python 

#==============================================================

from watchdog.observers import Observer
from watchdog.events    import PatternMatchingEventHandler

#==============================================================

class FileHandler(PatternMatchingEventHandler):

	def __init__(self, event, pattern):
		PatternMatchingEventHandler.__init__(self, patterns = [pattern])
		self.process_event = event

	def process(self, found_file):
		file_name = found_file.src_path
		self.process_event(file_name)

	def on_created(self, found_file):
		self.process(found_file)


class FileEventHandler(object):
	
	def __init__(self, event, pattern):
		self.event   = event
		self.pattern = pattern
		self.event_handler = FileHandler(event, pattern)

	def stream(self, path):
		self.observer = Observer()
		self.observer.schedule(self.event_handler, path, recursive = True)
		self.observer.start()

	def stop(self):
		self.observer.stop()

