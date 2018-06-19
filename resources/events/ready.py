from asyncio import sleep
from discord import Game, Status
from config import GAME as game_list


async def setup(client, *args, **kwargs):

	@client.event
	async def on_ready():
		print(f'Logged in as {client.user}', flush=True)
		while True:
			for game in game_list:
				game_name = game.format(
					guilds=len(client.guilds),
					users=len(client.users)
				)
				await client.change_presence(status=Status.online, activity=Game(game_name))
				await sleep(20)

