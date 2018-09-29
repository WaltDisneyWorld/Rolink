from asyncio import sleep
from discord import Game, Status
from config import GAME as games

from resources.module import get_module
parse_message = get_module("commands", attrs=["parse_message"])
post_count = get_module("post_server_count", attrs=["post_count"])

class OnReady:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")

	async def setup(self):

		@self.client.event
		async def on_ready():
			print(f'Logged in as {self.client.user}', flush=True)
			
			"""while True:
				for game in games:
					game_name = game.format(
						guilds=len(client.guilds),
						users=len(client.users)
					)
					await client.change_presence(status=Status.online, activity=Game(game_name))
					await sleep(60)
			"""
			await post_count()
			await self.client.change_presence(status=Status.online, activity=Game(games))

def new_module():
	return OnReady