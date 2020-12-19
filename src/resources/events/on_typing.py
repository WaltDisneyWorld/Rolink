from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from discord.errors import NotFound, Forbidden
from discord import Member, Object
from discord.utils import find
from ..constants import DEFAULTS, RELEASE # pylint: disable=import-error
from ..exceptions import RobloxDown, CancelCommand # pylint: disable=import-error

cache_get, cache_set, get_guild_value = Bloxlink.get_module("cache", attrs=["get", "set", "get_guild_value"])
guild_obligations = Bloxlink.get_module("roblox", attrs=["guild_obligations"])
get_board, get_options = Bloxlink.get_module("trello", attrs=["get_board", "get_options"])
get_features = Bloxlink.get_module("premium", attrs=["get_features"])


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
                        donator_profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)

                        if donator_profile.features.get("premium"):
                            if await cache_get(f"channel_typing:{guild.id}", user.id, primitives=True):
                                return

                            persist_roles = await get_guild_value(guild, ["persistRoles", DEFAULTS.get("persistRoles")])

                            if persist_roles:
                                await cache_set(f"channel_typing:{guild.id}", user.id, True, expire=7200)

                                if not find(lambda r: r.name == "Bloxlink Bypass", user.roles):
                                    try:
                                        await guild_obligations(user, guild, dm=False, event=False)
                                    except (RobloxDown, CancelCommand):
                                        pass
