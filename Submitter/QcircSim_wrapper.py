#!/usr/bin/env python 

""" Submits simulation job to desired solver and returns simulation results """

# Import available circuit solvers
from Submitter import solver_JJcircuitSim
from Submitter import solver_JJcircuitSimV3
from Submitter import solver_2node

def solve_circuit(solver, Carr, Larr, Jarr, phiExt=0, phiOffs=[0.5,0.5,0.5]):

	if solver == 'JJcircuitSimV3':
		results = solver_JJcircuitSimV3(Carr, Larr, Jarr, fluxSweep=True, phiOffs=phiOffs)

	elif solver == '2-node':
		# Larr must be None
		eigenspec = solver_2node(Carr, Larr, Jarr, phiExt=phiExt, qExt=[0,0], n=6, normalized=True)
		timeout_bool = False
		results = (eigenspec, timeout_bool) 

	else:
		raise NotImplementedError("Desired circuit solver '{}' not implemented".format(solver))

	return results
