from resources.structures.Argument import Argument
from discord.errors import Forbidden, NotFound

from resources.module import get_module
parse_message = get_module("commands", attrs=["parse_message"])

class OnMessage:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")
		self.r = kwargs.get("r")

	async def setup(self):

		@self.client.event
		async def on_message(message):
			author = message.author

			if author.bot:
				return
			if not hasattr(message, "guild"):
				return
			if not message.guild:
				return
			if not hasattr(message, "channel"):
				return
			if not message.channel:
				return

			guild = message.guild
			channel = message.channel

			is_command = await parse_message(message)

			if not is_command and not Argument.is_in_prompt(author):
				guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {}

				if str(guild_data.get("verifyChannel", "1")) == str(channel.id):
					try:
						await message.delete()
					except (Forbidden, NotFound):
						pass


def new_module():
	return OnMessage