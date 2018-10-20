from resources.structures.Argument import Argument
from config import MAGIC_ROLES
from discord.errors import Forbidden, NotFound
from discord.utils import find

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
			if not message.guild:
				return
			if not message.channel:
				return

			guild = message.guild
			channel = message.channel

			guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {}

			if guild_data.get("ignoredChannels", {}).get(str(channel.id)):
				if find(lambda r: r.name in MAGIC_ROLES, author.roles):
					is_command = await parse_message(message, guild_data=guild_data)
				elif guild.owner == author:
					is_command = await parse_message(message, guild_data=guild_data)
				else:
					perms = channel.permissions_for(author)

					if hasattr(perms, "manage_server") or hasattr(perms, "administrator"):
						is_command = await parse_message(message, guild_data=guild_data)
					else:
						return
			else:
				is_command = await parse_message(message, guild_data=guild_data)

			if not is_command and not Argument.is_in_prompt(author):

				if str(guild_data.get("verifyChannel", "1")) == str(channel.id):
					if not find(lambda r: r.name in MAGIC_ROLES, author.roles):
						try:
							await message.delete()
						except (Forbidden, NotFound):
							pass


def new_module():
	return OnMessage
