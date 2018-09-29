async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="joindm", arguments=[
		{
			"prompt": "Would you like to **enable** or **disable** join messages?",
			"type": "choice",
			"choices": {"enable", "disable"},
			"name": "enabled",
		}
	], category="Welcoming", permissions={"raw": "manage_guild"}, examples=[
		"joindm enable",
		"joindm disable"
	])
	async def joindm(message, response, args, prefix):
		"""messages users on server join"""

		guild = message.guild

		enabled = args.parsed_args["enabled"] == "enable"

		await r.table("guilds").insert({
			"id": str(guild.id),
			"joinDM": enabled
		}, conflict="update").run()

		await response.success(f'Successfully **{enabled and "enabled" or "disabled"}** ' \
			"join messages!")
