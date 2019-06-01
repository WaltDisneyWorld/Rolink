from aiotrello import Trello as TrelloClient
from aiotrello.exceptions import TrelloBadRequest
from ..structures.Bloxlink import Bloxlink
from ..exceptions import BadUsage
from time import time
from config import TRELLO # pylint: disable=E0611


@Bloxlink.module
class Trello:
	def __init__(self, args):
		self.args = args
		self.trello_boards = {}
		self.trello = TrelloClient(key=TRELLO.get("key"), token=TRELLO.get("token"))

	async def get_board(self, guild_data=None, guild=None):
		trello_board = None

		if guild_data is not None and guild:
			trello_board = self.trello_boards.get(guild.id)

			if guild_data.get("trelloID"):
				try:
					trello_board = trello_board or await self.trello.get_board(guild_data.get("trelloID"))

					if trello_board:
						if not self.trello_boards.get(guild.id):
							self.trello_boards[guild.id] = trello_board

						t_now = time()

						if hasattr(trello_board, "expiration"):
							if t_now > trello_board.expiration:
								await trello_board.sync()
								trello_board.expiration = t_now + (5 * 60)

						else:
							trello_board.expiration = t_now + (5 * 60)

				except TrelloBadRequest:
					pass
		else:
			raise BadUsage


		return trello_board


