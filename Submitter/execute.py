#!/usr/bin/env python 

""" Executes the circuit solver wrapper """

import os
import sys 
import uuid
import pickle 
import shutil

sys.path.append(os.getcwd())

#====================================================

process_index = int(sys.argv[2])

#====================================================


job_id   = sys.argv[1].split('_')[-1].split('.')[0]

# Load information about circuit, solver, sweep

with open(sys.argv[1], 'rb') as content:
	data = pickle.load(content)

function         = data['evaluation_function']
general_params   = data['general_params']
solver           = general_params['solver']
phiExt           = general_params['phiExt']
params           = data['circuit']['circuit_values']
carr, jarr, larr = params['capacities'], params['junctions'], params['inductances']

# Pass flux offsets in other loops to simulator
phiOffs_bool = False
if 'phiOffs' in params:
	phiOffs_bool = True
	phiOffs = params['phiOffs']

# Navigate into scratch directory before calling function
scratch_dir = '.scratch_dir_%s' % str(uuid.uuid4())
os.mkdir(scratch_dir)
os.chdir(scratch_dir)

# Circuit solver wrapper is called here
if phiOffs_bool:
	result_dict = function(solver, carr, larr, jarr, phiExt=phiExt, phiOffs=phiOffs)
else:
	result_dict = function(solver, carr, larr, jarr, phiExt=phiExt)
os.chdir('../')

data['results']  = result_dict
data['measurements'] = {'eigen_spectrum': data['results'][0], 'timeout': data['results'][1]}

# Save number of flux biases and maximum outer level pop if that information is available
if len(result_dict)==4:
	data['measurements']['num_biases'] = data['results'][2]
	data['measurements']['max_pop'] = data['results'][3]

processed_file_name = sys.argv[1].replace(job_id, 'proc_%s' % job_id)

with open(processed_file_name, 'wb') as content:
	pickle.dump(data, content)

# Clean up 
try:
	shutil.rmtree(scratch_dir)
except:
	pass










