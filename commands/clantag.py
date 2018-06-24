from resources.modules.utils import get_nickname
from discord.errors import Forbidden

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="clantag", arguments=[
		{
			"prompt": "What would you like your clan tag to be?",
			"type": "string",
			"name": "clan_tag",
			"min": 1,
			"max": 10
		}
	], category="Account")
	async def on_clan_tag(message, response, args):
		"""assigns a clan tag for the server"""

		author = message.author
		guild = message.guild

		clan_tags = (await r.table("users").get(str(author.id)).run() or {}).get("clanTags", {})

		clan_tags[str(guild.id)] = args.parsed_args["clan_tag"]

		await r.table("users").insert({
			"id": str(author.id),
			"clanTags": clan_tags
		}, conflict="update").run()

		msg = await response.success("Saved your new clan tag! If this server supports " \
			"clan tags, and you're linked to the bot, you'll be given it automatically.")

		nickname = await get_nickname(author)
		if nickname:
			if author.nick != nickname:
				try:
					await author.edit(nick=nickname)
					msg.edit(content="Saved your new clan tag! Your nickname has also been updated " \
						"successfully.")
				except Forbidden:
					if msg:
						await msg.edit(content=msg.content + "\n**Error:** I was unable to edit your nickname.")








		
