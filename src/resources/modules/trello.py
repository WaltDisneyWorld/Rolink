from aiotrello import Trello as TrelloClient
from aiotrello.exceptions import TrelloBadRequest, TrelloUnauthorized, TrelloNotFound
from ..structures.Bloxlink import Bloxlink
from ..exceptions import BadUsage
from time import time
from config import TRELLO # pylint: disable=E0611



@Bloxlink.module
class Trello(Bloxlink.Module):
	def __init__(self):
		self.trello_boards = {}
		self.trello = TrelloClient(key=TRELLO.get("KEY"), token=TRELLO.get("TOKEN"), cache_mode="none")

	async def get_board(self, guild_data, guild):
		trello_board = None

		if guild_data and guild:
			trello_board = self.trello_boards.get(guild.id)
			trello_id = guild_data.get("trelloID")

			if trello_id:
				try:
					trello_board = trello_board or await self.trello.get_board(trello_id, card_limit=TRELLO["GLOBAL_CARD_LIMIT"])

					if trello_board:
						if not self.trello_boards.get(guild.id):
							self.trello_boards[guild.id] = trello_board

						t_now = time()

						if hasattr(trello_board, "expiration"):
							if t_now > trello_board.expiration:
								await trello_board.sync(card_limit=TRELLO["GLOBAL_CARD_LIMIT"])
								trello_board.expiration = t_now + TRELLO["TRELLO_BOARD_CACHE_EXPIRATION"]

						else:
							trello_board.expiration = t_now + TRELLO["TRELLO_BOARD_CACHE_EXPIRATION"]

				except TrelloBadRequest:
					pass
				except TrelloUnauthorized:
					pass
				except TrelloNotFound:
					guild_data.pop("trelloID")

					await self.r.table("guilds").get(str(guild.id)).update(guild_data).run()


		return trello_board
