#!/usr/bin/env python 

#====================================================

import uuid
import numpy as np 
import pickle
import threading
import time

from Designers import AbstractDesigner
from Utilities.decorators import thread, delayed

#====================================================

class RandomDesigner(AbstractDesigner):
	
	batch_size = 1

	def __init__(self, general_settings, param_settings, options, *args, **kwargs):
		# likely that we need to pass variable settings to designers
		AbstractDesigner.__init__(self, general_settings, param_settings, options)

		# random search never requests new tasks
		self.OPTIMIZERS_FINISHED = True


	@thread
	@delayed(0.1)
	def _draw_circuit(self, condition_file):

		drawn_circuits = []
		for batch_iteration in range(self.batch_size):

			circuit = self._design_random_circuit()
			drawn_circuits.append(circuit)

		with open(condition_file, 'wb') as content:
			pickle.dump(drawn_circuits, content)


	def submit(self, *args, **kwargs):
		return self._submit(**kwargs)
