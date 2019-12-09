#!/usr/bin/env python 

# Multi-step workflow for 4-local coupler search

import numpy as np
import time
import pickle

from circuit_searcher import CircuitSearcher


if __name__ == '__main__':
	"""
		Set parameters and run the inverse design algorithm.
		Note 1: Task names are assumed to be unique.
		Note 2: The JJcircuitSim circuit simulation module is *not* included on the SCILLA GitHub repo.
	"""

	# Simulation of 3-node circuits (using JJcircuitSim V3.6e)
	c_specs        = {'dimension': 6, 'low': 1.,  'high': 100.,  'keep_prob': 0.5}
	j_specs        = {'dimension': 6, 'low': 99., 'high': 1982., 'keep_num':  3}
	l_specs        = {'dimension': 6, 'low': 75., 'high': 300.,  'keep_prob': 0.5}
	phiOffs_specs  = {'dimension': 4, 'values': [0.0, 0.5]}
	circuit_params = {'c_specs': c_specs, 'j_specs': j_specs, 'l_specs': l_specs, 'phiOffs_specs': phiOffs_specs}
	general_params = {'solver': 'JJcircuitSimV3', 'phiExt': None, 'target_spectrum': None}

	# Loss function settings
	dw_options       = {'max_peak': 1.5, 'max_split': 10, 'norm_p': 4, 'flux_sens': True, 'max_merit': 100}

	# Initialize circuit searcher
	circuit_searcher = CircuitSearcher(circuit_params, general_params, database_path = 'Experiments')

	# Monte Carlo optimization
	mc_options       = {'max_iters': 3, 'max_concurrent': 2, 'batch_size': 10}
	computing_task_0 = circuit_searcher.add_task(
							name ='random_search', 
							designer='random', designer_options=mc_options, 
							merit='DoubleWell', merit_options=dw_options)
	
	# Filtering for best circuits
	filtering_task_0 = circuit_searcher.add_task(name = 'filtering', designer = 'filter_db', designer_options = {'num_circuits': 2})

	# Swarm optimization
	swarm_options    = {'max_iters': 2, 'max_concurrent': 2, 'n_particles': 2}
	computing_task_2 = circuit_searcher.add_task(
	 						name='swarm_search', 
	 						designer='particle_swarms', designer_options=swarm_options, 
	 						merit='DoubleWell', merit_options=dw_options, use_library=True)

	tic_glob = time.time()
	circuit_searcher.execute()
	print('#### TOTAL TIME: {} s ####'.format(time.time()-tic_glob))


















