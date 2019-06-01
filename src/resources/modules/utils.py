from os import listdir
from re import compile
from ..structures.Bloxlink import Bloxlink
from config import RELEASE, PREFIX # pylint: disable=E0611


@Bloxlink.module
class Utils:
	def __init__(self, args):
		self.args = args
		self.prefix_regex = compile("(.+):(.+)")

	@staticmethod
	def get_files(directory):
		return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__" and name != "_DS_Store"]

	async def get_prefix(self, guild=None, guild_data=None, trello_board=None):
		if not guild:
			return PREFIX

		if RELEASE == "MAIN" and await guild.fetch_member(469652514501951518):
			return "!!"

		if trello_board:
			List = await trello_board.get_list(lambda L: L.name == "Bloxlink Settings")

			if List:
				card = await List.get_card(lambda c: c.name[:6] == "prefix")

				if card:
					if card.name == "prefix":
						if card.desc:
							return card.desc.strip()

					else:
						match = self.prefix_regex.search(card.name)

						if match:
							return match.group(2)



		guild_data = guild_data or await self.args.r.table("guilds").get(str(guild.id)).run() or {}
		prefix = guild_data.get("prefix")

		if prefix and prefix != "!":
			return prefix

		return PREFIX
