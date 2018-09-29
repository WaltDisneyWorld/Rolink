from discord.errors import Forbidden

from resources.module import get_module
get_nickname = get_module("roblox", attrs=["get_nickname"])
post_event = get_module("utils", attrs=["post_event"])

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="clantag", arguments=[
		{
			"prompt": "What would you like your clan tag to be?",
			"type": "string",
			"name": "clan_tag",
			"min": 1,
			"max": 10,
			"optional": True
		}
	], category="Account", examples=[
		"clantag awesome"
	])
	async def on_clan_tag(message, response, args, prefix):
		"""assign a clan tag for the server. Leave the value blank to clear clan tag."""

		author = message.author
		guild = message.guild

		clan_tags = (await r.table("users").get(str(author.id)).run() or {}).get("clanTags", {})

		clan_tags[str(guild.id)] = args.parsed_args.get("clan_tag") or None

		msg = None

		await r.table("users").insert({
			"id": str(author.id),
			"clanTags": clan_tags
		}, conflict="update").run()

		if args.parsed_args.get("clan_tag"):
			msg = await response.success("Saved your new clan tag! If this server supports " \
				"clan tags, and you're linked to the bot, you'll be given it automatically. " \
				"Call this command again without arguments to remove the clan tag.")
		else:
			msg = await response.success("Successfully **removed** your clan tag.")

		nickname = await get_nickname(author)
		if nickname:
			if author.nick != nickname:
				try:
					await author.edit(nick=nickname)
				except Forbidden:
					if msg:
						await msg.edit(content=msg.content + "\n**Error:** I was unable to edit your nickname.")
						await post_event(
							"error",
							f"Failed to update {author.mention}'s nickname. Please ensure I have " \
								"the ``Manage Nickname`` permission, and drag my role above the other roles.",
							guild=guild,
							color=0xE74C3C
						)








		
