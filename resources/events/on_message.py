from resources.modules.commands import parse_message



async def setup(**kwargs):
	client = kwargs.get("client")

	@client.event
	async def on_message(message):
		if message.author.bot:
			return
		if not message.guild:
			return

		await parse_message(message)
