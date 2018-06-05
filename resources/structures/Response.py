from discord.errors import Forbidden

class Response:
	def __init__(self, message, command="N/A"):
		self.message = message
		self.channel = message.channel
		self.author = message.author
		self.command = command
	async def send(self, content=None, embed=None, on_error=None, dm=False):
		channel = dm and self.author or self.channel
		try:
			await channel.send(embed=embed, content=content)
		except Forbidden:
			# try to send on_error
			# if that fails, try to post in opposite channel that it couldn't send a msg
			try:
				await channel.send(content=on_error or content)
			except Forbidden:
				channel = dm and self.channel or self.author # opposite channel
				try:
					if dm:
						await self.channel.send(content=str(self.author) + ", I was unable to DM you. "
						"Please check your privacy settings and try again.")
					else:
						await self.author.send(f'You attempted to use command {self.command} in '
						f'{self.channel.mention}, but I was unable to post there. ' \
							"You may need to grant me the ``Embed Links`` permission.")
				except Forbidden:
					pass
	async def error(self, error, embed=None, embed_color=0xE74C3C):
		if embed:
			embed.color = embed_color
		await self.send(":exclamation: " + error, embed=embed)
	async def success(self, success, embed=None, embed_color=0x3CE754):
		if embed:
			embed.color = embed_color
		await self.send(":thumbsup: " + success, embed=embed)
	async def text(self, text, embed=None):
		await self.send(text, embed=embed)
  