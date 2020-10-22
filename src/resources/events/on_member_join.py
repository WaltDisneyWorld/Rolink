from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..exceptions import RobloxDown # pylint: disable=import-error

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

            try:
                await guild_obligations(member, guild, cache=False, dm=True, event=True)
            except RobloxDown:
                pass
