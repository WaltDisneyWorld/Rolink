from config import TEMPLATES

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="welcomemessage", aliases=["welcomemsg"], arguments=[
		{
			"prompt": "The user will get this message if !joindm is enabled, " \
				"and from !verify messages.\n\nPlease specify a message using the templates: " \
				f"```{TEMPLATES}```",
			"type": "string",
			"name": "msg",
			"ignoreFormatting": True
		}
	], category="Welcoming", permissions={"raw": "manage_guild"})
	async def welcomemessage(message, response, args, prefix):
		"""uses this message for joins/verifications"""

		guild = message.guild

		await r.table("guilds").insert({
			"id": str(guild.id),
			"welcomeMessage": args.parsed_args["msg"]
		}, conflict="update").run()

		await response.success("Successfully **saved** your new welcome message!")
