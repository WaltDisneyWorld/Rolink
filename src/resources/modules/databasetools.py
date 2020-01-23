from ..structures.Bloxlink import Bloxlink
from config import RELEASE # pylint: disable=no-name-in-module
from rethinkdb.errors import ReqlOpFailedError

TABLE_STRUCTURE = {
	"bloxlink": [
		"users",
		"guilds",
	],
	"patreon": []
}

@Bloxlink.module
class DatabaseTools(Bloxlink.Module):
	def __init__(self):
		pass

	async def __setup__(self):
		for missing_database in set(TABLE_STRUCTURE.keys()).difference(await self.r.db_list().run()):
			if RELEASE == "LOCAL":
				await self.r.db_create(missing_database).run()

				for table in TABLE_STRUCTURE[missing_database]:
					await self.r.db(missing_database).table_create(table).run()
			else:
				print(f"CRITICAL: Missing database: {missing_database}", flush=True)

	async def wait(self):
		for db_name, table_names in TABLE_STRUCTURE.items():
			try:
				await self.r.db(db_name).wait().run()
			except ReqlOpFailedError as e:
				print(f"CRITICAL: {e}", flush=True)


			for table_name in table_names:
				try:
					await self.r.db(db_name).table(table_name).wait().run()
				except ReqlOpFailedError as e:
					print(f"CRITICAL: {e}", flush=True)
