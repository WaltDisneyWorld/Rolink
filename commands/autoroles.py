async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="autoroles", arguments=[
		{
			"prompt": "Would you like to **enable** or **disable** auto-roles?",
			"type": "choice",
			"choices": {"enable", "disable"},
			"name": "enabled",
		}
	], category="Premium", permissions={"raw": "manage_guild"})
	async def autoroles(message, response, args):
		"""gives _all_ roles for each member that joins the server"""

		guild = message.guild

		enabled = args.parsed_args["enabled"] == "enable"

		await r.table("guilds").insert({
			"id": str(guild.id),
			"autoRoles": enabled
		}, conflict="update").run()

		await response.success(f'Successfully **{enabled and "enabled" or "disabled"}** ' \
			"auto-roles.")
