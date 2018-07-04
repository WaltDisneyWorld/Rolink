from resources.modules.commands import parse_message, processed_messages



async def setup(**kwargs):
	client = kwargs.get("client")

	@client.event
	async def on_message_edit(before, after):
		if after.author.bot:
			return

		if before.id not in processed_messages:
			await parse_message(after)
