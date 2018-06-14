import traceback
from importlib import import_module
import rethinkdb as r
from resources.modules.logger import log


class Module:
	def __init__(self, file_path, file_name):
		log(f'Initializing Module {file_name}')

		self.path = file_path
		self.name = file_name
		self.module = None

	async def execute(self):
		import_name = f'{self.path}.{self.name}'.replace("/",".").replace(".py","")

		try:
			module = import_module(import_name)
			self.module = module
			if hasattr(module, "setup"):
				from resources.framework import client
				from resources.modules.commands import new_command as command
				from resources.modules.database import get_connection

				await get_connection()

				await getattr(module, "setup")(client=client, command=command, r=r)
		except (ModuleNotFoundError, ImportError) as e:
			log(e)
			traceback.print_exc()
		except Exception as e:
			log(f'Module {self.name} failed to load: {e}')
			traceback.print_exc()
