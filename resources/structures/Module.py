import traceback
from importlib import import_module
from resources.modules.logger import log


class Module:
	def __init__(self, file_path, file_name):
		log(f'Initializing Module {file_name}')
		self.path = file_path
		self.name = file_name
		import_name = f'{self.path}.{self.name}'.replace("/",".").replace(".py","")
		try:
			module = import_module(import_name)
			self.module = module
		except (ModuleNotFoundError, ImportError) as e:
			log(e)
			traceback.print_exc()
		except Exception as e:
			log(f'Module {self.name} failed to load: {e}')
			traceback.print_exc()
