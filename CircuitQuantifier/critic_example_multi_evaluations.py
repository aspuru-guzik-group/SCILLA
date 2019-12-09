#!/usr/bin/env python 

import copy
import numpy as np 


def merit_TwoEvalExample(circuit_dict, merit_options, **kwargs):

	merit_dict = {'extra_tasks': []}

	if 'context_circuits' in kwargs:
		rmsd = 0.
		context_circuits = kwargs['context_circuits']
		for context_circuit in context_circuits:
			context_spectrum = context_circuit['measurements']['eigen_spectrum']

			dev   = context_spectrum - circuit_dict['measurements']['eigen_spectrum']
			rmsd += np.sqrt(np.mean(np.square(dev)))

		merit_dict['loss'] = rmsd

	else:
		perturbed_circuit = copy.deepcopy(circuit_dict)
		perturbed_circuit['general_params']['phiExt'] += 0.1

		merit_dict['extra_tasks'].append(perturbed_circuit)

	return merit_dict