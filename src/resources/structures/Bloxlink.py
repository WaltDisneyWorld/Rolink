from importlib import import_module
from os import environ as env
from discord import AutoShardedClient
from config import WEBHOOKS # pylint: disable=E0611
from ..constants import SHARD_RANGE, CLUSTER_ID, SHARD_COUNT, IS_DOCKER
from . import Args, Permissions
from ast import literal_eval
from async_timeout import timeout
import functools
import traceback
import datetime
import logging
import aiohttp
import aredis
import asyncio; loop = asyncio.get_event_loop()

from rethinkdb.errors import ReqlDriverError

try:
    from rethinkdb import RethinkDB; r = RethinkDB() # pylint: disable=no-name-in-module
except ImportError:
    import rethinkdb as r
finally:
    r.set_loop_type("asyncio")



LOG_LEVEL = env.get("LOG_LEVEL", "INFO").upper()
LABEL = env.get("LABEL", "Bloxlink")

logger = logging.getLogger()


loaded_modules = {}

try:
    from config import RETHINKDB
except ImportError:
    RETHINKDB = {
        "HOST": env.get("RETHINKDB_HOST"),
        "PASSWORD": env.get("RETHINKDB_PASSWORD"),
        "PORT": int(env.get("RETHINKDB_PORT")),
        "DB": env.get("RETHINKDB_DB")
    }

try:
    from config import REDIS
except ImportError:
    REDIS = {
        "HOST": env.get("REDIS_HOST"),
        "PORT": int(env.get("REDIS_PORT")),
        "PASSWORD": env.get("REDIS_PASSWORD"),
    }


class BloxlinkStructure(AutoShardedClient):
    db_host_validated = False

    def __init__(self, *args, **kwargs): # pylint: disable=W0235
        super().__init__(*args, **kwargs) # this seems useless, but it's very necessary.
        loop.run_until_complete(self.get_session())
        loop.run_until_complete(self.load_database())

    async def get_session(self):
        self.session = aiohttp.ClientSession(headers={"Connection": "close"})

    @staticmethod
    def log(*text, level=LOG_LEVEL):
        if level.upper() == LOG_LEVEL:
            print(f"{LABEL} | {LOG_LEVEL} | {'| '.join(text)}", flush=True)


    def error(self, text, title=None):
        logger.exception(text)
        loop.create_task(self._error(text, title=title))

    async def _error (self, text, title=None):
        webhook_data = {
            "username": "Cluster Instance",

            "embeds": [{
                "timestamp": datetime.datetime.now().isoformat(),
                "description": f"**Cluster:** {CLUSTER_ID}\n**Shards:** {str(SHARD_RANGE)}",
                "fields": [
                    {"name": "Traceback", "value": text[0:2000]}
                ],
                "color": 13319470,
            }]
        }

        if title:
            webhook_data["embeds"][0]["title"] = title

        await self.session.post(WEBHOOKS["ERRORS"], json=webhook_data)

    @staticmethod
    def module(module):
        new_module = module()
        module_name = module.__name__

        failed = False
        if hasattr(new_module, "__setup__"):
            try:
                loop.create_task(new_module.__setup__())
            except Exception as e:
                Bloxlink.log(f"ERROR | Module {module_name.lower()}.__setup__() failed: {e}")
                Bloxlink.error(str(e), title=f"Error source: {module_name.lower()}.py")
                failed = True

        if not failed:
            Bloxlink.log(f"Loaded {module_name}")
            loaded_modules[module_name.lower()] = new_module

        return new_module

    @staticmethod
    def loader(module):
        def load(*args, **kwargs):
            return module(*args, **kwargs)

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
                traceback_text = traceback.format_exc()
                traceback_text = len(traceback_text) < 500 and traceback_text or f"...{traceback_text[len(traceback_text)-500:]}"
                Bloxlink.error(traceback_text, title=f"Error source: {name}.py")

            except Exception as e:
                Bloxlink.log(f"ERROR | Module {name} failed to load: {e}")
                traceback_text = traceback.format_exc()
                traceback_text = len(traceback_text) < 500 and traceback_text or f"...{traceback_text[len(traceback_text)-500:]}"
                Bloxlink.error(traceback_text, title=f"Error source: {name}.py")

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

        return (mod and (isinstance(mod, list) and mod[0]) or mod) or module

    async def load_database(self, save_conn=True):
        async def connect(host, password, db, port):
            try:
                conn = await r.connect(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    timeout=2
                )
                conn.repl()

                if save_conn:
                    self.conn = conn

                print("Connected to RethinkDB", flush=True)

            except ReqlDriverError as e:
                print(f"Unable to connect to Database: {e}. Retrying with a different host.", flush=True)

            else:
                return conn

        while True:
            for host in [RETHINKDB["HOST"], "rethinkdb", "localhost"]:
                async with timeout(2):
                    success = await connect(host, RETHINKDB["PASSWORD"], RETHINKDB["DB"], RETHINKDB["PORT"])

                    if success:
                        return

    @staticmethod
    def command(*args, **kwargs):
        return Bloxlink.get_module("commands", attrs="new_command")(*args, **kwargs)

    @staticmethod
    def subcommand(**kwargs):
        def decorator(f):
            f.__issubcommand__ = True
            f.__subcommandattrs__ = kwargs

            @functools.wraps(f)
            def wrapper(self, *args):
                return f(self, *args)

            return wrapper

        return decorator

    @staticmethod
    def flags(fn):
        fn.__flags__ = True
        return fn

    Permissions = Permissions.Permissions # pylint: disable=no-member

    def __repr__(self):
        return "< Bloxlink Client >"


Bloxlink = BloxlinkStructure(
    fetch_offline_members=False,
    shard_count=SHARD_COUNT,
    shard_ids=SHARD_RANGE
)

class Module:
    client = Bloxlink
    r = r
    session = aiohttp.ClientSession(loop=loop)
    loop = loop
    redis = IS_DOCKER and aredis.StrictRedis(host=REDIS["HOST"], port=REDIS["PORT"], password=REDIS["PASSWORD"])
    conn = Bloxlink.conn

Bloxlink.Module = Module
