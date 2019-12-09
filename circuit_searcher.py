#!/usr/bin/env python 

import os
import time
import numpy as np 
import threading
import pickle

from Submitter            import CircuitSubmitter
from CircuitQuantifier    import CircuitCritic, CircuitValidator
from DatabaseHandler      import DatabaseHandler
from Designers            import CircuitDesigner
from TaskSets             import CalculationTaskSet, FilteringTaskSet
from Utilities            import Settings

from Utilities            import defaults
from Utilities.decorators import thread


#====================================================

def _report_times(file_name, start, end):
	content = open(file_name, 'a')
	content.write('%.5f\n' % (end - start))
	content.close()

#====================================================


class CircuitSearcher(object):
	"""
		API for SCILLA functionalities.
	"""

	def __init__(self, circuit_params = None, general_params = None, database_path = None, settings = None):
		if settings is None:
			self.settings       = Settings(defaults.SETTINGS)

		if not os.path.isdir(self.settings.general.scratch_dir):
			os.mkdir(self.settings.general.scratch_dir)

		self.circuit_params = circuit_params
		self.general_params = general_params
		self.task_sets      = []

		self.db_handler        = DatabaseHandler(self.settings.databases, database_path)
		self.circuit_submitter = CircuitSubmitter(self.settings.general, self.general_params)
		self.circuit_validator = CircuitValidator()
		self.circuit_critic    = CircuitCritic(self.circuit_params)
		self.circuit_designer  = CircuitDesigner(self.settings.general, self.circuit_params)


	def add_task(self, name = 'task0', 
					   designer = 'random_search', designer_options = {'max_iters': 10, 'max_concurrent': np.inf},
					   merit = 'DoubleWell', merit_options = {},
					   observations = [], use_library = False, 
					   computing_resource = 'local', computing_options = {}):

		# copy settings from kwargs
		settings = {}
		for key, value in locals().items():
			if key in ['self', 'settings']: continue
			settings[key] = value

		# add task set based on defined designer
		if designer in ['random', 'particle_swarms', 'phoenics','grid','CMAES','LBFGS', 'scipy']:
			task_set = CalculationTaskSet(settings)
			self.circuit_designer.add_designer(name, designer, designer_options)
			self.circuit_submitter.add_submitter(computing_resource)
		elif designer in ['filter_db']:
			task_set = FilteringTaskSet(settings)
		else:
			raise NotImplementedError

		self.task_sets.append(task_set)
		return task_set


	def _run_calculation(self, task_set):
		# fetch task_set_id for easy access
		task_set_id = task_set.task_set_id

		# generate all primary tasks (i.e. primers for optimization iterations)
		all_tasks = task_set.generate_all_tasks()
		task_ids  = [task['task_id'] for task in task_set.generated_tasks]
		self.db_handler.refresh()
		self.db_handler.add_tasks(all_tasks)

		# check if we build on prior results
		if task_set.settings['use_library']:
			prior_observations = self.db_handler.get_prior_circuit_evaluations()

		# check abortion criteria
		task_set_completed  = self.db_handler.task_set_completed(task_set_id)
		designer_terminated = self.circuit_designer.designer_terminated(task_set)

		total_start = time.time()

		# enter task execution loop

		start_time = time.time()

		iteration = 0
		while not task_set_completed or not designer_terminated:

			tic = time.time()
			reported_times, reported_labels = [], []

			# [x] fetch all tasks remaining for this task_set
			start = time.time()
			remaining_tasks = self.db_handler.fetch_remaining_tasks(task_set_id)
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('fetching remaining tasks')

			# [x] force designer to generate new parameters
			start = time.time()
			if not task_set_completed and designer_terminated:
				num_from_optimizer = 0
				for remaining_task in remaining_tasks:
					if remaining_task['from_optimizer']:
						num_from_optimizer += 1
				if num_from_optimizer == len(remaining_tasks):
					self.db_handler.set_tasks_to_redundant(remaining_tasks)


			# [x] query parameters from designer
			if task_set_completed and not designer_terminated:

				# send new observations to designer, i.e. give designer the chance to update
				observations = self.db_handler.get_circuit_evaluations(task_set_id)
				if task_set.settings['use_library']:
					observations.extend(prior_observations)
				self.circuit_designer.provide_observations(task_set, observations)

				# get new tasks from designer
				new_tasks = self.circuit_designer.get_requested_tasks(task_set)
				self.db_handler.add_tasks(new_tasks)
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('processing special cases')			
	

			# give priority to tasks associated with currently running optimization iterations
			sorted_tasks = remaining_tasks
			print('# LOG | ... found %d remaining tasks ...' % len(sorted_tasks))


			# [x] try to submit tasks to computing resources

			# try to submit remaining tasks
			start_0 = time.time()
			num_available_resources = self.db_handler.get_num_available_resources(task_set)
			if num_available_resources > 0:
				submittable_tasks  = sorted_tasks[:num_available_resources]
				available_circuits = self.db_handler.get_validated_circuits()

				if len(available_circuits) == 0:
					start = time.time()
					# no valid circuits available --> tell designer to generate more circuit parameters
					print('# LOG | ... could not find validated circuits ...')
					if not self.circuit_designer.is_busy(task_set):
						# send observations to designer
						observations = self.db_handler.get_circuit_evaluations(task_set.task_set_id)
						if task_set.settings['use_library']:
							observations.extend(prior_observations)
						# tell designer to make more circuits
						self.circuit_designer.design_new_circuits(task_set, observations = observations)
						print('# LOG | ... called circuit designer ...')
					reported_times.append(time.time() - start)
					reported_labels.append('\tpinging_designer')
				else:
					# fetch valid circuits and submit to computing resources
					num_submissions = np.minimum(len(submittable_tasks), len(available_circuits))
					tasks    = submittable_tasks[:num_submissions]
					circuits = available_circuits[:num_submissions] 

					# attempt to submit circuits
					start = time.time()
					self.db_handler.reserve_circuits(circuits)
					reported_times.append(time.time() - start)
					reported_labels.append('\tsubmitting_task_0')

					start = time.time()
					submitted, not_submitted = self.circuit_submitter.submit(circuits, task_set)
					reported_times.append(time.time() - start)
					reported_labels.append('\tsubmitting_task_1')

					# record successfully submitted circuits
					start = time.time()
					submitted_tasks    = tasks
					submitted_circuits = circuits
					self.db_handler.set_tasks_to_submitted(submitted_tasks)
					self.db_handler.link_submissions(submitted_tasks, submitted_circuits)
					reported_times.append(time.time() - start)
					reported_labels.append('\tsubmitting_task_3')

			end_0 = time.time()
			reported_times.append(end_0 - start_0)
			reported_labels.append('processing remaining tasks')


			# check if new circuits have been designed
			start = time.time()
			new_circuits = self.circuit_designer.get_circuits()
			self.db_handler.add_new_circuits(new_circuits)
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('getting circuits from designer')

			# query validator for validated circuits
			start = time.time()
			validated_circuits = self.circuit_validator.get_validated_circuits()
			self.db_handler.store_validated_circuits(validated_circuits)
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('getting circuits from validator')

			# submit new circuits to validator
			start_0 = time.time()
			new_circuits = self.db_handler.get_new_circuits()
			end_0 = time.time()
			reported_times.append(end_0 - start_0)
			reported_labels.append('\tsubmitting circuits to validator 0')

			start_1 = time.time()
			print('# LOG | ... processing %d new circuits ...' % len(new_circuits))
			self.circuit_validator.validate_circuits(new_circuits)
			end_1 = time.time()
			reported_times.append(end_1 - start_1)
			reported_labels.append('submitting circuits to validator 1')

			# collect criticized circuits
			start = time.time()
			criticized_circuit_results = self.circuit_critic.get_criticized_circuits()
			criticized_circuits = [result[0] for result in criticized_circuit_results]
			id_dicts            = [result[1] for result in criticized_circuit_results]
			print('# LOG | ... found %d criticized circuits ...' % len(criticized_circuits))
			self.db_handler.store_criticized_circuits(criticized_circuits, id_dicts)
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('collecting circuits from critic')

			# check if critic requires new tasks
			start = time.time()
			new_circuits = self.circuit_critic.get_requested_tasks()
			for circuit in new_circuits:
				self.circuit_submitter.submit(circuit, task_set)
				self.db_handler.report_circuit_submission()
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('submitting tasks from critic')

			# report progress
			start = time.time()
			progress_info = self.db_handler.get_task_set_progress_info(task_set, time.time() - start_time)
			print('PROGRESS:\n%s (%.3f)' % (progress_info, time.time() - total_start))	
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('getting progress report')

			iteration += 1

			# update abortion criteria
			start = time.time()
			task_set_completed  = self.db_handler.task_set_completed(task_set_id)
			designer_terminated = self.circuit_designer.designer_terminated(task_set)
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('updating abortion criteria')

			# check if the designer requests any new tasks
			start = time.time()
			new_tasks = self.circuit_designer.get_requested_tasks(task_set)
			self.db_handler.add_tasks(new_tasks)
			end = time.time()
			reported_times.append(end - start)
			reported_labels.append('getting tasks from designer')

			# query submitter for received spectra
			start = time.time()
			merit_evaluation_circuits, newly_computed_circuits = [], []
			computed_circuits = self.circuit_submitter.get_computed_circuits()
			for circuit in computed_circuits:
				if 'merit_re-eval' in circuit:
					merit_evaluation_circuits.append(circuit)
					self.db_handler.report_circuit_computation()
				else:
					newly_computed_circuits.append(circuit)

			reported_times.append(time.time() - start)
			reported_labels.append('\tprocessing merit evaluations 0')

			unsuccessful = True
			id_dicts = self.db_handler.set_tasks_to_computed(newly_computed_circuits)
			while len(id_dicts) < len(newly_computed_circuits):
				id_dicts = self.db_handler.set_tasks_to_computed(newly_computed_circuits)

			self.circuit_critic.criticize_circuits(newly_computed_circuits, task_set, id_dicts)
			self.circuit_critic.report_reevaluations(merit_evaluation_circuits)

			self.db_handler.print_pending_updates(time.time() - start_time)
			self.db_handler.synchronize()

			toc = time.time()
			new_line = '@@@ Timing: %.5f @@@ | NUM_THREADS: %d\n' % ((toc - tic), threading.active_count())
			print(new_line)

			content = open('log_threads', 'a')
			content.write('%.3f\t%d\n' % (time.time() - start_time, threading.active_count()))
			content.close()

			time.sleep(.2) # <== THIS SLEEP IS ESSENTIAL; DO NOT REMOVE

		self.db_handler.set_circuits_to_unused()


	def _run_filtering(self, task_set):
		while self.db_handler.is_updating():
			time.sleep(0.05)
		self.db_handler.filter_for_best_performing(task_set.settings['designer_options'])
		# wait for completion of update_requests
		while self.db_handler.is_updating():
			time.sleep(0.05)

	
	def execute(self):
		
		for task_set in self.task_sets:
	
			print('# LOG | ... starting task "%s" ...' % task_set.task_set_name)

			if task_set.task_type == 'calculation':
				self._run_calculation(task_set)

			elif task_set.task_type == 'filtering':
				self._run_filtering(task_set)

			elif task_set.task_type == 'db_query':
				self._run_db_query(task_set)


			print('# LOG | ... COMPLETED task "%s" ...' % task_set.task_set_name)
			time.sleep(1)


	def query(self, kind = None, **kwargs):

		if kind == 'get_circuits_from_task':
			return self.db_handler.get_circuits_from_task(kwargs['task'])
		elif kind == 'get_trajectories':
			return self.db_handler.get_trajectories(kwargs['task'])
		elif kind == 'list_computing_tasks':
			task_set_dicts = self.db_handler.list_computing_tasks()
			return task_set_dicts
		else:
			raise NotImplementedError



















