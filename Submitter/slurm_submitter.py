#!/usr/bin/env python 

from Submitter import AbstractSubmitter


#====================================================


class SlurmSubmitter(AbstractSubmitter):

	def __init__(self):

		AbstractSubmitter.__init__(self)

