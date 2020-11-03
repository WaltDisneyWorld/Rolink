from importlib import import_module
from os import environ as env
from discord import AutoShardedClient, AllowedMentions, Intents, MemberCacheFlags
from config import WEBHOOKS # pylint: disable=E0611
from ..constants import SHARD_RANGE, CLUSTER_ID, SHARD_COUNT, IS_DOCKER, TABLE_STRUCTURE, RELEASE # pylint: disable=import-error
from ..secrets import REDIS, RETHINKDB # pylint: disable=import-error
from . import Args, Permissions # pylint: disable=import-error
from ast import literal_eval
from async_timeout import timeout
import functools
import traceback
import datetime
import logging
import aiohttp
import aredis
#import sentry_sdk
import asyncio; loop = asyncio.get_event_loop()

from rethinkdb.errors import ReqlDriverError, ReqlOpFailedError

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



class BloxlinkStructure(AutoShardedClient):
    db_host_validated = False
    conn = None

    def __init__(self, *args, **kwargs): # pylint: disable=W0235
        super().__init__(*args, **kwargs) # this seems useless, but it's very necessary.
        #loop.run_until_complete(self.get_session())
        loop.set_exception_handler(self._handle_async_error)
        loop.run_until_complete(self.load_database())

    async def get_session(self):
        self.session = aiohttp.ClientSession() # headers={"Connection": "close"}

    @staticmethod
    def log(*text, level=LOG_LEVEL):
        print(f"{LABEL} | {LOG_LEVEL} | {'| '.join(text)}", flush=True)


    """
    def error(self, e=None, **kwargs):
        if not e:
            e = traceback.format_exc()

        logger.exception(e)

        with sentry_sdk.push_scope() as scope:
            for tag_name, tag_value in kwargs.items():
                if tag_name == "user":
                    scope.user = {"id": tag_value[0], "username": tag_value[1]}
                else:
                    scope.set_tag(tag_name, tag_value)

            scope.level = "error"

            return sentry_sdk.capture_exception()
    """
    def error(self, text, title=None):
        logger.exception(text)
        loop.create_task(self._error(str(text), title=title))

    async def _error (self, text, title=None):
        if (not text) or text == "Unclosed connection":
            return

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

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                try:
                    await session.post(WEBHOOKS["ERRORS"], json=webhook_data)
                except Exception as e:
                    logger.exception(e)
                    pass

        except asyncio.TimeoutError:
            pass

    def _handle_async_error(self, loop, context):
        exception = context.get("exception")
        future_info = context.get("future")
        title = None

        if exception:
            title = exception.__class__.__name__

        if future_info:
            msg = str(future_info)
        else:
            if exception:
                msg = str(exception)
            else:
                msg = str(context["message"])


        self.error(future_info or str(context["message"]), title=title)

    @staticmethod
    def module(module):
        new_module = module()

        module_name = module.__name__.lower()
        module_dir = module.__module__.lower() # ".".join((module.__module__, module.__qualname__))

        if hasattr(new_module, "__setup__"):
            loop.create_task(new_module.__setup__())

        Bloxlink.log(f"Loaded {module_name}")

        if loaded_modules.get(module_dir):
            loaded_modules[module_dir][module_name] = new_module
        else:
            loaded_modules[module_dir] = {module_name: new_module}

        return new_module

    @staticmethod
    def loader(module):
        def load(*args, **kwargs):
            return module(*args, **kwargs)

        stuff = {}

        for attr in dir(module):
            stuff[attr] = getattr(module, attr)

        #loaded_modules[module.__name__.lower()] = [load, stuff]

        #return load

    @staticmethod
    def get_module(dir_name, *, name_override=None, path="resources.modules", attrs=None):
        modules = loaded_modules.get(dir_name)
        name_obj = (name_override or dir_name).lower()

        class_obj = None
        module = None

        if not modules:
            import_name = f"{path}.{dir_name}".replace("src/", "").replace("/",".").replace(".py","")

            try:
                module = import_module(import_name)
            except (ModuleNotFoundError, ImportError) as e:
                Bloxlink.log(f"ERROR | {e}")
                traceback_text = traceback.format_exc()
                traceback_text = len(traceback_text) < 500 and traceback_text or f"...{traceback_text[len(traceback_text)-500:]}"
                Bloxlink.error(traceback_text, title=f"{dir_name}.py")

            except Exception as e:
                Bloxlink.log(f"ERROR | Module {dir_name} failed to load: {e}")
                traceback_text = traceback.format_exc()
                traceback_text = len(traceback_text) < 500 and traceback_text or f"...{traceback_text[len(traceback_text)-500:]}"
                Bloxlink.error(traceback_text, title=f"{dir_name}.py")
            else:
                for attr_name in dir(module):
                    if attr_name.lower() == name_obj:
                        class_obj = getattr(module, attr_name)
                        break

        if not attrs:
            return module or class_obj

        if class_obj is None and module:
            for attr_name in dir(module):
                if attr_name.lower() == name_obj:
                    class_obj = getattr(module, attr_name)

                    break


        if class_obj is not None:
            if attrs:
                attrs_list = list()

                if not isinstance(attrs, list):
                    attrs = [attrs]

                for attr in attrs:
                    if hasattr(class_obj, attr):
                        attrs_list.append(getattr(class_obj, attr))

                if len(attrs_list) == 1:
                    return attrs_list[0]
                else:
                    if not attrs_list:
                        return None

                    return (*attrs_list,)
            else:
                return class_obj

        raise RuntimeError(f"Unable to find module {name_obj} from {dir_name}")


    async def check_database(self, conn):
        try:
            for missing_database in set(TABLE_STRUCTURE.keys()).difference(await r.db_list().run()):
                if RELEASE in ("LOCAL", "CANARY"):
                    await r.db_create(missing_database).run()

                    for table in TABLE_STRUCTURE[missing_database]:
                        await r.db(missing_database).table_create(table).run()
                else:
                    print(f"CRITICAL: Missing database: {missing_database}", flush=True)

            for db_name, table_names in TABLE_STRUCTURE.items():
                try:
                    await r.db(db_name).wait().run()
                except ReqlOpFailedError as e:
                    if RELEASE == "LOCAL":
                        await r.db_create(db_name).run()
                    else:
                        print(f"CRITICAL: {e}", flush=True)

                for table_name in table_names:
                    try:
                        await r.db(db_name).table(table_name).wait().run()
                    except ReqlOpFailedError as e:
                        if RELEASE == "LOCAL":
                            await r.db(db_name).table_create(table_name).run()
                        else:
                            print(f"CRITICAL: {e}", flush=True)
        except ReqlOpFailedError:
            pass

    async def load_database(self, save_conn=True):
        if self.conn:
            return self.conn

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
                try:
                    async with timeout(5):
                        conn = await connect(host, RETHINKDB["PASSWORD"], RETHINKDB["DB"], RETHINKDB["PORT"])

                        if conn:
                            # check for missing databases/tables
                            await self.check_database(conn)

                            return

                except asyncio.TimeoutError:
                    pass

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


