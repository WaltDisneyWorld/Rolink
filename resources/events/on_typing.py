from asyncio import sleep, TimeoutError
from discord.errors import NotFound
from discord import Member

from resources.module import get_module
clear_user_from_cache, give_roblox_stuff = get_module("roblox", attrs=[
	"clear_user_from_cache",
	"give_roblox_stuff"
	]
)
is_premium = get_module("utils", attrs=["is_premium"])

from resources.exceptions import BloxlinkException
from aiohttp.client_exceptions import ClientOSError


class OnTyping:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")
		self.loop = self.client.loop
		self.r = kwargs.get("r")

	async def setup(self):

		@self.client.event
		async def on_typing(channel, user, when):

			if not isinstance(user, Member):
				return

			if user.bot:
				return

			await clear_user_from_cache(author=user)

			try:
				profile = await is_premium(guild=channel.guild)

				if profile.is_premium:
					guild_data = await self.r.table("guilds").get(str(channel.guild.id)).run() or {}
					persist_roles = guild_data.get("persistRoles")

					if persist_roles:
						await give_roblox_stuff(user, complete=True)

			except (NotFound, TypeError, BloxlinkException, ClientOSError, TimeoutError):
				pass

def new_module():
	return OnTyping
