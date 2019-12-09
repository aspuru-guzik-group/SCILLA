#!/usr/bin/env python 

import time
import numpy as np 

#========================================================================

from DatabaseHandler import CircuitHandler
from DatabaseHandler import MeritHandler
from DatabaseHandler import MasterHandler
from DatabaseHandler import TaskHandler

from Utilities.decorators import thread

#========================================================================

class DatabaseHandler(object):

	CIRCUIT_EVALUATIONS         = {}
	CIRCUIT_EVALUATIONS_CHANGED = {}

	def __init__(self, db_settings, db_path):

		self.db_settings     = db_settings
		if not db_path is None:
			for db_prop in ['master', 'circuits', 'merits', 'tasks']:
				db_settings = getattr(self.db_settings, db_prop)
				db_settings.db_path = '%s/%s.db' % (db_path, db_prop)
				setattr(self.db_settings, db_prop, db_settings)

		self.circuit_handler = CircuitHandler(self.db_settings.circuits)
		self.master_handler  = MasterHandler(self.db_settings.master)
		self.merit_handler   = MeritHandler(self.db_settings.merits)
		self.task_handler    = TaskHandler(self.db_settings.tasks)

	#====================================================================

	def add_task(self, info_dict):
		self.task_handler.add_task(info_dict)
		master_entry = {key: info_dict[key] for key in ['task_id', 'task_set_id', 'primer_index', 'execution_index']}
		if 'condition_id' in info_dict:
			master_entry['condition_id'] = info_dict['condition_id']
		self.master_handler.add_task(info_dict)

	def add_tasks(self, info_dicts):
		master_entries = []
		for info_dict in info_dicts:
			master_entry = {key: info_dict[key] for key in ['task_id', 'task_set_id', 'primer_index', 'execution_index']}
			if 'condition_id' in info_dict:
				master_entry['condition_id'] = info_dict['condition_id']
			master_entries.append(master_entry)
		self.task_handler.add_tasks(info_dicts)
		self.master_handler.add_tasks(info_dicts)

	def fetch_remaining_tasks(self, task_set_id):
		return self.task_handler.fetch_remaining_tasks(task_set_id)

	def task_set_completed(self, task_set_id):
		return self.task_handler.task_set_completed(task_set_id)

	def report_circuit_submission(self):
		self.task_handler.report_circuit_submission()

	def report_circuit_computation(self):
		self.task_handler.report_circuit_computation()

	def set_tasks_to_submitted(self, tasks):
		self.task_handler.set_tasks_to_submitted(tasks)

	def set_tasks_to_redundant(self, task):
		return self.task_handler.set_tasks_to_redundant(task)

	def set_tasks_to_computed(self, circuits):
		circuit_ids = [circuit['circuit']['circuit_id'] for circuit in circuits]
		id_dicts    = self.master_handler.get({'circuit_id': circuit_ids})

		conditions = []
		for id_dict in id_dicts:
			condition  = {key: id_dict[key] for key in ['task_set_id', 'task_id', 'primer_index', 'execution_index']}
			conditions.append(condition)
		self.task_handler.set_tasks_to_computed(conditions)
		return id_dicts

	#==========================================f==========================

	def check_resource_availability(self, task_dict):
		return self.task_handler.check_resource_availability(task_dict)

	def get_num_available_resources(self, task_set):
		return self.task_handler.get_num_available_resources(task_set)

	#====================================================================

	def add_new_circuit(self, circuit):
		self.circuit_handler.add_new_circuit(circuit)

	def add_new_circuits(self, circuits):
		self.circuit_handler.add_new_circuits(circuits)

	def get_new_circuits(self):
		circuits = self.circuit_handler.get_new_circuits()
		return circuits

	def get_validated_circuits(self):
		circuits = self.circuit_handler.get_validated_circuits()
		return circuits

	def reserve_circuits(self, circuit_dicts):
		self.circuit_handler.reserve_circuits(circuit_dicts)

	def release_circuits(self, circuit_dicts):
		self.circuit_handler.release_circuits(circuit_dicts)

	def set_circuits_to_unused(self):
		self.circuit_handler.set_circuits_to_unused()

	#====================================================================

	def store_validated_circuits(self, circuits):
		valid_circuits = []
		for circuit in circuits:
			if circuit['is_valid']:
				valid_circuits.append(circuit)
		self.circuit_handler.store_validated_circuits(valid_circuits)

	def __OLD__store_validated_circuits(self, circuits):
		self.circuit_handler.store_validated_circuits(circuits)
		invalid_circuit_ids = []
		for circuit in circuits:
			if not circuit['is_valid']:
				invalid_circuit_ids.append(circuit['circuit_id'])
		if len(invalid_circuit_ids) > 0:
			loss_ids = self.merit_handler.add_losses_for_invalid_circuits(len(invalid_circuit_ids))
			self.master_handler.add_invalid_circuits(invalid_circuit_ids, loss_ids)

	#====================================================================

	def get_circuit_evaluations(self, task_set_id):

		# implement container to accelerate evaluation queries
		if not task_set_id in self.CIRCUIT_EVALUATIONS_CHANGED or self.CIRCUIT_EVALUATIONS_CHANGED[task_set_id]:
			self.CIRCUIT_EVALUATIONS_CHANGED[task_set_id] = False

			identifier_sets = self.master_handler.get_linked_losses_and_circuits(task_set_id)
			observations = []
			circuit_ids  = []
			merit_ids    = []
			for identifier_set in identifier_sets:
				circuit_id = identifier_set['circuit_id']
				merit_id   = identifier_set['merit_id']
				if circuit_id is None or merit_id is None: continue

				circuit_ids.append(circuit_id)
				merit_ids.append(merit_id)

			start = time.time()
			circuits = self.circuit_handler.select_circuits(circuit_ids)
			merits   = self.merit_handler.select_merits(merit_ids)

			for circuit_index, circuit in enumerate(circuits):
				merit = merits[circuit_index]

				observ_dict = {}
				for param_name, param_value in circuit['circuit_values'].items():
					observ_dict[param_name] = {'samples': param_value}
				for merit_name, merit_value in merit['merit_value'].items():
					observ_dict[merit_name] = merit_value
				observations.append(observ_dict)
			self.CIRCUIT_EVALUATIONS[task_set_id] = observations
			return observations
		else:
			return self.CIRCUIT_EVALUATIONS[task_set_id]

	def get_prior_circuit_evaluations(self):
		condition       = {'interest_score': 'relevant'}
		identifier_sets = self.master_handler.db_fetch_all(condition)
		observations = []
		for identifier_set in identifier_sets:
			circuit_id = identifier_set['circuit_id']
			merit_id   = identifier_set['merit_id']
			if circuit_id is None or merit_id is None: continue

			circuit = self.circuit_handler.db_fetch_all({'circuit_id': circuit_id})[0]
			merit   = self.merit_handler.db_fetch_all({'merit_id': merit_id})[0]

			observ_dict = {}
			for param_name, param_value in circuit['circuit_values'].items():
				observ_dict[param_name] = {'samples': param_value}
			for merit_name, merit_value in merit['merit_value'].items():
				observ_dict[merit_name] = merit_value
			observations.append(observ_dict)
		return observations

	#====================================================================

	def link_submissions(self, tasks, circuits):
		self.master_handler.link_submissions(tasks, circuits)

	#====================================================================

	def store_criticized_circuits(self, circuit_dicts, id_dicts = None):

		circuits    = [circuit_dict['circuit'] for circuit_dict in circuit_dicts]
		circuit_ids = [circuit['circuit_id'] for circuit in circuits]

		merits = self.merit_handler.add_losses_for_circuits(circuit_dicts)

		self.master_handler.link_losses_to_circuits(circuits, merits)
		self.circuit_handler.update_circuits_with_contexts(circuit_dicts)

		if id_dicts is None:
			id_dicts    = self.master_handler._get({'circuit_id': circuit_ids})
	
		conditions = []
		for id_dict in id_dicts:
			self.CIRCUIT_EVALUATIONS_CHANGED[id_dict['task_set_id']] = True 
			conditions.append({key: id_dict[key] for key in ['task_set_id', 'task_id', 'primer_index', 'execution_index']})
		self.task_handler.set_tasks_to_completed(conditions)

	#====================================================================

	def get_task_set_progress_info(self, task_set, run_time):
		
		counter       = self.task_handler.COUNTER
		statuses      = range(counter['statuses'])
		num_new       = counter['new']
		num_submitted = counter['submitted']
		num_computed  = counter['computed']
		num_completed = counter['completed']

		werkzeug = self.master_handler.database
		print('DB OPERATIONS: updates: %d, writes: %d, reads: %d' % (len(werkzeug.UPDATE_REQUESTS), len(werkzeug.WRITING_REQUESTS), len(werkzeug.READING_REQUESTS)))
	
		# progress string will consist of NUM_CHAR characters
		NUM_CHAR = 75

		progress_string = ''
		for index in range( int(NUM_CHAR * num_completed / len(statuses))):
			progress_string += '#'
		for index in range( int(NUM_CHAR * num_computed / len(statuses))):
			progress_string += '|'
		for index in range( int(NUM_CHAR * num_submitted / len(statuses))):
			progress_string += ':'
		for index in range( NUM_CHAR - len(progress_string)):
			progress_string += '.'

		counter = self.task_handler.COUNTER
		print(len(statuses), num_new, num_submitted, num_computed, num_completed, \
			  '(#statuses, #new, #submitted, #computed, #completed)')

		content = open('log_run_time', 'a')
		content.write('%.3f\t%d\n' % (run_time, num_completed))
		content.close()

		return progress_string


	#====================================================================

	def filter_for_best_performing(self, options):

		import time 

		start = time.time()
		all_entries = self.master_handler.get({})

		print('\n\n')
		print('LEN OF ALL ENTRIES', len(all_entries))
		print('... took', time.time() - start)
		print('\n\n')

		start = time.time()
		all_merits = self.merit_handler._get({})
		print('\n\n')
		print('LEN OF ALL MERITS', len(all_merits))
		print('... took', time.time() - start)
		print('\n\n')

		# get entries for which merit has been calculated
		relevant_entries = []
		for entry in all_entries:
			if not entry['interest_score'] == 'invalid':
				relevant_entries.append(entry)

		# collect merit_id
		merit_ids = [entry['merit_id'] for entry in relevant_entries]

		# get merits for merit_ids
		merits = []
		for merit_id in merit_ids:
			print('MERIT_ID', merit_id)
			start = time.time()
			if merit_id is None: continue
			try:
				merit_dict = self.merit_handler._get({'merit_id': merit_id})[0]
			except IndexError:
				time.sleep(1)
				merit_dict = self.merit_handler._get({'merit_id': merit_id})[0]
			merits.append(merit_dict['merit_value']['loss'])
			print('...', time.time() - start)
		merits = np.array(merits)

		print('\n\n')

		# select relevant merits
		sorting_indices    = np.argsort(merits)
		relevant_indices   = sorting_indices[:options['num_circuits']]
		irrelevant_indices = sorting_indices[options['num_circuits']:]

		for relevant_index in relevant_indices:
			self.master_handler.label_relevant(relevant_entries[relevant_index])

		for irrelevant_index in irrelevant_indices:
			self.master_handler.label_irrelevant(relevant_entries[irrelevant_index])

	#====================================================================

	# User queries

	def get_circuits_from_task(self, task):

		try:
			task_set_id = task.task_set_id
		except AttributeError:
			task_set_id = task['task_set_id']

		id_dicts_all = self.master_handler._get({'task_set_id': task_set_id})
		id_dicts = []
		for id_dict in id_dicts_all:
			if not id_dict['circuit_id'] is None and not id_dict['merit_id'] is None:
				id_dicts.append(id_dict)

		circuits_ids = [id_dict['circuit_id'] for id_dict in id_dicts]
		circuits     = self.circuit_handler._get({})
		circuits_raw = {circuit['circuit_id']: circuit for circuit in circuits}

		merit_ids    = [id_dict['merit_id'] for id_dict in id_dicts]
		merits       = self.merit_handler._get({})
		merits_raw   = {merit['merit_id']: merit for merit in merits}

		out_dicts = []
		i = -1
		j = 0 
		for id_dict in id_dicts:
			i += 1

			try:
				circuit = circuits_raw[id_dict['circuit_id']]
				merit   = merits_raw[id_dict['merit_id']]
			except KeyError:
				print('Circuit {0} \t| Diff {1} \t| FAILED GETTING CIRCUIT OR MERIT'.format(i, i-j))
				j = i
				continue

			out_dict = {'circuit': circuit, 'merit': merit}
			out_dicts.append(out_dict)
		return out_dicts


	def get_trajectories(self, task_set):
		try:
			task_set_id = task_set.task_set_id
		except AttributeError:
			task_set_id = task_set['task_set_id']


		id_dicts_all = self.master_handler._get({'task_set_id': task_set_id})
		id_dicts = []
		for id_dict in id_dicts_all:
			if not id_dict['circuit_id'] is None and not id_dict['merit_id'] is None:
				id_dicts.append(id_dict)

		circuit_ids  = [id_dict['circuit_id'] for id_dict in id_dicts]
		circuits     = self.circuit_handler._get({})
		circuits_raw = {circuit['circuit_id']: circuit for circuit in circuits}

		merit_ids  = [id_dict['merit_id'] for id_dict in id_dicts]
		merits     = self.merit_handler._get({})
		merits_raw = {merit['merit_id']: merit for merit in merits}

		# sort id_dicts by execution index
		trajs             = {}
		current_bests     = {}
		recorded_task_ids = {}
		recorded_exec_ids = {}
		for id_dict_index, id_dict in enumerate(id_dicts):

			try:
				circuit = circuits_raw[id_dict['circuit_id']]
				merit   = merits_raw[id_dict['merit_id']]
			except KeyError:
				print('!!', id_dict_index)
				continue

			if not 'sim_id' in circuit['circuit_values']: 
				circuit['circuit_values']['sim_id'] = 0
			if not 'task_id_index' in circuit['circuit_values']: 
				circuit['circuit_values']['task_id_index'] = 0

			sim_id        = circuit['circuit_values']['sim_id']
			task_id_index = circuit['circuit_values']['task_id_index']
			if not sim_id in trajs:
				trajs[sim_id]             = []
				current_bests[sim_id]     = np.inf
				recorded_task_ids[sim_id] = []
				recorded_exec_ids[sim_id] = []

			recorded_task_ids[sim_id].append(task_id_index)
			recorded_exec_ids[sim_id].append(id_dict['execution_index'])

			loss_value   = merit['merit_value']['loss']
			measurements = merit['measurements']
			current_bests[sim_id] = loss_value

			circuit_out_dict = {key: circuit[key] for key in ['circuit_id', 'circuit_values', 'context_circuits']}
			merit_out_dict   = {'merit_value': current_bests[sim_id], 'measurements': measurements}
			out_dict         = {'circuit': circuit_out_dict, 'merit': merit_out_dict}
			trajs[sim_id].append(out_dict)


		short_trajs = {key: [] for key in trajs.keys()}
		for key, values in trajs.items():

			max_task_id = -1
			collected_values = {}
			for index, element in enumerate(recorded_task_ids[key]):
				max_task_id = np.maximum(max_task_id, element)
				if not element in collected_values:
					collected_values[element] = []
				collected_values[element].append(values[index])

			for task_id in range(max_task_id + 1):
				try:
					current_values = collected_values[task_id]
				except:
					continue
				best_loss = np.inf 
				for value in current_values:
					if value['merit']['merit_value'] < best_loss:
						best_loss = value['merit']['merit_value']
						best_dict = value 
				short_trajs[key].append(best_dict)

		return short_trajs


	def get_lbfgs_trajectories(self, task_set):
		return self._get_trajectories(task_set)


	def get_particle_swarms_trajectories(self, task_set):
		return self._get_trajectories(task_set)


	def list_computing_tasks(self):
		tasks = self.task_handler._get({})
		task_sets = []
		task_names, task_ids = [], []
		for task in tasks:
			if task['task_set_name'] in task_names or task['task_set_id'] in task_ids: continue
			task = {'task_set_name': task['task_set_name'], 'task_set_id': task['task_set_id']}
			task_names.append(task['task_set_name'])
			task_ids.append(task['task_set_id'])
			task_sets.append(task)
		return task_sets


	def refresh(self):
		self.task_handler.refresh()


	#====================================================================

	def is_updating(self, db = 'master'):
		if db == 'master':
			werkzeug = self.master_handler.database
			# print('FOUND UPDATES', len(werkzeug.UPDATE_REQUESTS))
			# print('FOUND WRITES', len(werkzeug.WRITING_REQUESTS))
			# print('FOUND READS', len(werkzeug.READING_REQUESTS))
			return len(werkzeug.UPDATE_REQUESTS) != 0


	#====================================================================

	def synchronize(self, db = 'master'):
		if db == 'master':
			werkzeug = self.master_handler.database

		import time

		while True:
			num_updates = len(werkzeug.UPDATE_REQUESTS)
			num_writes  = len(werkzeug.WRITING_REQUESTS)
			num_reads   = len(werkzeug.READING_REQUESTS)
			limiting    = np.amax([num_updates, num_writes, num_reads])
			if limiting < 20:
				break
			else:
				print('## WAITING ##', num_updates, num_writes, num_reads)
				time.sleep(1.0)
	

	def print_pending_updates(self, iteration, db = 'master'):
		if db == 'master':
			werkzeug = self.master_handler.database
			# print('\t*******************')
			# print('\tPENDING UPDATES ...', len(werkzeug.UPDATE_REQUESTS))
			# print('\tPENDING WRITES  ...', len(werkzeug.WRITING_REQUESTS))
			# print('\tPENDING READS   ...', len(werkzeug.READING_REQUESTS))
			# print('\t*******************')

			content = open('log_db_activity', 'a')
			content.write('%.3f\t%d\t%d\t%d\n' % (iteration, len(werkzeug.UPDATE_REQUESTS), len(werkzeug.WRITING_REQUESTS), len(werkzeug.READING_REQUESTS)))
			content.close()



