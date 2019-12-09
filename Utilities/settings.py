#!/usr/bin/env python 

#========================================================================

class _AbstractSetting: 

	def __init__(self, raw = None, general = None):
		self._raw    = raw
		self.general = general
		self.list    = []

	def __iter__(self):
		for element in self.list:
			yield element

#========================================================================

class Settings(object):

	def __init__(self, settings_dict):

		# first, get the general settings
		for setting_name, setting_values in settings_dict.items():
			if setting_name == 'general':
				general_settings = _AbstractSetting()
				for key, value in setting_values.items():
					setattr(general_settings, key, value)
				setattr(self, setting_name, general_settings)	
				break
		else:
			general_settings = None

		# now, parse all other settings
		for setting_name, setting_values in settings_dict.items():

			if isinstance(setting_values, list):
				setting = _AbstractSetting(raw = setting_values, general = general_settings)
				for list_entry in setting_values:
					if isinstance(list_entry, dict):
						entry = _AbstractSetting(raw = list_entry, general = general_settings)
						for key, value in list_entry.items():
							setattr(entry, key, value)
						setattr(setting, entry.name, entry)
						setting.list.append(entry)
					else:
						setattr(setting, list_entry['name'], list_entry)
						setting.list.append(list_entry)
				setattr(self, setting_name, setting)


			elif isinstance(setting_values, dict):
				setting = _AbstractSetting(raw = setting_values, general = general_settings)
				for key, value in setting_values.items():
					setattr(setting, key, value)
				setattr(self, setting_name, setting)