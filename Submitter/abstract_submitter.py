#!/usr/bin/env python 

import copy
import pickle 

#====================================================

class AbstractSubmitter(object):

	# submitter only computes the spectra / other properties of interest
	# there'll be another module computing the loss, which is done on the same computing architecure for now

	RECEIVED_RESULTS = []

	def __init__(self, settings, general_params, evaluation_function):
		self.settings            = settings
		self.general_params      = general_params
		self.evaluation_function = evaluation_function


	# implement file logger and pick ups
	def process_received_results(self, file_name):
	
		results = pickle.load(open(file_name, 'rb'))


	def _submit(self):
		# this is the actual submission procedure
		pass


	def submit(self):
		
		# first, we need to validate the circuit, then we submit
		if self.is_valid():
			loss = 0.
		else:
			loss = np.nan
		

	def get_results(self):
		results = copy.deepcopy(self.RECEIVED_RESULTS)
		for result in results:
			del self.RECEIVED_RESULTS[0]
		return results
	
