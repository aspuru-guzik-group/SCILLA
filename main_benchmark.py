#!/usr/bin/env python

# Multi-step workflow for 2-node flux qubit benchmark

import numpy as np
import time
import pickle

from circuit_searcher import CircuitSearcher


if __name__ == '__main__':
	"""
		Set parameters and run the inverse design algorithm.

		general_params:
			solver: string         | specifies circuit solver - 'JJcircuitSim' or '2-node'
			phiExt: array		   | external fluxes for which to solve circuit
			target_spectrum: array | target flux spectrum of circuit (used by specific loss functions only)

		Note: Task names are assumed to be unique.
	"""

	# Python simulation of 2-node circuits
	c_specs         = {'dimension': 3, 'low': 0., 'high': 100, 'keep_prob': 1.}
	j_specs         = {'dimension': 3, 'low': 0., 'high': 200, 'keep_num':  3}
	circuit_params  = {'c_specs': c_specs, 'j_specs': j_specs, 'l_specs': None, 'phiOffs_specs': None}
	phiExt          = np.linspace(0,1,41,endpoint=True)
	general_params  = {'solver': '2-node', 'phiExt': phiExt}

	# Loss function settings
	with open('target_fluxqubit.p', 'rb') as content: target_info = pickle.load(content)
	ts_options = {'target_spectrum': target_info['spectrum'], 'include_symmetry': True}

	# Initialize circuit searcher
	circuit_searcher = CircuitSearcher(circuit_params, general_params, database_path = 'Experiments')

	# Monte Carlo (random) optimization
	mc_options       = {'max_iters': 6, 'max_concurrent': 2, 'batch_size': 10}
	computing_task_0 = circuit_searcher.add_task(
							name ='random_search', 
							designer='random', designer_options=mc_options, 
							merit='TargetSpectrum', merit_options=ts_options)
	
	# Filtering for best circuits
	filtering_task_0 = circuit_searcher.add_task(name = 'filtering', designer = 'filter_db', designer_options = {'num_circuits': 2})

	# L-BFGS-B optimization
	bfgs_options     = {'max_iters': 2, 'max_concurrent': 2}
	ts_options       = {'target_spectrum': target_info['spectrum'], 'include_symmetry': True}
	computing_task_2 = circuit_searcher.add_task(
							name='lbfgs', 
							designer='scipy', designer_options=bfgs_options, 
							merit='TargetSpectrum', merit_options=ts_options, use_library=True)

	tic_glob = time.time()
	circuit_searcher.execute()
	print('#### TOTAL TIME: {} s ####'.format(time.time()-tic_glob))


















