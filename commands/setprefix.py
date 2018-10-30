async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="setprefix", category="Administration", arguments=[{
		"prompt": "What would you like to use as the prefix?",
		"name": "new_prefix",
		"type": "string",
		"max": 6,
		"min": 1,
		"optional": True
	}], permissions={"raw": "manage_guild"}, examples=[
		"setprefix !!"
	])
	async def setprefix(message, response, args, prefix):
		"""set the prefix used for Bloxlink commands. The bot will stop listening to the old prefix. Leave the value blank to revert to the original."""

		guild = message.guild
		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

		new_prefix = args.parsed_args.get("new_prefix") or guild_data.get("prefix") or "!"

		await r.table("guilds").insert({
			"id": str(guild.id),
			"prefix": new_prefix
		}, conflict="update").run()

		await response.success(f"Your prefix has been updated to: ``{new_prefix}``")
