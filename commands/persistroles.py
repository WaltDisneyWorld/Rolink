async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="persistroles", arguments=[
		{
			"prompt": "Would you like to **enable** or **disable** persist-roles?",
			"type": "choice",
			"choices": {"enable", "disable"},
			"name": "enabled",
		}
	], category="Premium", permissions={"raw": "manage_guild"})
	async def persistroles(message, response, args, prefix):
		"""updates roles/nickname on typing"""

		guild = message.guild

		enabled = args.parsed_args["enabled"] == "enable"

		await r.table("guilds").insert({
			"id": str(guild.id),
			"persistRoles": enabled
		}, conflict="update").run()

		await response.success(f'Successfully **{enabled and "enabled" or "disabled"}** ' \
			"persist-roles.")
