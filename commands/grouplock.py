async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="grouplock", arguments=[
		{
			"prompt": "Would you like to **enable** or **disable** the grouplock?",
			"type": "choice",
			"choices": {"enable", "disable"},
			"name": "enabled",
		}
	], category="Premium", permissions={"raw": "manage_guild"}, examples=[
		"grouplock disable",
		"grouplock enable"
	])
	async def grouplock(message, response, args, prefix):
		"""locks server joining only to members of your group"""

		guild = message.guild

		enabled = args.parsed_args["enabled"] == "enable"

		await r.table("guilds").insert({
			"id": str(guild.id),
			"groupLocked": enabled
		}, conflict="update").run()

		await response.success(f'Successfully **{enabled and "enabled" or "disabled"}** ' \
			"the grouplock.")
