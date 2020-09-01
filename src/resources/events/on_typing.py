from ..structures.Bloxlink import Bloxlink
from discord.errors import NotFound, Forbidden
from discord import Member, Object
from discord.utils import find
from ..constants import DEFAULTS, RELEASE
import asyncio

cache_get, cache_set = Bloxlink.get_module("cache", attrs=["get", "set"])
guild_obligations = Bloxlink.get_module("roblox", attrs=["guild_obligations"])
get_board, get_options = Bloxlink.get_module("trello", attrs=["get_board", "get_options"])
is_premium = Bloxlink.get_module("utils", attrs=["is_premium"])


@Bloxlink.module
class ChannelTypingEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_typing(channel, user, when):
            if RELEASE == "PRO":
                if isinstance(user, Member):
                    guild = user.guild

                    if self.redis:
                        donator_profile, _ = await is_premium(Object(id=guild.owner_id), guild=guild)

                        if donator_profile.features.get("premium"):
                            if await cache_get(f"channel_typing:{guild.id}", user.id, primitives=True):
                                return

                            if await cache_get("persistRoles", guild.id, primitives=True) is None:
                                guild_data = await cache_get("guild_data", guild.id)

                                if not guild_data:
                                    guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {"id": str(guild.id)}

                                    trello_board = await get_board(guild=guild, guild_data=guild_data)
                                    trello_options = {}

                                    if trello_board:
                                        trello_options, _ = await get_options(trello_board)
                                        guild_data.update(trello_options)

                                await cache_set("guild_data", guild.id, guild_data)
                                await cache_set("persistRoles", guild.id, bool(guild_data.get("persistRoles", DEFAULTS.get("persistRoles"))))


                            if await cache_get("persistRoles", guild.id, primitives=True):
                                await cache_set(f"channel_typing:{guild.id}", user.id, True, expire=7200)

                                if not find(lambda r: r.name == "Bloxlink Bypass", user.roles):
                                    await guild_obligations(user, guild, dm=False, event=False)