intents = Intents.none()

intents.members = True # pylint: disable=assigning-non-slot
intents.guilds = True # pylint: disable=assigning-non-slot
intents.guild_reactions = True # pylint: disable=assigning-non-slot
intents.guild_messages = True # pylint: disable=assigning-non-slot
intents.dm_messages = True # pylint: disable=assigning-non-slot
intents.bans = True # pylint: disable=assigning-non-slot

if RELEASE == "PRO":
    intents.guild_typing = True # pylint: disable=assigning-non-slot


Bloxlink = BloxlinkStructure(
    chunk_guilds_at_startup=False,
    shard_count=SHARD_COUNT,
    shard_ids=SHARD_RANGE,
    allowed_mentions=AllowedMentions(everyone=False, users=True, roles=False),
    intents=intents,
)


def load_redis():
    redis = redis_cache = None

    if IS_DOCKER:
        while not redis:
            try:
                redis = aredis.StrictRedis(host=REDIS["HOST"], port=REDIS["PORT"], password=REDIS["PASSWORD"])
            except aredis.exceptions.ConnectionError:
                pass
            else:
                redis_cache = redis.cache("cache")

    return redis, redis_cache

redis, redis_cache = load_redis()

class Module:
    client = Bloxlink
    r = r
    #session = aiohttp.ClientSession(loop=loop)
    loop = loop
    redis = redis
    cache = redis_cache
    conn = Bloxlink.conn

Bloxlink.Module = Module
