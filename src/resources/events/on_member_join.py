from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..exceptions import RobloxDown, CancelCommand # pylint: disable=import-error
from ..constants import DEFAULTS # pylint: disable=import-error

cache_get, cache_set = Bloxlink.get_module("cache", attrs=["get", "set"])
get_board, get_options = Bloxlink.get_module("trello", attrs=["get_board", "get_options"])
guild_obligations = Bloxlink.get_module("roblox", attrs=["guild_obligations"])


@Bloxlink.module
class MemberJoinEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_member_join(member):
            guild = member.guild

            if member.bot:
                return

            if self.redis:
                if await cache_get("autoRoles", guild.id, primitives=True) is None and await cache_get("autoVerification", guild.id, primitives=True) is None:
                    guild_data = await cache_get("guild_data", guild.id)

                    if not guild_data:
                        guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {"id": str(guild.id)}

                        trello_board = await get_board(guild=guild, guild_data=guild_data)
                        trello_options = {}

                        if trello_board:
                            trello_options, _ = await get_options(trello_board)
                            guild_data.update(trello_options)

                    await cache_set("guild_data", guild.id, guild_data)
                    await cache_set("autoRoles", guild.id, bool(guild_data.get("autoRoles", DEFAULTS.get("autoRoles"))))
                    await cache_set("autoVerification", guild.id, bool(guild_data.get("autoVerification", DEFAULTS.get("autoVerification"))))

                auto_roles = await cache_get("autoRoles", guild.id, primitives=True)
                auto_verification = await cache_get("autoRoles", guild.id, primitives=True)

                if auto_verification or auto_roles:
                    try:
                        await guild_obligations(member, guild, cache=False, dm=True, event=True)
                    except (RobloxDown, CancelCommand):
                        pass
