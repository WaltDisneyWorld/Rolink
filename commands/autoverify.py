async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="autoverify", arguments=[
		{
			"prompt": "Would you like to **enable** or **disable** auto-verification?",
			"type": "choice",
			"choices": {"enable", "disable"},
			"name": "enabled",
		}
	], category="Administration", permissions={"raw": "manage_guild"})
	async def autoverify(message, response, args):
		"""gives verified role/nickname to new members"""

		guild = message.guild

		enabled = args.parsed_args["enabled"] == "enable"

		await r.table("guilds").insert({
			"id": str(guild.id),
			"autoVerification": enabled
		}, conflict="update").run()

		await response.success(f'Successfully **{enabled and "enabled" or "disabled"}** ' \
			"auto-verification.")
