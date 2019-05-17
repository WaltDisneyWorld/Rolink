from importlib import import_module
from os import environ as env
from discord import AutoShardedClient
from config import RETHINKDB # pylint: disable=E0611
from .Args import Args
from rethinkdb import RethinkDB; r = RethinkDB(); r.set_loop_type("asyncio")
from rethinkdb.errors import ReqlDriverError
from ast import literal_eval
import traceback
import asyncio; loop = asyncio.get_event_loop()


SHARD_COUNT = int(env.get("SHARD_COUNT", 1))
SHARD_RANGE = literal_eval(env.get("SHARD_RANGE", "(0,)"))

LOG_LEVEL = env.get("LOG_LEVEL", "INFO").lower()
LABEL = env.get("LABEL", "Bloxlink")


loaded_modules = {}


class BloxlinkStructure(AutoShardedClient):
	db_host_validated = False

	def __init__(self, *args, **kwargs): # pylint: disable=W0235
		super().__init__(*args, **kwargs) # this seems useless, but it's very necessary.

	@staticmethod
	def log(text, level=LOG_LEVEL):
		if level.lower() == LOG_LEVEL:
			print(f"{LABEL} | {text}", flush=True)

	@staticmethod
	def module(module):
		args = Args(
			r=r,
			client=Bloxlink
		)
		new_module = module(args)

		failed = False
		if hasattr(new_module, "setup"):
			try:
				loop.create_task(new_module.setup())
			except Exception as e:
				Bloxlink.log(f"ERROR | Module {new_module.__name__.lower()}.setup() failed: {e}")
				failed = True

		if not failed:
			Bloxlink.log(f"Loaded {module.__name__}")
			loaded_modules[module.__name__.lower()] = new_module

	@staticmethod
	def loader(module):
		module_args = Args(
			r=r,
			client=Bloxlink
		)

		def load(*args, **kwargs):
			return module(module_args, *args, **kwargs)

		stuff = {}

		for attr in dir(module):
			stuff[attr] = getattr(module, attr)

		loaded_modules[module.__name__.lower()] = [load, stuff]

	@staticmethod
	def get_module(name, *, path="resources.modules", attrs=None):
		module = None

		if loaded_modules.get(name):
			module = loaded_modules.get(name)
		else:
			import_name = f"{path}.{name}".replace("src/", "").replace("/",".").replace(".py","")

			try:
				module = import_module(import_name)
			except (ModuleNotFoundError, ImportError) as e:
				Bloxlink.log(f"ERROR | {e}")
				traceback.print_exc()

			except Exception as e:
				Bloxlink.log(f"ERROR | Module {name} failed to load: {e}")
				traceback.print_exc()

		mod = loaded_modules.get(name)

		if attrs:
			attrs_list = []

			if not isinstance(attrs, list):
				attrs = [attrs]

			if mod:

				for attr in attrs:
					if isinstance(mod, list):
						if attr in mod[1]:
							attrs_list.append(mod[1][attr])
					else:
						if hasattr(mod, attr):
							attrs_list.append(getattr(mod, attr))

				if hasattr(mod, attr) and not getattr(mod, attr) in attrs_list:
					attrs_list.append(getattr(mod, attr))

			if len(attrs_list) == 1:
				return attrs_list[0]
			else:
				if not attrs_list:
					return None

				return (*attrs_list,)

		return (mod and (isinstance(mod, list) and mod[0]) or mod)  or module


	@staticmethod
	async def load_database(host=RETHINKDB["HOST"]):
		try:
			conn = await r.connect(
				host,
				RETHINKDB["PORT"],
				RETHINKDB["DB"],
				password=RETHINKDB["PASSWORD"]
			)
			Bloxlink.db_host_validated = True
		except ReqlDriverError as e:
			Bloxlink.log(f"Unable to connect to Database: {e}. Retrying.")
			await asyncio.sleep(5)

			if not Bloxlink.db_host_validated:
				return await Bloxlink.load_database("localhost")

			return await Bloxlink.load_database()

		conn.repl()

		Bloxlink.log("Connected to RethinkDB")

	@staticmethod
	def command(*args, **kwargs):
		Bloxlink.log("Adding new command")
		return Bloxlink.get_module("commands", attrs="new_command")(*args, **kwargs)

	@staticmethod
	def subcommand(a=None):
		if callable(a):
			a.__issubcommand__ = True
			return a
		else:
			def wrapper(fn):
				fn.__issubcommand__ = True
				fn.__subcommandattrs__ = a or {}
				return fn

			return wrapper

	@staticmethod
	def flags(fn):
		fn.__flags__ = True

	def __repr__(self):
		return "< Bloxlink Instance >"


Bloxlink = BloxlinkStructure(
	fetch_offline_members=False,
	shard_count=SHARD_COUNT,
	shard_ids=SHARD_RANGE
)

class Module: # all of this is cancerous and will change when I think of a better way
	client = Bloxlink
	r = r

Bloxlink.Module = Module
