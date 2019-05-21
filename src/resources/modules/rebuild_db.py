from ..structures.Bloxlink import Bloxlink
from config import RELEASE # pylint: disable=no-name-in-module

TABLE_STRUCTURE = {
	"bloxlink": [
		"users",
		"guilds",
	],
	"patreon": []
}

@Bloxlink.module
class RebuildDB:
	def __init__(self, args):
		self.r = args.r

	async def __setup__(self):
		for missing_database in set(TABLE_STRUCTURE.keys()).difference(await self.r.db_list().run()):
			if RELEASE == "LOCAL":
				await self.r.db_create(missing_database).run()

				for table in TABLE_STRUCTURE[missing_database]:
					await self.r.db(missing_database).table_create(table).run()
			else:
				print(f"CRITICAL: Missing database: {missing_database}", flush=True)
