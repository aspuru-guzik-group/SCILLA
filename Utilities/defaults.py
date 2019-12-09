#!/usr/bin/env python 

import os

_HOME = os.getcwd()

SETTINGS = {
	
	'general': {'scratch_dir': '.scratch'
		},

	'databases': [{'name': 'master',   'db_name': 'master',   'db_type': 'sqlite', 'db_path': '%s/Experiments/master.db'   % _HOME},
				  {'name': 'circuits', 'db_name': 'circuits', 'db_type': 'sqlite', 'db_path': '%s/Experiments/circuits.db' % _HOME},
				  {'name': 'merits',   'db_name': 'merits',   'db_type': 'sqlite', 'db_path': '%s/Experiments/merits.db'   % _HOME},
				  {'name': 'losses',   'db_name': 'losses',   'db_type': 'sqlite', 'db_path': '%s/Experiments/losses.db'   % _HOME},
				  {'name': 'tasks',    'db_name': 'tasks',    'db_type': 'sqlite', 'db_path': '%s/Experiments/tasks.db'    % _HOME},
		],

}

