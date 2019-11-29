from io import StringIO
from discord.errors import Forbidden, HTTPException, DiscordException, NotFound
from discord import File
from ..exceptions import PermissionError, Message
from ..structures.Bloxlink import Bloxlink
from config import PREFIX, REACTIONS # pylint: disable=E0611
import asyncio

loop = asyncio.get_event_loop()


class ResponseLoading:
	def __init__(self, response, backup_text):
		self.response = response
		self.original_message = response.message
		self.reaction = None
		self.channel = response.message.channel

		self.reaction_success = False
		self.from_reaction_fail_msg = None

		self.backup_text = backup_text

	@staticmethod
	def _check_reaction(message):
		def _wrapper(reaction, user):
			return reaction.me and str(reaction) == REACTIONS["LOADING"] and message.id == reaction.message.id

	async def _send_loading(self):
		try:
			future = Bloxlink.wait_for("reaction_add", check=self._check_reaction(self.original_message), timeout=60)

			try:
				await self.original_message.add_reaction(REACTIONS["LOADING"])
			except (Forbidden, HTTPException):
				try:
					self.from_reaction_fail_msg = await self.channel.send(self.backup_text)
				except Forbidden:
					raise PermissionError
			else:
				reaction, _ = await future
				self.reaction_success = True
				self.reaction = reaction

		except NotFound:
			pass

	async def _remove_loading(self, errored):
		try:
			if self.reaction_success:
				for reaction in self.original_message.reactions:
					if reaction == self.reaction:
						try:
							async for user in reaction.users():
								await self.original_message.remove_reaction(self.reaction, user)
						except NotFound:
							pass

				if errored:
					await self.original_message.add_reaction(REACTIONS["ERROR"])
				else:
					await self.original_message.add_reaction(REACTIONS["DONE"])
			elif self.from_reaction_fail_msg is not None:
				await self.from_reaction_fail_msg.delete()
		except NotFound:
			pass

	def __enter__(self):
		loop.create_task(self._send_loading())
		return self

	def __exit__(self, tb_type, tb_value, traceback):
		if (tb_type is None) or (tb_type == Message):
			loop.create_task(self._remove_loading(errored=False))
		else:
			loop.create_task(self._remove_loading(errored=True))

	async def __aenter__(self):
		await self._send_loading()

	async def __aexit__(self, tb_type, tb_value, traceback):
		if (tb_type is None) or (tb_type == Message):
			await self._remove_loading(errored=False)
		else:
			await self._remove_loading(errored=True)




@Bloxlink.loader
class Response:
	def __init__(self, _, CommandArgs):
		self.webhook_only = CommandArgs.guild_data.get("customBot", {}).get("enabled")

		self.message = CommandArgs.message
		self.author = CommandArgs.message.author
		self.channel = CommandArgs.message.channel
		self.prompt = None
		self.args = CommandArgs

	def loading(self, text="Please wait until the operation completes."):
		return ResponseLoading(self, text)

	async def send(self, content=None, embed=None, on_error=None, dm=False, no_dm_post=False, strict_post=False, files=None):
		channel = dm and self.author or self.channel

		verified_webhook = False
		if self.webhook_only:
			bot_name = self.args.guild_data["customBot"].get("name", "Bloxlink")
			bot_avatar = self.args.guild_data["customBot"].get("avatar", "")

			try:
				for webhook in await self.channel.webhooks():
					if (webhook.user and webhook.user.id) == self.args.client.user.id:
						verified_webhook = webhook
			except Forbidden:
				self.webhook_only = False

			if not verified_webhook:
				# try to create the webhook
				try:
					verified_webhook = await self.channel.create_webhook(name="Bloxlink Webhooks")
				except Forbidden:
					self.webhook_only = False
					verified_webhook = False

					try:
						await channel.send("Customized Bot is enabled, but I couldn't "
						"create the webhook! Please give me the ``Manage Webhooks`` permission.")
					except Forbidden:
						pass


		if embed and not dm and not embed.color:
			#embed.color = self.guild.me.color
			embed.color = 0x36393E
		try:
			if verified_webhook and not dm:
				msg = await verified_webhook.send(embed=embed, content=content,
				wait=True, username=bot_name, avatar_url=bot_avatar)
			else:
				msg = await channel.send(embed=embed, content=content, files=files)
			if dm and not no_dm_post:
				if verified_webhook:
					await verified_webhook.send(content=self.author.mention + ", **check your DMs!**",
						username=bot_name, avatar_url=bot_avatar
					)
				else:
					await self.channel.send(self.author.mention + ", **check your DMs!**")
			return msg

		except Forbidden:
			channel = not strict_post and (dm and self.channel or self.author) or channel # opposite channel

			try:
				if verified_webhook and not dm:
					return await verified_webhook.send(content=on_error or content, embed=embed,
					wait=True, username=bot_name, avatar_url=bot_avatar)

				return await channel.send(content=on_error or content, embed=embed, files=files)
			except Forbidden:
				try:
					if dm:
						if verified_webhook and not dm:
							await verified_webhook.send(content=self.author.mention + ", I was unable to DM you. "
								"Please check your privacy settings and try again.", username=bot_name, avatar_url=bot_avatar)
						else:
							await self.channel.send(content=self.author.mention + ", I was unable to DM you. "
							"Please check your privacy settings and try again.")
					else:
						await self.author.send(f'You attempted to use command {self.args.command_name} in '
						f'{self.channel.mention}, but I was unable to post there. ' \
							"You may need to grant me the ``Embed Links`` permission.", files=files)
					return False

				except Forbidden:
					return False

		except HTTPException:
			# check for embed, THEN do pagination
			if self.webhook_only:
				self.webhook_only = False
				return await self.send(content=content, embed=embed, on_error=on_error, dm=dm, no_dm_post=no_dm_post, strict_post=strict_post, files=files)

			else:
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
					file = StringIO()
					file.write(str([x.get("value") for x in embed.to_dict()["fields"]]), "utf-8") # temp

					try:
						await self.channel.send(
							files=[
								File(file, filename="data.txt"),
							]
						)
					except DiscordException:
						pass

					finally:
						file.close()

				else:
					raise HTTPException

		return True

	async def error(self, text, *, embed=None, embed_color=0xE74C3C, dm=False, no_dm_post=False):
		emoji = self.webhook_only and ":cry:" or "<:BloxlinkError:506622933226225676>"

		if embed and not dm:
			embed.color = embed_color

		return await self.send(f"{emoji} {text}", embed=embed, dm=dm, no_dm_post=no_dm_post)

	async def success(self, success, embed=None, embed_color=0x36393E, dm=False, no_dm_post=False):
		emoji = self.webhook_only and ":thumbsup:" or "<:BloxlinkSuccess:506622931791773696>"
		if embed and not dm:
			embed.color = embed_color

		return await self.send(f"{emoji} {success}", embed=embed, dm=dm, no_dm_post=no_dm_post)

	async def silly(self, text, embed=None, embed_color=0x36393E, dm=False, no_dm_post=False):
		emoji = self.webhook_only and ":sweat_smile:" or "<:BloxlinkSweaty:506622933502918656>"
		if embed and not dm:
			embed.color = embed_color

		return await self.send(f"{emoji} {text}", embed=embed, dm=dm, no_dm_post=no_dm_post)