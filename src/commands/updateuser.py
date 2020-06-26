from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, UserNotVerified, Message, BloxlinkBypass # pylint: disable=import-error
from config import REACTIONS # pylint: disable=no-name-in-module
from discord import Embed

update_member = Bloxlink.get_module("roblox", attrs=["update_member"])

@Bloxlink.command
class UpdateUserCommand(Bloxlink.Module):
    """force update user(s) with roles and nicknames"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_UPDATER")
        self.aliases = ["update", "updateroles"]
        self.arguments = [
            {
                "prompt": "Please specify user(s) to update. For example: ``@user1 @user2 @user3``",
                "type": "user",
                "name": "users",
                "multiple": True,
                "max": 10
            }
        ]
        self.category = "Administration"
        self.cooldown = 2

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        users = CommandArgs.parsed_args["users"]

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        trello_board = CommandArgs.trello_board
        trello_binds_list = trello_board and await trello_board.get_list(lambda l: l.name.lower() == "bloxlink binds")

        async with response.loading():
            if len(users) > 1:
                for user in users:
                    if not user.bot:
                        try:
                            added, removed, nickname, errors, roblox_user = await update_member(
                                user,
                                guild             = guild,
                                guild_data        = guild_data,
                                trello_board      = trello_board,
                                trello_binds_list = trello_binds_list,
                                roles             = True,
                                nickname          = True,
                                author_data       = await self.r.table("users").get(str(user.id)).run())
                        except BloxlinkBypass:
                            await response.info(f"{user.mention} **bypassed**")
                        except UserNotVerified:
                            await response.send(f"{REACTIONS['ERROR']} {user.mention} is **not linked to Bloxlink**")
                        else:
                            await response.send(f"{REACTIONS['DONE']} **Updated** {user.mention}")

            else:
                user = users[0]

                if user.bot:
                    raise Message("Bots can't have Roblox accounts!", type="silly")

                try:
                    added, removed, nickname, errors, roblox_user = await update_member(
                        user,
                        guild             = guild,
                        guild_data        = guild_data,
                        trello_board      = trello_board,
                        trello_binds_list = trello_binds_list,
                        roles             = True,
                        nickname          = True,
                        author_data       = await self.r.table("users").get(str(user.id)).run())

                    embed = Embed(title=f"Discord Profile for {user}", description="Changed someone’s group rank? Please wait 10 minutes for Bloxlink to catch up!")
                    embed.set_author(name=str(user), icon_url=user.avatar_url, url=roblox_user.profile_link)

                    if not (added or removed):
                        raise Message("All caught up! There no roles to add or remove.", type="success")

                    if added:
                        embed.add_field(name="Added Roles", value=", ".join(added))
                    if removed:
                        embed.add_field(name="Removed Roles", value=", ".join(removed))
                    if nickname:
                        embed.description = f"**Nickname:** ``{nickname}``\nChanged someone’s group rank? Please wait 10 minutes for Bloxlink to catch up!"
                    if errors:
                        embed.add_field(name="Errors", value=", ".join(errors))

                    embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)

                    await CommandArgs.response.send(embed=embed)

                except BloxlinkBypass:
                    raise Message("Since you have the ``Bloxlink Bypass`` role, I was unable to update your roles/nickname.", type="info")

                except UserNotVerified:
                    raise Error("This user is not linked to Bloxlink.")
