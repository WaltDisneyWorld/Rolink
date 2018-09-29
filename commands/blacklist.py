
async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="blacklist", category="Developer", permissions={
		"owner_only": True
	}, arguments=[
		{
			"prompt": "Please specify the user.",
			"type": "string",
			"name": "user"
		},
		{
			"prompt": "Please specify the reason.",
			"type": "string",
			"name": "reason",
			"optional": True
		}
	])
	async def blacklist(message, response, args, prefix):
		"""blacklists a user from using Bloxlink"""

		await r.table("blacklisted").insert({
			"id": args.parsed_args["user"],
			"reason": args.parsed_args.get("reason")
		}, conflict="update").run()

		await response.success("This user has been blacklisted.")
		