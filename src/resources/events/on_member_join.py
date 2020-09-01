from ..structures.Bloxlink import Bloxlink
from ..exceptions import UserNotVerified, BloxlinkBypass, PermissionError, RobloxAPIError, Error, CancelCommand, RobloxDown
from ..constants import DEFAULTS, SERVER_INVITE, RELEASE
from discord.errors import Forbidden, HTTPException, NotFound

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

            await guild_obligations(member, guild, cache=False, dm=True, event=True)
