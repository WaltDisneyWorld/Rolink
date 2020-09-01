from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, UserNotVerified, Message, BloxlinkBypass, CancelCommand, PermissionError, Blacklisted # pylint: disable=import-error
from config import REACTIONS # pylint: disable=no-name-in-module
from resources.constants import CACHE_CLEAR # pylint: disable=import-error
from discord import Embed, Object

update_member = Bloxlink.get_module("roblox", attrs=["update_member"])
parse_message = Bloxlink.get_module("commands", attrs=["parse_message"])
is_premium = Bloxlink.get_module("utils", attrs="is_premium")

@Bloxlink.command
class UpdateUserCommand(Bloxlink.Module):
    """force update user(s) with roles and nicknames"""

    def __init__(self):
        permissions = Bloxlink.Permissions().build("BLOXLINK_UPDATER")
        permissions.allow_bypass = True

        self.permissions = permissions
        self.aliases = ["update", "updateroles"]
        self.arguments = [
            {
                "prompt": "Please specify user(s) to update. For example: ``@user1 @user2 @user3``",
                "type": "user",
                "name": "users",
                "multiple": True,
                "max": 10,
                "optional": True
            }
        ]
        self.category = "Administration"
        self.cooldown = 2


    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        users = CommandArgs.parsed_args["users"]
        prefix = CommandArgs.prefix

        message = CommandArgs.message
        author = message.author
        guild = message.guild

        guild_data = CommandArgs.guild_data


        if not users:
            message.content = f"{prefix}getrole"
            return await parse_message(message)

        if not CommandArgs.has_permission:
            if users[0] == author:
                message.content = f"{prefix}getrole"
                return await parse_message(message)
            else:
                raise PermissionError("You do not have permission to update arbitrary users!")

        donator_profile, _ = await is_premium(Object(id=guild.owner_id), guild=guild)
        premium = donator_profile.features.get("premium")

        if not premium:
            donator_profile, _ = await is_premium(author, guild=guild)
            premium = donator_profile.features.get("premium")


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
                                author_data       = await self.r.db("bloxlink").table("users").get(str(user.id)).run(),
                                cache             = not premium)
                        except BloxlinkBypass:
                            await response.info(f"{user.mention} **bypassed**")
                        except UserNotVerified:
                            await response.send(f"{REACTIONS['ERROR']} {user.mention} is **not linked to Bloxlink**")
                        except Blacklisted as b:
                            await response.send(f"{REACTIONS['ERROR']} {user.mention} is **blacklisted**")
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
                        author_data       = await self.r.db("bloxlink").table("users").get(str(user.id)).run(),
                        cache             = not premium)

                    embed = Embed(title=f"Discord Profile for {user}", description=f"Changed someone’s group rank? Please wait {CACHE_CLEAR} minutes for Bloxlink to catch up!")
                    embed.set_author(name=str(user), icon_url=user.avatar_url, url=roblox_user.profile_link)

                    if not (added or removed):
                        raise Message(f"All caught up! There are no roles to add or remove. Please note that you may need to wait {CACHE_CLEAR} minutes for the "
                                       "Bloxlink cache to clear if this user was recently promoted/demoted.", type="success")

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

                except Blacklisted as b:
                    if str(b):
                        raise Error(f"{user.mention} is **blacklisted** for: ``{b}``.")
                    else:
                        raise Error(f"{user.mention} is **blacklisted** from Bloxlink.")

                except UserNotVerified:
                    raise Error("This user is not linked to Bloxlink.")
