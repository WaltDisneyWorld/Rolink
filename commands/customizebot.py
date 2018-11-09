async def setup(**kwargs):
	command = kwargs.get("command")
	subcommand = kwargs.get("subcommand")
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
			"direct image with the file extension at the end. Example: <https://blox.link/asset.png>.",
			"type": "string",
			"min": 1,
			"max": 200
		}
	], aliases=["custombot"])
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


	@subcommand(parent_name="customizebot", name="disable")
	async def disable(message, response, args, prefix):

		guild_data = response.guild_data
		custom_bot = guild_data.get("customBot", {})
		custom_bot["enabled"] = False

		await r.table("guilds").insert({
			"id": str(message.guild.id),
			"customBot": custom_bot
		}, conflict="update").run()

		await response.success("Successfully **disabled** the custom bot.")

	@subcommand(parent_name="customizebot", name="enable")
	async def enable(message, response, args, prefix):

		guild_data = response.guild_data
		custom_bot = guild_data.get("customBot", {})
		custom_bot["enabled"] = True

		await r.table("guilds").insert({
			"id": str(message.guild.id),
			"customBot": custom_bot
		}, conflict="update").run()

		await response.success("Successfully **enabled** the custom bot.")
