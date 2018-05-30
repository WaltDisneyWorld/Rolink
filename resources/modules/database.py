import rethinkdb as r
from resources.settings import RETHINKDB

r.set_loop_type("asyncio")

conn = None



async def get_connection():
	global conn
	conn = conn or await r.connect("localhost", RETHINKDB["PORT"],  RETHINKDB["DB"], password=RETHINKDB["PASSWORD"])
	conn.repl()
	return conn
