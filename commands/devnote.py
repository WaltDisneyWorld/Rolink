from resources.module import get_module
get_user = get_module("roblox", attrs=["get_user"])

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="devnote", category="Developer", permissions={
		"owner_only": True
	}, arguments=[
		{
			"prompt": "Please specify the user.",
			"type": "user",
			"name": "user"
		},
		{
			"prompt": "Please specify the note. Leave blank to remove the note.",
			"type": "string",
			"name": "note",
			"optional": True
		}
	])
	async def devnote(message, response, args, prefix):
		"""creates a developer note for the user"""

		note = args.parsed_args.get("note")

		user, _ = await get_user(author=args.parsed_args["user"])
		await user.fill_missing_details()

		if not user.is_verified:
			await response.error(f'{args.parsed_args["user"]} is not verified.')

		if note:

			await r.table("notes").insert({
				"id": user.id,
				"note": note
			}, conflict="update").run()

			await response.success("Successfully **set** this user's note.")

		else:

			if await r.table("notes").get(user.id).run():
				  await r.table("notes").get(user.id).delete().run()
				  await response.success("Successfully **deleted** this user's note.")
