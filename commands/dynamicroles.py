async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="dynamicroles", arguments=[
		{
			"prompt": "Would you like to **enable** or **disable** dynamic roles?",
			"type": "choice",
			"choices": {"enable", "disable"},
			"name": "enabled",
		}
	], category="Administration", permissions={"raw": "manage_guild"})
	async def dynamicroles(message, response, args, prefix):
		"""automatically attempts to create missing group roles"""

		guild = message.guild

		enabled = args.parsed_args["enabled"] == "enable"

		await r.table("guilds").insert({
			"id": str(guild.id),
			"dynamicRoles": enabled
		}, conflict="update").run()

		await response.success(f'Successfully **{enabled and "enabled" or "disabled"}** ' \
			"dynamic roles.")
