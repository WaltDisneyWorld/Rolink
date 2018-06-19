from config import RETHINKDB as rethinkdb
import rethinkdb as r


r.set_loop_type("asyncio")

conn = None



async def get_connection():
	global conn
	conn = conn or await r.connect(rethinkdb["HOST"], rethinkdb["PORT"],  rethinkdb["DB"], password=rethinkdb["PASSWORD"])
	conn.repl()
	return conn
