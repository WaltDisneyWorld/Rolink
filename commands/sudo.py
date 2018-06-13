from resources.modules.commands import parse_message



async def setup(client, command, r, *args, **kwargs):
	

	@command(name="sudo", category="Developer", permissions={
		"owner_only": True
	}, arguments=[
		{
			"prompt": "Please specify a user.",
			"type": "user",
			"name": "user"
		},
		{
			"prompt": "Please specify the command.",
			"type": "string",
			"name": "command"
		},
		{
			"prompt": "Please specify the channel.",
			"type": "channel",
			"name": "channel",
			"optional": True
		}
	])
	async def sudo(message, response, args):
		"""spoofs a command as another user"""

		message.author = args.parsed_args["user"]
		message.content = args.parsed_args["command"]
		message.channel = args.parsed_args.get("channel") or message.channel

		await parse_message(message)
		