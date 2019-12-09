#!/usr/bin/env python 

#====================================================

import os
import copy
import uuid
import time
import pickle
import threading

from Submitter import LocalSubmitter
from Submitter import solve_circuit
from Utilities import FileLogger

from Utilities.decorators import thread

#====================================================

class CircuitSubmitter(object):
    """
        Purpose:
            connects to hardware specific circuit submission modules,
            receives circuit parameters from circuit searcher,
            submits these parameters to appropriate computing hardware,
            collects computation results for pick up by circuit searcher,
    """

    # declare containers
    FILE_LOGGERS     = {}
    RECEIVED_RESULTS = []


    def __init__(self, settings, general_params):
        self.settings       = settings
        self.general_params = general_params
        self.submitters     = {}


    def add_submitter(self, keyword):
        if not keyword in self.submitters:
            if keyword == 'local':  
                from Submitter import LocalSubmitter as SelectedSubmitter
            else:
                raise NotImplementedError()
            self.submitters[keyword] = SelectedSubmitter(self.settings, self.general_params, solve_circuit)


    def parse_calculation_results(self, file_name):
        if not 'proc' in file_name: return None

        with open(file_name, 'rb') as content:
            data = pickle.load(content)

        self.RECEIVED_RESULTS.append(data)
        os.remove(file_name)
        file_name = file_name.replace('proc_', '')
        os.remove(file_name)

        # need to close file logger
        job_id = file_name.split('_')[-1].split('.')[0]
        file_logger = self.FILE_LOGGERS[job_id]
        file_logger.stop()
        del self.FILE_LOGGERS[job_id]


    def get_new_results(self):
        new_results = copy.deepcopy(self.RECEIVED_RESULTS)
        for new_result in new_results:
            self.RECEIVED_RESULTS.pop(0)
        return new_results


    def check_resource_availability(self, task_set):
        computing_resource = task_set.settings['computing_resource']
        submitter          = self.submitters[computing_resource]
        return submitter.is_available()


    def _submit(self, submitter, circuit, task_set, job_id):
        file_logger = FileLogger(action = self.parse_calculation_results, path = self.settings.scratch_dir, pattern = '*job*%s*' % (job_id))
        self.FILE_LOGGERS[job_id] = file_logger
        file_logger.start()

        # submit job
        success = submitter.submit(circuit, task_set, job_id)
        self.successes[job_id] = success
        if not success:
            self.FILE_LOGGERS[job_id].stop()
            del self.FILE_LOGGERS[job_id]


    def submit(self, circuits, task_set):
        # fetch hardware specific submitter, create for monitoring

        computing_resource = task_set.settings['computing_resource']
        submitter          = self.submitters[computing_resource]

        self.successes = {}
        job_ids, threads = [], []

        # Case 1: there is just one circuit to be submitted (avoid enumerating dict entries)
        if type(circuits) == dict:
            circuit = circuits
            job_id = str(uuid.uuid4())
            job_ids.append(job_id)
            thread = threading.Thread(target = self._submit, args = (submitter, circuit, task_set, job_id))
            threads.append(thread)
            thread.start()

        # Case 2: there are several circuits to be submitted
        else:
            for circuit_index, circuit in enumerate(circuits):
                job_id = str(uuid.uuid4())
                job_ids.append(job_id)
                thread = threading.Thread(target = self._submit, args = (submitter, circuit, task_set, job_id))
                threads.append(thread)
                thread.start()

        submitted = range(len(job_ids))
        not_submitted = []
        return submitted, not_submitted


    def get_computed_circuits(self):
        # return all results collected from prior submission
        computed_circuits = copy.deepcopy(self.RECEIVED_RESULTS)
        for computed_circuit in computed_circuits:
            self.RECEIVED_RESULTS.pop(0)
        return computed_circuits
