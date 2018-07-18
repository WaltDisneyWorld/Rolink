async def check_age(message, age, previous_args):
	return age.isdigit() and int(age), "You must specify an age limit in days (int)"

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="agelimit", aliases=["setagelimit", "setaccountage", "setaccountlimit"], arguments=[
		{
			"prompt": "How many days should new joiners be? Set ``0`` to remove the limit.",
			"type": "number",
			"name": "days",
			#"check": check_age
		}
	], category="Premium", permissions={"raw": "manage_guild"})
	async def agelimit(message, response, args, prefix):
		"""enforces an age limit for the server in days"""

		guild = message.guild

		age = args.parsed_args["days"]

		await r.table("guilds").insert({
			"id": str(guild.id),
			"ageLimit": age
		}, conflict="update").run()

		await response.success(f"Successfully set the age limit to ``{age}`` days!")
