from resources.module import get_module
parse_message = get_module("commands", attrs=["parse_message"])



async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")
	client = kwargs.get("client")

	@command(name="keysearch", category="Developer", permissions={
		"owner_only": True
	}, arguments=[
		{
			"prompt": "Please specify the key.",
			"type": "string",
			"name": "key"
		}
	])
	async def keysearch(message, response, args, prefix):
		"""checks who redeemed the key"""

		key = args.parsed_args["key"]
		user = None

		feed = await r.table("users").filter(
			lambda redeemed: redeemed.has_fields({'redeemed': {key: True}})
		).run()

		while await feed.fetch_next():
			user = await feed.next()

			discord_tag = str(await client.get_user_info(int(user["id"])))

			await response.send(f'User that redeemed code: {user["id"]} | {discord_tag}')

			message.content = f'{prefix}getinfo {user["id"]}'
			await parse_message(message)

			break

		if not user:
			key = await r.table("keys").get(key).run()

			if key:
				await response.send(f'This key was never redeemed, but is valid for **{key["duration"]}** days.')
			else:
				await response.send("This key was never redeemed, and is not valid.")
		