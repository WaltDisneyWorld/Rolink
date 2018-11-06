async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="customizebot", category="Premium", permissions={"raw": "manage_guild"},
	arguments=[
		{   
			"name": "name",
			"prompt": "What name would you like to use for the bot?",
			"type": "string",
			"min": 1,
			"max": 30
		},
		{
			"name": "avatar",
			"prompt": "Please provided a URL of an image to use for the bot. This image must be a " \
			"direct image with the file extension at the end. Example: <https://blox.link/asset.png>\n"
			"Also, the image link can't be a discord image url, it needs to be hosted on some other site.",
			"type": "string",
			"min": 1,
			"max": 200
		}
	])
	async def customizebot(message, response, args, prefix):
		"""customize the name and avatar of the bot used in responses"""

		guild = message.guild

		bot_name = args.parsed_args["name"]
		bot_avatar = args.parsed_args["avatar"]

		await r.table("guilds").insert({
			"id": str(guild.id),
			"customBot": {
				"name": bot_name,
				"avatar": bot_avatar,
				"enabled": True
			}
		}, conflict="update").run()

		await response.success("Successfully saved your new bot config! Please ensure I have the "
		"``Manage Webhooks`` role permission for this to work.")
