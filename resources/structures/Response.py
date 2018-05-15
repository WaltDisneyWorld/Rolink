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
		except:
			# try to send on_error
			# if that fails, try to post in opposite channel that it couldn't send a msg
			try:
				await channel.send(content=on_error or content)
			except:
				channel = dm and self.channel or self.author # opposite channel
				try:
					if dm:
						await self.channel.send(content=str(self.author) + ", I was unable to DM you. "
						"Please check your privacy settings and try again.")
					else:
						await self.author.send(f'You attempted to use command {self.command} in '
						f'{self.channel.mention}, but I was unable to post there.')
				except:
					pass
	async def error(self, error, embed=None, embed_color=0xE74C3C):
		if embed:
			embed.color = embed_color
		await self.send(error, embed=embed)
	   