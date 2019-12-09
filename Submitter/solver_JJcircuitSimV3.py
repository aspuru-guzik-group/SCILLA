#!/usr/bin/env python 

""" Wrapper to run the JJcircuitSim code in a Mathematica subprocess """

from subprocess import run, TimeoutExpired
import os
import time
import csv
import numpy as np
import re


def solver_JJcircuitSimV3(Carr, Larr, JJarr, nLin=6, nNol=8, nJos=11, nIsl=1, timeout=600, fluxSweep=True, phiOffs=[0.5,0.5,0.5,0.5]):
	"""
		Returns:
		eigenspec - 10-dim numpy array of the circuit eigenspectrum at fixed flux. If fluxSweep=True,
		returns a 10x41-dim array with flux sweep of each eigenmode (first flux bias chosen if multiple
		biases available).
		timeout_bool - flag for expired timeout
		Only returned if it can be determined:
			num_biases - number of flux biases available in circuit

		Parameters:
		Carr - flattened upper triangular of capacitance matrix [fF]
		Larr - flattened upper triangular of inductance matrix [pH]
		JJarr - flattened upper triangular of Josephson junction matrix [GHz]
		nLin, nNol, nJos, nIsl - truncation of linear, non-linear, Josephson and island modes
		timeout - timeout for Mathematica simulation in seconds
		fluxBool - perform flux sweep if set to True

		Note: The components matrices are entered as 1-dim numpy arrays stepping through the
		upper triangular matrix row-wise, e.g. np.array([c11, c12, c13, c22, c23, c33])
	"""

	print('Running circuit simulation...')

	tA = time.time()

	timeout_bool = False

	tstart = time.time()

	# Write parameters to text file, for Mathematica to read
	Carr.astype('float32').tofile('Carr.dat')
	Larr.astype('float32').tofile('Larr.dat')
	JJarr.astype('float32').tofile('JJarr.dat')
	phiOffs = np.array(phiOffs)
	phiOffs.astype('float32').tofile('phiOffs.dat') #flux biases for loops

	# Subprocess to run Mathematica script
	try:
		run(["wolframscript", "-file", "../Mathematica_scriptV2-JJsimV3.wl",
			str(nLin), str(nNol), str(nJos), str(nIsl), str(int(fluxSweep))],
			timeout=timeout, stdout=open(os.devnull, 'wb'))
	except TimeoutExpired:
		print('ERROR: timeout expired')
		timeout_bool = True
		return None, timeout_bool

	# Extract eigenspectrum from file
	eigenspec = []
	if not os.path.isfile('log_eigenspectrum.csv'):
		return None, timeout_bool

	try: #try opening and reading spectrum file
		with open('log_eigenspectrum.csv', 'r') as datafile:
			if fluxSweep:
				reader = csv.reader(datafile, delimiter=',')
				for row in reader:
					eigenspec.append([float(e) for e in row])
			else:
				for n, line in enumerate(datafile):
					eigenspec.append(float(line.strip()))
	except AttributeError:
		return None, timeout_bool

	# Determine number of flux biases and outermost level population
	try:
		## Number of flux biases ##
		with open('log_biasinfo.txt', 'r') as datafile:
			content = datafile.read()
		start_indices = [m.start() for m in re.finditer('Fb', content)]
		matches = [content[i:i+3] for i in start_indices] #assumes no more than 9 biases
		matches = list(set(matches))
		num_biases = len(matches)
		print('# Found {} flux biases'.format(num_biases))

		## Maximum outermost level population of eigenstates ##
		with open('log_diagonalization.txt', 'r') as datafile:
			content = datafile.read()
		# Find indices of level pop information for each mode
		start_indices = np.array([m.start() for m in re.finditer('Max level probs', content)])
		stop_temp     = np.array([m.start() for m in re.finditer('}', content)])
		stop_indices  = np.array([np.min([t for t in stop_temp-s if t>0])+s for s in start_indices])
		# Extract level pops and convert to float
		levelpops = []
		for s,t in zip(start_indices,stop_indices):
			l = content[s+19:t]
			pattern = re.compile('\*\^')
			l = pattern.sub('e', l)
			l = l.split(',')
			l = [float(e) for e in l]
			levelpops.append(l)
		# Determine maximum outermost level pop overall
		max_pop = np.max([np.max(l) for l in levelpops])
		print('# Maximum outermost level pop: {}'.format(max_pop))

		print('Simulation time: {} s'.format(time.time()-tA))
		return eigenspec, timeout_bool, num_biases, max_pop

	except:
		print('ERROR: could not determine number of flux biases or outermost level population')
		print('Simulation time: {} s'.format(time.time()-tA))
		return eigenspec, timeout_bool

















