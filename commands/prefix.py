async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="prefix")
	async def prefix(message, response, args, prefix):
		"""views the prefix used for Bloxlink"""

		guild = message.guild
		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

		prefix = guild_data.get("prefix") or "!"

		await response.send(f"Your prefix used for Bloxlink: ``{prefix}``")
