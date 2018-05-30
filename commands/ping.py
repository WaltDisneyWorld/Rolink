def setup(client, command):
	@command(name="ping", flags=["test"], arguments=[
		{
			"name": "name1",
			"prompt": "say test1!",
			"type": "string",
			"check": lambda m, c: c == "test1",

		},
		{
			"name": "name2",
			"prompt": "say test2!",
			"type": "string",
			"check": lambda m, c: c == "test2",

		},
	])
	async def ping(message, response, args):
		"""measures the latency of the bot"""

		await message.channel.send("args: " + str(args.parsed_args))
		await message.channel.send("flags: " + str(args.flags))
