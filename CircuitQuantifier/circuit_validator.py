#!/usr/bin/env python 

#====================================================

import copy
import threading
import numpy as np 
import time

from Utilities.decorators import thread

#====================================================

class CircuitValidator(object):

	VALIDATED_CIRCUITS = []

	def __init__(self):
		pass


	@thread
	def run_validation(self, circuit):
		start = time.time()

		capacities = circuit['circuit_values']['capacities']

		k = len(capacities)
		n = int(np.sqrt(2 * k + 0.25) - 0.5)

		c_mat_mf = np.zeros((n, n))
		c_mat_mf[np.triu_indices(n, k = 0)] = capacities
		c_mat_mf = np.maximum(c_mat_mf, c_mat_mf.transpose())

		c_mat_modified  = np.diag(np.sum(c_mat_mf, axis = 0))
		c_mat_modified += np.diag(np.diag(c_mat_mf)) - c_mat_mf

		determinant = np.abs(np.linalg.det(c_mat_modified))
		if determinant > 10**-6:
			circuit['is_valid'] = True
		else:
			circuit['is_valid'] = False

		self.VALIDATED_CIRCUITS.append(circuit)


	def validate_circuits(self, circuits):
		start = time.time()
		for circuit in circuits:
			self.run_validation(circuit)
		end = time.time()
		content = open('TIME_validations', 'a')
		content.write('%.5f\t%d\n' % (end - start, len(circuits)))
		content.close()


	def get_validated_circuits(self):
		validated_circuits = copy.deepcopy(self.VALIDATED_CIRCUITS)
		for circuit in validated_circuits:
			self.VALIDATED_CIRCUITS.pop(0)
		return validated_circuits
