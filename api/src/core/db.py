from rethinkdb.errors import ReqlDriverError
from .conf import *
from async_timeout import timeout

try:
    from rethinkdb import RethinkDB; r = RethinkDB() # pylint: disable=no-name-in-module
except ImportError:
    import rethinkdb as r
finally:
    r.set_loop_type("asyncio")


async def load_database():

    async def connect(host, port, db, password):
        try:
            conn = await r.connect(
                host=host,
                port=DB_PORT,
                db=DB,
                password=DB_PASS,
                timeout=2
            )
            conn.repl()

            print("Connected to RethinkDB", flush=True)

        except ReqlDriverError as e:
            print(f"Unable to connect to Database: {e}. Retrying with a different host.", flush=True)

        else:
            return True

    while True:
        for host in DB_HOSTS:
            async with timeout(2):
                success = await connect(host, DB_PORT, DB, DB_PASS)

                if success:

                    return

    return r
