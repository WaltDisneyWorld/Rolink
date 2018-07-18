from discord.errors import Forbidden
from discord import Embed

text = [
	":wave: Welcome to Bloxlink! <:bloxlink:372437348539170817>",
	":exclamation: To view all commands, say ``!help``.",
	":gear: To set up your server with Bloxlink, use ``!setup``.  To set up binds, say ``!settings server`` and then ``binds``.",
	":sparkles: To turn on automatic member verification, say ``!autoverify``. If you have Bloxlink Premium (<https://selly.gg/u/bloxlink>), say ``!autoroles`` to turn on automatic member roles.",
	":question: If you require assistance with Bloxlink, don't hesitate to join the support server! https://discord.gg/g4Z2Pbx",
	"<:twitter:450703269652725760> Why not follow us on Twitter? <https://twitter.com/bloxlink>"
]

text = "\n\n".join(text)



async def setup(client, *args, **kwargs):

	@client.event
	async def on_guild_join(guild):
		channels = []

		for channel in guild.text_channels:
			permissions = channel.permissions_for(guild.me)

			if permissions.send_messages and permissions.read_messages:
				channels.append(channel)

		if channels:
			highest_channel = sorted(channels, key=lambda c: c.position, reverse=True)[0]

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
