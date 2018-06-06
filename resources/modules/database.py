import rethinkdb as r
from resources.framework import config

rethinkdb = config.RETHINKDB

r.set_loop_type("asyncio")

conn = None



async def get_connection():
	global conn
	conn = conn or await r.connect(rethinkdb["HOST"], rethinkdb["PORT"],  rethinkdb["DB"], password=rethinkdb["PASSWORD"])
	conn.repl()
	return conn
