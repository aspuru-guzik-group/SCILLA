#!/usr/bin/env python 

""" Simulate Hamiltonian of 2-node circuits with arbitrary capacitances and junctions """

import numpy as np 
import numpy.linalg
import scipy as sp
import csv
import os


def solver_2node(Carr, Larr, Jarr, phiExt=0, qExt=[0,0], n=40, normalized=True):
	"""
		Calculates flux or charge spectrum of 2-node circuit containing junctions and capacitances. If
		flux or charge offset is given as a list, a sweep over the list will be performed. However, only
		one-dimensional sweeps are allowed. Returns eigenvalues for fixed parameters if no sweep specifid.

		Parameters:
			Carr: array                 | flattened capacitance matrix (in fF)
			Jarr: array                 | flattened junction matrix (in GHz)
			Larr: None                  | NOT SUPPORTED, SET TO 'None'
			phiExt: float or m-dim list | external flux (in fraction of flux quanta)
			qExt: 2-dim or 2xm-dim list | charge offsets for nodes 1 and 2 (in fraction of Cooper pairs)
			n: int                      | sets 2n+1 charge basis states (integer)

		Returns:
			spec: mxn-dim array | Eigenvalues of circuit for each point along sweep (in GHz)

		Note: Only one sweep allowed, i.e. sweep either flux or one of the two node charges.
	"""

	import time
	start = time.time()

	# Determine which parameter to sweep
	sweep_phi = (np.shape(phiExt) != ())
	sweep_q1 = (np.shape(qExt[0]) != ())
	sweep_q2 = (np.shape(qExt[1]) != ())

	# Check whether more than one sweep is specified
	sweep_list = [sweep_phi, sweep_q1, sweep_q2]
	valid = (len([s for s in sweep_list if s==True]) <= 1)
	assert valid, "Only one sweep allowed - sweep either flux OR one of the two node charges."

	# Initialize spectrum
	spec = []

	# Calculate spectrum for swept parameter
	if sweep_phi:
		for p in phiExt:
			spec.append( _eigs_2node_singleflux(Carr, Larr, Jarr, phiExt_fix=p, qExt_fix=qExt, n=n) )
	elif sweep_q1 or sweep_q2:
		if sweep_q1:
			qSweep = [[q,qExt[1]] for q in qExt[0]]
		else:
			qSweep = [[qExt[0],q] for q in qExt[1]]
		for qv in qSweep:
			spec.append( _eigs_2node_singleflux(Carr, Larr, Jarr, phiExt_fix=phiExt, qExt_fix=qv, n=n) )
	else:
		spec = _eigs_2node_singleflux(Carr, Larr, Jarr, phiExt_fix=phiExt, qExt_fix=qExt, n=n)

	spec = np.array(spec)

	# Normalize spectrum by ground state if desired
	if normalized:
		e0 = np.array([spec[i][0] for i in range(len(spec))])
		spec = (spec.T - e0).T

	end = time.time()
	new_line= '$$$$$ took: %.4f s $$$$$$$\n' % (end - start)
	return spec


def _eigs_2node_singleflux(Carr, Larr, Jarr, phiExt_fix=0, qExt_fix=[0,0], n=6):
	"""
		Eigenenergies of 2-node circuit containing capacitances and junctions for fixed flux and charge
		offset. Note: Adds junction capacitance.

		Parameters:
			Carr: array            | flattened capacitance matrix (in fF)
			Jarr: array            | flattened junction matrix (in GHz)
			Larr: None             | NOT YET SUPPORTED, SET TO 'None'
			phiExt_fix: float      | external flux (in fraction of flux quanta)
			qExt_fix:  2-dim array | charge offset vector for nodes 1 and 2 (in fraction of Cooper pairs)
			n: int                 | sets 2n+1 charge basis states (integer)

		Returns:
			evals: array | 2n+1 eigenvalues of circuit (in GHz)
	"""

	assert Larr==None, "Linear inductors not supported in 2-node solver - set Larr to 'None'"

	# Construct component connectivity matrices
	N = int((np.sqrt(1+8*len(Carr))-1)/2) #calculate dimension of matrices from number of upper triagonal entries
	Cmat, Jmat = np.zeros((N,N)), np.zeros((N,N))
	Cmat[np.triu_indices(N,k=0)] = Carr
	Cmat = np.maximum(Cmat, Cmat.transpose())
	Jmat[np.triu_indices(N,k=0)] = Jarr
	Jmat = np.maximum(Jmat, Jmat.transpose())
	Cmat += 1/26.6 * Jmat #add junction capacitance

	# Capacitance matrix C (not to be confused with Capacitance connectivity matrix Cmat)
	C = np.diag(np.sum(Cmat, axis=0)) + np.diag(np.diag(Cmat)) - Cmat
	C = C * 10.**(-15) #convert fF -> F

	# Capacitive (kinetic) part of Hamiltonian
	e = 1.60217662 * 10**(-19) #elementary charge
	h = 6.62607004 * 10**(-34) #Planck constant
	T = np.zeros( ((2*n+1)**len(C), (2*n+1)**len(C)) ) #kinetic part of Hamiltonian
	Cinv = np.linalg.inv(C)
	I = np.eye(2*n+1) #identity matrix
	Q = np.diag(np.arange(-n,n+1)) #Charge operator
	Q1 = Q + qExt_fix[0]*I
	Q2 = Q + qExt_fix[1]*I
	# More simple construction specific to flux qubit
	T += 0.5*Cinv[0,0] * np.kron(Q1.dot(Q1), I)
	T += 0.5*Cinv[1,1] * np.kron(I, Q2.dot(Q2))
	T += Cinv[0,1] * np.kron(Q1, Q2)
	T *= 4*e**2/h

	# Josephson potential part (specific to flux qubit)
	Jmat = Jmat * 10.**9 #convert GHz -> Hz
	U = np.zeros(((2*n+1)**len(C),(2*n+1)**len(C))) #potential part of Hamiltonian
	Dp = np.diag(np.ones((2*n+1)-1), k=1)
	Dm = np.diag(np.ones((2*n+1)-1), k=-1)
	# Add displacement operator terms that were obtained from cosines
	U = U - Jmat[0,0]/2 * np.kron((Dp + Dm),I)
	U = U - Jmat[1,1]/2 * np.kron(I, (Dp + Dm))
	U = U - Jmat[0,1]/2 * ( np.exp(-2*np.pi*1j*phiExt_fix) * np.kron(Dp,Dm) + np.exp(2*np.pi*1j*phiExt_fix) * np.kron(Dm,Dp) )

	# Assemble Hamiltonian
	H = T + U

	evals = np.linalg.eigh(H)[0]
	evals /= 1e9 #convert to GHz

	return evals


####### Testing #######
if __name__=='__main__':

	from matplotlib import pyplot as plt

	# Initialization
	EJa = 115
	EJb = 115
	EJc = 50
	Csh = 45
	Jarr = np.array([EJa, EJc, EJb])
	Carr = np.array([0, Csh, 0])
	phiExt = np.linspace(0, 1, 25, endpoint=True)
	qSweep = np.linspace(0, 1, 25, endpoint=True)

	# Find eigenvalues
	res = solver_2node(Carr, None, Jarr, phiExt=phiExt, qExt=[0,0], n=10, normalized=True)
	print('Testing _eigs_2node_singleflux:', res[:,1])

	# Output
	plt.figure()
	plt.plot(res[:,1])
	plt.show()





























