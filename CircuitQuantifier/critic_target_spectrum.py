#!/usr/bin/env python 

import numpy as np 


def merit_TargetSpectrum(circuit, merit_options, circuit_params = {}):

	# Calculated and target spectrum
	spectrum   = np.array(circuit['measurements']['eigen_spectrum'])
	targetspec = np.array(merit_options['target_spectrum'])

	# Calculate loss from mean square of spectra difference
	loss_flux = np.mean((spectrum[:,1:3]-targetspec[:,1:3])**2)
	loss = loss_flux

	# Symmetry enforcement for 2-node circuits without linear inductances
	if merit_options['include_symmetry']:
		Carr_norm = (circuit['circuit']['circuit_values']['capacities'] - circuit_params['c_specs']['low']) / circuit_params['c_specs']['high']
		Jarr_norm = (circuit['circuit']['circuit_values']['junctions']  - circuit_params['j_specs']['low']) / circuit_params['j_specs']['high']
		Larr = circuit['circuit']['circuit_values']['inductances']
		if len(Carr_norm) == 3 and Larr == None:
			loss_symmetry = np.abs(Carr_norm[0] - Carr_norm[2]) + np.abs(Jarr_norm[0] - Jarr_norm[2])
			loss += 100 * loss_symmetry
		else:
			raise NotImplementedError("Symmetry loss only implemented for 2-node circuits without linear inductances")

	# Apply squashing function
	loss = np.log10(loss)
	
	merit_dict = {'loss': loss, 'extra_tasks': []}

	return merit_dict
