#!/usr/bin/env python 

""" Creates a subprocess to execute the circuit solver wrapper """

### Toggle line 11, 29, 38 comments to switch between MacOS and Odyssey computing cluster ###

#====================================================

import os
import pickle
# import multiprocessing #comment for MacOS / uncomment for Odyssey
import subprocess
import uuid

import numpy as np

from Submitter import AbstractSubmitter

#====================================================

class LocalSubmitter(AbstractSubmitter):

    FILE_LOGGERS = []


    def __init__(self, settings, general_params, evaluation_function):
        
        AbstractSubmitter.__init__(self, settings, general_params, evaluation_function)
        # self.num_cores    = multiprocessing.cpu_count() #comment for MacOS / uncomment for Odyssey
        # print('\n\n')
        # print('NUM_CORES', self.num_cores)
        # print('\n\n')
        self.get_available_cpus()
        self.next_process = {}
	
    def get_available_cpus(self):
        scratch_name = 'scratch_file'
        # subprocess.call('cat /proc/"self"/status | grep Cpus_allowed_list > %s' % scratch_name, shell = True) #comment for MacOS / uncomment for Odyssey
        with open(scratch_name, 'r') as content:
            file_content = content.read()
            cpu_info = file_content.strip().split()[1].split(',')
            cpu_list = []
            for element in cpu_info:
                if '-' in element:
                    cpu_bounds = [int(entry) for entry in element.split('-')]
                    cpu_list.extend(range(cpu_bounds[0], cpu_bounds[1] + 1))
                else:
                    cpu_list.append(int(element))
        self.cpu_list = cpu_list
        print('\n\nCPU_LIST: %s\n\n' % str(self.cpu_list))


    def get_process_index(self, task_set):
        task_name      = task_set.settings['name']
        max_concurrent = task_set.settings['designer_options']['max_concurrent']

        if not task_name in self.next_process:
            next_process = self.cpu_list[0]
            self.next_process[task_name] = 1
        else:
            next_process = self.cpu_list[self.next_process[task_name]]
            self.next_process[task_name] = (self.next_process[task_name] + 1) % len(self.cpu_list)
        return next_process


    def submit(self, circuit, task_set, job_id):

        process_index = self.get_process_index(task_set)

        job_name = 'job_%s' % job_id
        if 'general_params' in circuit:
            job_dict = {'evaluation_function': circuit['evaluation_function'],
                        'general_params':      circuit['general_params'],
                        'circuit':             circuit['circuit'],
                        'merit_re-eval':       True,
                        'job_name':            job_name,}
        else:
            job_dict = {'evaluation_function': self.evaluation_function,
                        'general_params':      self.general_params,
                        'circuit':             circuit,
                        'job_name':            job_name,}

        file_name = '%s/%s.pkl' % (self.settings.scratch_dir, job_name)
        with open(file_name, 'wb') as content:
            pickle.dump(job_dict, content)

        FNULL = open(os.devnull, 'w')

        subprocess.call('python Submitter/execute.py %s %d &' % (file_name, process_index), shell = True) #debug: show subprocess output

        return True

