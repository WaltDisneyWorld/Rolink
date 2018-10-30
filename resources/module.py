from importlib import import_module
from config import RETHINKDB
from resources.structures.Client import client
from time import sleep
from typing import Callable, Optional, Any
import rethinkdb as r; r.set_loop_type("asyncio")
import traceback
import asyncio
import aiohttp

loop = asyncio.get_event_loop()
session = aiohttp.ClientSession(loop=asyncio.get_event_loop())

loaded_modules = {}



async def load_database():
	print("Bloxlink | Connecting to RethinkDB", flush=True)
	conn = await r.connect(
		RETHINKDB["HOST"],
		RETHINKDB["PORT"],
		RETHINKDB["DB"],
		password=RETHINKDB["PASSWORD"]
	)

	conn.repl()


def get_loader(name: str, path: Optional=None) -> Callable:
	path = path or "resources.modules"
	path = path.replace("/", ".")

	import_name = f'{path}.{name}'.replace("/",".").replace(".py","")

	def wrapper(*args, **kwargs) -> Any:
		try:
			module = import_module(import_name)

			if hasattr(module, "new_module"):
				module = module.new_module()

			return module(client=client, r=r, session=session, *args, **kwargs)

		except Exception as e:
			print(f"Module {name} failed to load: {e}", flush=True)
			traceback.print_exc()

	return wrapper


def get_module(name, path=None, attrs=None, *args, **kwargs):
	path = path or "resources.modules"
	path = path.replace("/", ".")
	module = None

	if loaded_modules.get(f'{name}-{path}'):
		module = loaded_modules.get(f'{name}-{path}')
	else:
		import_name = f'{path}.{name}'.replace("/",".").replace(".py","")

		try:
			module = import_module(import_name)

			if hasattr(module, "new_module"):
				new_class = module.new_module()
				module = new_class(client=client, r=r, session=session)
			
			if hasattr(module, "setup"):
				loop.create_task(module.setup(*args, **kwargs))

		except (ModuleNotFoundError, ImportError) as e:
			# log(e)
			print(str(e), flush=True)
			traceback.print_exc()

		except Exception as e:
			# log(f'Module {self.name} failed to load: {e}')
			print(f"Module {name} failed to load: {e}", flush=True)
			traceback.print_exc()
		else:
			print(f"Module {name} has loaded.", flush=True)
			loaded_modules[f'{name}-{path}'] = module

	if attrs:
		attrs_list = []

		for attr in attrs:
			attrs_list.append(getattr(module, attr))

		if len(attrs_list) == 1:
			return attrs_list[0]
		else:
			return (*attrs_list,)

	return loaded_modules.get(f'{name}-{path}') or module
