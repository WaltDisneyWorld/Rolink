from os import listdir
from ..structures.Bloxlink import Bloxlink
from config import RELEASE, PREFIX # pylint: disable=E0611


@Bloxlink.module
class Utils:
	def __init__(self, args):
		self.args = args

	@staticmethod
	def get_files(directory):
		return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__" and name != "_DS_Store"]

	async def get_prefix(self, guild=None, guild_data=None):
		if not guild:
			return PREFIX

		if RELEASE == "MAIN" and await guild.fetch_member(469652514501951518):
			return "!!"

		guild_data = guild_data or await self.args.r.table("guilds").get(str(guild.id)).run() or {}
		prefix = guild_data.get("prefix")

		if prefix and prefix != "!":
			return prefix

		return PREFIX
