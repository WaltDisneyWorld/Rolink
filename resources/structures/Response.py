from discord.errors import Forbidden

class Response:
	def __init__(self, message, command="N/A"):
		self.message = message
		self.channel = message.channel
		self.author = message.author
		self.command = command
		self.guild = message.guild

	async def send(self, content=None, embed=None, on_error=None, dm=False, no_dm_post=False, strict_post=False):
		channel = dm and self.author or self.channel

		if embed and not dm and not embed.color:
			embed.color = self.guild.me.color
		try:
			msg = await channel.send(embed=embed, content=content)
			if dm and not no_dm_post:
				await self.channel.send(self.author.mention + ", **check your DMs!**")
			return msg

		except Forbidden:
			channel = not strict_post and (dm and self.channel or self.author) or channel # opposite channel

			try:
				if embed and dm:
					embed.color = self.guild.me.color

				return await channel.send(content=on_error or content, embed=embed)
			except Forbidden:
				try:
					if dm:
						await self.channel.send(content= self.author.mention + ", I was unable to DM you. "
						"Please check your privacy settings and try again.")
					else:
						await self.author.send(f'You attempted to use command {self.command} in '
						f'{self.channel.mention}, but I was unable to post there. ' \
							"You may need to grant me the ``Embed Links`` permission.")
					return False

				except Forbidden:
					return False

		return True

	async def error(self, error, embed=None, embed_color=0xE74C3C, dm=False, no_dm_post=False):
		if embed and not dm:
			embed.color = embed_color

		return await self.send(":anguished: " + error, embed=embed, dm=dm, no_dm_post=no_dm_post)

	async def success(self, success, embed=None, embed_color=0x2ECC71, dm=False, no_dm_post=False):
		if embed and not dm:
			embed.color = embed_color

		return await self.send(":ok_hand: " + success, embed=embed, dm=dm, no_dm_post=no_dm_post)

	async def text(self, text, dm=False, no_dm_post=False):
		return await self.send(text, dm=dm, no_dm_post=no_dm_post)
  