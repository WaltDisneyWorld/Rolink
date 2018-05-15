from resources.framework import client
from resources.modules.commands import parse_message


@client.event
async def on_message(message):
	if message.author.bot:
		return
		
	await parse_message(message)

