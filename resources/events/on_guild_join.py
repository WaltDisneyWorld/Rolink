from config import DEFAULTS

from discord.errors import Forbidden
from discord import Embed


from resources.module import get_module
is_premium = get_module("utils", attrs=["is_premium"])

from os import environ as env

RELEASE = env.get("RELEASE", 0)

text = [
	":wave: Welcome to Bloxlink! <:bloxlink:372437348539170817>",
	":exclamation: To view all commands, say ``!help``.",
	":gear: To set up your server with Bloxlink, use ``!setup``.  To set up binds, say ``!bind``.",
	":sparkles: Check out <https://github.com/bloxlink/docs> for cool things you can do with Bloxlink!",
	":question: If you require assistance with Bloxlink, don't hesitate to join the support server! https://discord.gg/g4Z2Pbx",
	"<:twitter:450703269652725760> Why not follow us on Twitter? <https://twitter.com/bloxlink>"
]

text = "\n\n".join(text)


class OnGuildJoin:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")
		self.r = kwargs.get("r")

	async def setup(self):

		@self.client.event
		async def on_guild_join(guild):

			if RELEASE == "PRO":
				profile = await is_premium(guild)

				if not profile.is_premium:
					return await guild.leave()

			await self.r.table("guilds").insert({
				"id": str(guild.id),
				**DEFAULTS
			}, conflict="update").run()


			channels = []

			for channel in guild.text_channels:
				permissions = channel.permissions_for(guild.me)

				if permissions.send_messages and permissions.read_messages:
					channels.append(channel)

			if channels:
				highest_channel = sorted(channels, key=lambda c: c.position, reverse=False)[0]

				if highest_channel:
					"""
					owner_dm_text = "**Thanks for adding Bloxlink to your server!**\n\nHere are a few things " \
						"you should know:\n**1).** The default prefix for Bloxlink is ``!`` or ``@Bloxlink``" \
						"\n**2).** You can set up your server with ease by using the ``!setup`` command\n" \
						"**3).** You can join our official Discord server at https://discord.gg/g4Z2Pbx"

					embed = Embed(description=text)
					embed.set_author(name=client.user.name, icon_url=client.user.avatar_url)
					"""

					try:
						await highest_channel.send(text)
					except Forbidden:
						pass

def new_module():
	return OnGuildJoin
