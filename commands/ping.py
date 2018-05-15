from resources.modules.commands import new_command as command


@command(name="ping", alias=["test"])
async def ping(message, response):
	"""measures the latency of the bot"""

	await message.channel.send("pong")
