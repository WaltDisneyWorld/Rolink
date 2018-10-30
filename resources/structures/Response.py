from discord.errors import Forbidden, HTTPException, DiscordException
from resources.module import get_loader

from discord import File
from io import BytesIO

Paginate = get_loader("paginate")

class Response:
	def __init__(self, message, command="N/A"):
		self.message = message
		self.channel = message.channel
		self.author = message.author
		self.command = command
		self.guild = message.guild

	async def send(self, content=None, embed=None, on_error=None, dm=False, no_dm_post=False, strict_post=False, files=None):
		channel = dm and self.author or self.channel

		if embed and not dm and not embed.color:
			#embed.color = self.guild.me.color
			embed.color = 0x36393E
		try:
			msg = await channel.send(embed=embed, content=content, files=files)
			if dm and not no_dm_post:
				await self.channel.send(self.author.mention + ", **check your DMs!**")
			return msg

		except Forbidden:
			channel = not strict_post and (dm and self.channel or self.author) or channel # opposite channel

			try:
				#if embed and dm:
					#embed.color = self.guild.me.color

				return await channel.send(content=on_error or content, embed=embed, files=files)
			except Forbidden:
				try:
					if dm:
						await self.channel.send(content= self.author.mention + ", I was unable to DM you. "
						"Please check your privacy settings and try again.")
					else:
						await self.author.send(f'You attempted to use command {self.command} in '
						f'{self.channel.mention}, but I was unable to post there. ' \
							"You may need to grant me the ``Embed Links`` permission.", files=files)
					return False

				except Forbidden:
					return False
		
		except HTTPException:
			# check for embed, THEN do pagination
			if embed:
				"""
				paginate = Paginate(embed=embed, field_limit=5)
				async with paginate.get_embed_field() as field:
					pass
				"""
				"""
				paginate = Paginate(message=self.message, embed=embed, smart_fields=True)
				await paginate.start()
				"""
				file = BytesIO()
				file.write(bytes(str([x.get("value") for x in embed.to_dict()["fields"]]), "utf-8")) # temp

				try:
					await self.channel.send(
						files=[
							File(file.getvalue(), filename="binds.txt"),
						]
					)
				except DiscordException:
					pass

				finally:
					file.close()

			else:
				raise HTTPException

		return True

	async def error(self, error, embed=None, embed_color=0xE74C3C, dm=False, no_dm_post=False):
		if embed and not dm:
			embed.color = embed_color

		return await self.send("<:BloxlinkSad:506622933158985728> " + error, embed=embed, dm=dm, no_dm_post=no_dm_post)

	async def success(self, success, embed=None, embed_color=0x36393E, dm=False, no_dm_post=False):
		if embed and not dm:
			embed.color = embed_color

		return await self.send("<:BloxlinkSuccess:506622931791773696> " + success, embed=embed, dm=dm, no_dm_post=no_dm_post)

	async def text(self, text, dm=False, no_dm_post=False):
		return await self.send(text, dm=dm, no_dm_post=no_dm_post)
  