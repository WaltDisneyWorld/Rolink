from ..structures.Bloxlink import Bloxlink
from resources.exceptions import UserNotVerified # pylint: disable=import-error
from resources.constants import DEFAULTS
from discord.errors import Forbidden, HTTPException

update_member, get_nickname, get_user = Bloxlink.get_module("roblox", attrs=["update_member", "get_nickname", "get_user"])
get_board, get_options = Bloxlink.get_module("trello", attrs=["get_board", "get_options"])

@Bloxlink.module
class MemberJoinEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_member_join(member):
            guild = member.guild
            guild_data = await self.r.db("canary").table("guilds").get(str(guild.id)).run() or {"id": str(guild.id)}
            trello_board = await get_board(guild=guild, guild_data=guild_data)
            trello_options = {}

            if trello_board:
                trello_options, _ = await get_options(trello_board)
                guild_data.update(trello_options)


            group_roles = guild_data.get("autoRoles", DEFAULTS.get("autoRoles"))
            verify_enabled = guild_data.get("verifiedRoleEnabled", DEFAULTS.get("verifiedRoleEnabled"))
            auto_verification = guild_data.get("autoVerification", verify_enabled)

            verified_dm = guild_data.get("verifiedDM", DEFAULTS.get("welcomeMessage"))
            unverified_dm = guild_data.get("unverifiedDM")

            if auto_verification or group_roles:
                required_groups = guild_data.get("groupLocked") # TODO: integrate with Trello

                try:
                    added, removed, nickname, errors, roblox_user = await update_member(
                        member,
                        guild                   = guild,
                        guild_data              = guild_data,
                        group_roles             = group_roles,
                        roles                   = True,
                        nickname                = True,
                        given_trello_options    = True)

                except UserNotVerified:
                    if required_groups:
                        try:
                            await member.send(f"_Bloxlink Server-Lock_\nYou were kicked from **{guild.name}** for not being linked to Bloxlink.\n"
                                               "You may link your account by joining https://discord.gg/jJKWpsr and running the ``!verify`` command, then "
                                               "check your DMs. After, wait 10 minutes and try joining again.")
                        except Forbidden:
                            pass

                        try:
                            await member.kick(reason="SERVER-LOCK: not linked to Bloxlink")
                        except Forbidden:
                            pass

                        return

                    if unverified_dm:
                        unverified_dm = await get_nickname(member, unverified_dm, guild_data=guild_data, skip_roblox_check=True, is_nickname=False)

                        try:
                            await member.send(unverified_dm)
                        except (Forbidden, HTTPException):
                            pass
                else:
                    if required_groups:
                        for group_id, group_data in required_groups.items():
                            if not roblox_user.groups.get(group_id):
                                dm_message = group_data.get("dmMessage")
                                group_url = f"https://www.roblox.com/groups/{group_id}/-"

                                if dm_message:
                                    try:
                                        await member.send(f"_Bloxlink Server-Lock_\nYou were kicked from **{guild.name}** for not being in the "
                                                          f"required group <{group_url}>. These instructions were set by the Server "
                                                          f"Admins:\n\n{dm_message}")
                                    except Forbidden:
                                        pass

                                try:
                                    await member.kick(reason=f"SERVER-LOCK: not in group {group_id}")
                                except Forbidden:
                                    pass


                                return


                    if verified_dm:
                        verified_dm = await get_nickname(member, verified_dm, guild_data=guild_data, roblox_user=roblox_user, is_nickname=False)

                        try:
                            await member.send(verified_dm)
                        except (Forbidden, HTTPException):
                            pass
            else:
                if unverified_dm or verified_dm:
                    try:
                        primary_account, _ = await get_user(author=member, everything=False, basic_details=True)

                    except UserNotVerified:
                        if unverified_dm:
                            unverified_dm = await get_nickname(member, unverified_dm, guild_data=guild_data, skip_roblox_check=True, is_nickname=False)

                            try:
                                await member.send(unverified_dm)
                            except (Forbidden, HTTPException):
                                pass
                    else:
                        if verified_dm:
                            verified_dm = await get_nickname(member, verified_dm, guild_data=guild_data, roblox_user=primary_account, is_nickname=False)

                            try:
                                await member.send(verified_dm)
                            except (Forbidden, HTTPException):
                                pass
