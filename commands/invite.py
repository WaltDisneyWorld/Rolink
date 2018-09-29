from discord import Embed



async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="invite")
	async def invite(message, response, args, prefix):
		"""invite the bot to your server"""

		me = message.guild.me

		embed = Embed(description = f"**To add **Bloxlink** to your server, click " \
			"the link below:\nhttps://blox.link/invite\n" \
			"Support server: https://discord.gg/wBndznK**")

		embed.set_author(name=me.name, icon_url=me.avatar_url)

		await response.send(embed=embed)
