from resources.modules.commands import parse_message



async def setup(client, *args, **kwargs):

	@client.event
	async def on_message(message):
		if message.author.bot:
			return

		await parse_message(message)
