async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="ignorechannel", permissions={
		"raw": "manage_guild"}
	)
	async def ignorechannel(message, response, args, prefix):
		"""toggles commands from being used by non-admins in the current channel"""

		guild = message.guild
		channel = message.channel

		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

		ignored_channels = guild_data.get("ignoredChannels", {})
		ignored_channels[str(channel.id)] = not ignored_channels.get(str(channel.id), True)

		disabled = bool(ignored_channels[str(channel.id)])

		await r.table("guilds").insert({
			"id": str(guild.id),
			"ignoredChannels": ignored_channels
		}, conflict="update").run()

		if disabled:
			await response.success("Successfully **disabled** commands from this channel by non-admins.\n"
				"If you would like to grant a certain person access to use commands, give them a role called "
				"``Bloxlink Bypass``."
			)
		else:
			await response.success("Successfully **enabled** commands to be used by everyone in this channel.")