from ..structures.Bloxlink import Bloxlink
from resources.exceptions import UserNotVerified

update_member = Bloxlink.get_module("roblox", attrs="update_member")

@Bloxlink.module
class MemberJoinEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_member_join(member):
            guild = member.guild

            guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {"id": str(guild.id)}

            group_roles = guild_data.get("autoRoles", True)
            verify_role = group_roles or guild_data.get("autoVerification", True)

            if verify_role:
                try:
                    added, removed, nickname, errors, roblox_user = await update_member(
                        member,
                        guild             = guild,
                        guild_data        = guild_data,
                        group_roles       = group_roles,
                        verify_role       = verify_role,
                        roles             = True,
                        nickname          = True)
                except UserNotVerified:
                    pass
