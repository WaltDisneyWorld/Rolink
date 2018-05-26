from resources.framework import client
from discord import Game, Status


@client.event
async def on_ready():
	print(f'Logged in as {client.user}', flush=True)
	game = Game("!help | !invite")
	await client.change_presence(status=Status.online, activity=game)
