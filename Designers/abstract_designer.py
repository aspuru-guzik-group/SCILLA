#!/usr/bin/env python 

#====================================================

import uuid

import numpy as np

#====================================================

# Factor to account for intrinsic junction capacitance
CJFACTOR = 0 #junction capacitance is added automatically in simulation code

class AbstractDesigner(object):
		
	def __init__(self, general_settings, param_settings, options):
		self.busy = False
		self.general         = general_settings
		self.param_settings  = param_settings
		self.c_specs         = self.param_settings['c_specs']
		self.j_specs         = self.param_settings['j_specs']
		self.l_specs         = self.param_settings['l_specs']
		self.phiOffs_specs = self.param_settings['phiOffs_specs']
		self.has_inductances = self.l_specs is not None

		# copy method specific options
		for key, value in options.items():
			setattr(self, key, value)
		self.options = options

		self.NEW_TASKS           = []
		self.OPTIMIZERS_FINISHED = False

		self.construct_bounds()


	def construct_bounds(self):
		# construct bounds for combined array (c, j, l)
		# CONVENTION: always report numbers in alphabetical order, i.e. c --> j --> l
		# No bounds added for inductors if 'l_specs' is set to None in param_settings

		self.bounds = []
		for specs in [self.c_specs, self.j_specs, self.l_specs]:
			if specs != None:
				dim = specs['dimension']
				# Case of 4-node circuit: add one element to account for forbidden connection
				if dim==9:
					dim += 1
				bounds = [(specs['low'], specs['high']) for _ in range(dim)]
				self.bounds += bounds
		self.bounds = np.array(self.bounds)


	def _construct_array_from_dict(self, obs_dict):

		# Get parameter arrays for junctions, capacitances, inductances
		try:
			j_arr = obs_dict['junctions']['samples']
			if self.has_inductances:
				l_arr = obs_dict['inductances']['samples']
			c_arr = obs_dict['capacities']['samples'] - j_arr * CJFACTOR
		except IndexError:
			j_arr = obs_dict['junctions']
			if self.has_inductances:
				l_arr = obs_dict['inductances']
			c_arr = obs_dict['capacities'] - j_arr * CJFACTOR

		# Make parameter array 
		if self.has_inductances:
			param = np.concatenate([c_arr, j_arr, l_arr])
		else:
			param = np.concatenate([c_arr, j_arr])
		mask  = np.ones(len(param))
		mask[np.where(np.abs(param) < 1e-4)[0]] *= 0.
		return param, mask


	def _construct_dict_from_array(self, param, info_dict):
		param_vect = np.zeros(len(info_dict['x_init']))
		param_vect[np.where(info_dict['x_mask'] > 0.)[0]] = param 
		if self.has_inductances:
			k = len(param_vect) // 3
			c_arr  = param_vect[:k]
			j_arr  = param_vect[k : 2*k]
			l_arr  = param_vect[2 * k:]
		else:
			k = len(param_vect) // 2
			c_arr  = param_vect[:k]
			j_arr  = param_vect[k:]
			l_arr  = None
		c_arr += j_arr * CJFACTOR
		circuit = {'junctions': j_arr, 'capacities': c_arr, 'inductances': l_arr, 
				   'sim_id': info_dict['sim_id'], 'task_id_index': info_dict['task_id_index'], 'circuit_id': str(uuid.uuid4())}
		if 'phiOffs' in info_dict:
			circuit['phiOffs'] = info_dict['phiOffs']
		return circuit


	def _design_random_circuit(self):

		mask      = np.ones(self.j_specs['dimension'])
		indices   = np.arange(len(mask))
		np.random.shuffle(indices)
		mask[indices[:self.j_specs['dimension']-self.j_specs['keep_num']]] *= 0.

		# Draw junctions
		junctions  = np.random.uniform(self.j_specs['low'], self.j_specs['high'], self.j_specs['dimension'])
		junctions *= mask
		# Case of 4-node circuit: add zero at forbidden connection 2-4
		if self.j_specs['dimension']==9:
			junctions = np.insert(junctions, 6, 0)

		# Draw capacitances
		capacities  = np.random.uniform(self.c_specs['low'], self.c_specs['high'], self.c_specs['dimension'])
		capacities  = capacities * (np.random.uniform(0., 1., self.c_specs['dimension']) < self.c_specs['keep_prob'])
		# Case of 4-node circuit: add zero at forbidden connection 2-4
		if self.c_specs['dimension']==9:
			capacities = np.insert(capacities, 6, 0)
		capacities += junctions * CJFACTOR

		# Draw inductances
		if self.l_specs != None:
			inductances  = np.random.uniform(self.l_specs['low'], self.l_specs['high'], self.l_specs['dimension'])
			inductances  = inductances * (np.random.uniform(0., 1., self.l_specs['dimension']) < self.l_specs['keep_prob'])
			# Case of 4-node circuit: add zero at forbidden connection 2-4
			if self.l_specs['dimension']==9:
				inductances = np.insert(inductances, 6, 0)
			inductances[junctions > 0] = 0.
		else:
			inductances = None

		# draw flux offsets for loops
		if self.phiOffs_specs is not None:
			phiOffs = np.random.choice(self.phiOffs_specs['values'], self.phiOffs_specs['dimension'])
		else:
			phiOffs = None

		circuit = {'junctions': junctions, 'capacities': capacities, 'inductances': inductances, 'phiOffs': phiOffs}
		return circuit


	def is_busy(self):
		return self.busy

	def set_busy(self):
		self.busy = True

	def set_available(self):
		self.busy = False

	def _draw_circuit(self):
		pass


	def _submit(self, *args, **kwargs):
		job_id = kwargs['job_id']
		condition_file = '%s/conditions_%s.pkl' % (self.general.scratch_dir, job_id)
		self._draw_circuit(condition_file)
		return condition_file