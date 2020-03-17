from ..structures.Bloxlink import Bloxlink
from resources.exceptions import UserNotVerified # pylint: disable=import-error

update_member = Bloxlink.get_module("roblox", attrs="update_member")
get_board, get_options = Bloxlink.get_module("trello", attrs=["get_board", "get_options"])

@Bloxlink.module
class MemberJoinEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_member_join(member):
            guild = member.guild
            guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {"id": str(guild.id)}
            trello_board = await get_board(guild=guild, guild_data=guild_data)
            trello_options = {}

            if trello_board:
                trello_options, _ = await get_options(trello_board)
                guild_data.update(trello_options)

            group_roles = guild_data.get("autoRoles", True)
            verify_enabled = guild_data.get("verifiedRoleEnabled", True)
            auto_verification = guild_data.get("autoVerification", group_roles)


            if auto_verification or group_roles:
                try:
                    added, removed, nickname, errors, roblox_user = await update_member(
                        member,
                        guild                   = guild,
                        guild_data              = guild_data,
                        group_roles             = group_roles,
                        skip_verify_role        = not auto_verification,
                        roles                   = True,
                        nickname                = True,
                        given_trello_options    = True)

                except UserNotVerified:
                    pass
