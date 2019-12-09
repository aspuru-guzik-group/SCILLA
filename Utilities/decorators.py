#!/usr/bin/env python 

#========================================================================

import time

from multiprocessing import Process
from threading       import Thread

#========================================================================

def delayed(time_delay = 1.0):
	def decorator_wrapper(function):
		def wrapper(*args, **kwargs):
			time.sleep(time_delay)
			function(*args, **kwargs)
		return wrapper
	return decorator_wrapper

#========================================================================

def process(function):
	def wrapper(*args, **kwargs):
		background_process = Process(target = function, args = args, kwargs = kwargs)
		background_process.start()
	return wrapper

def thread(function):
	def wrapper(*args, **kwargs):
		background_thread = Thread(target = function, args = args, kwargs = kwargs)
		background_thread.start()
	return wrapper

#========================================================================
