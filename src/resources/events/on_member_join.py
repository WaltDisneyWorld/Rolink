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
                trello_options, _ = get_options(trello_board)

            group_roles = (trello_options.get("autoroles", "")).lower() or guild_data.get("autoRoles", True)
            group_roles = group_roles != "false"

            verify_role = (trello_options.get("autoVerification", "")).lower() or guild_data.get("autoVerification", True)
            verify_role = verify_role != "false"

            if verify_role:
                try:
                    added, removed, nickname, errors, roblox_user = await update_member(
                        member,
                        guild             = guild,
                        guild_data        = guild_data,
                        group_roles       = group_roles,
                        verify_role       = verify_role,
                        roles             = True,
                        nickname          = True,
                        trello_options    = trello_options)

                except UserNotVerified:
                    pass
