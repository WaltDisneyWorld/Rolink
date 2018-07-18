from discord import Embed



async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")

	@command(name="invite")
	async def invite(message, response, args, prefix):
		"""invite the bot to your server"""

		me = message.guild.me

		embed = Embed(description = f"**To add {me.mention} to your server, click " \
			"the link below:\nhttps://discordapp.com/oauth2/authorize?" \
			f"client_id={client.user.id}&scope=bot&permissions=469888209\n" \
			"Support server: https://discord.gg/wBndznK**")

		embed.set_author(name=me.name, icon_url=me.avatar_url)

		await response.send(embed=embed)
