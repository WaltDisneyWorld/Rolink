from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, UserNotVerified, Message, BloxlinkBypass, CancelCommand, PermissionError, Blacklisted # pylint: disable=import-error
from config import REACTIONS # pylint: disable=no-name-in-module
from resources.constants import CACHE_CLEAR, RELEASE, GREEN_COLOR # pylint: disable=import-error
from discord import Embed, Object, Role
import math

guild_obligations, format_update_embed = Bloxlink.get_module("roblox", attrs=["guild_obligations", "format_update_embed"])
parse_message = Bloxlink.get_module("commands", attrs=["parse_message"])
get_features = Bloxlink.get_module("premium", attrs="get_features")
post_event = Bloxlink.get_module("utils", attrs=["post_event"])

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
                "prompt": "Please specify user(s) or role(s) to update. For example: ``@user1 @user2 @user3`` or ``@role``",
                "type": ["user", "role"],
                "name": "users",
                "multiple": True,
                "optional": True,
                "create_missing_role": False
            }
        ]
        self.category = "Administration"
        self.cooldown = 2
        self.REDIS_COOLDOWN_KEY = "guild_scan:{id}"


    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        users_ = CommandArgs.parsed_args["users"]
        prefix = CommandArgs.prefix

        message = CommandArgs.message
        author = message.author
        guild = message.guild

        guild_data = CommandArgs.guild_data

        users = []

        if not users_:
            message.content = f"{prefix}getrole"
            return await parse_message(message)

        if not CommandArgs.has_permission:
            if users_[0] == author:
                message.content = f"{prefix}getrole"
                return await parse_message(message)
            else:
                raise PermissionError("You do not have permission to update arbitrary users or roles!")

        if isinstance(users_[0], Role):
            if not guild.chunked:
                await guild.chunk()

            for role in users_:
                users += role.members

            if not users:
                raise Error("These role(s) have no members in it!")
        else:
            users = users_


        len_users = len(users)

        if self.redis:
            redis_cooldown_key = self.REDIS_COOLDOWN_KEY.format(release=RELEASE, id=guild.id)
            on_cooldown = await self.redis.get(redis_cooldown_key)

            if len_users > 3 and on_cooldown:
                cooldown_time = math.ceil(await self.redis.ttl(redis_cooldown_key)/60)

                if not cooldown_time or cooldown_time == -1:
                    await self.redis.delete(redis_cooldown_key)
                    on_cooldown = None

                if on_cooldown:
                    if on_cooldown == 1:
                        raise Message(f"This server is still queued.")
                    elif on_cooldown == 2:
                        raise Message("This server's scan is currently running.")
                    elif on_cooldown == 3:
                        cooldown_time = math.ceil(await self.redis.ttl(redis_cooldown_key)/60)

                        raise Message(f"This server has an ongoing cooldown! You must wait **{cooldown_time}** more minutes.")

            donator_profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)
            premium = donator_profile.features.get("premium")

            if not premium:
                donator_profile, _ = await get_features(author)
                premium = donator_profile.features.get("premium")


            cooldown = 0

            if len_users > 10:
                if not premium:
                    raise Error("You need premium in order to update more than 10 members at a time! "
                                f"Use ``{prefix}donate`` for instructions on donating.")

                if len_users >= 100:
                    cooldown = math.ceil(((len_users / 1000) * 120) * 60)
                else:
                    cooldown = 120

                if self.redis:
                    await self.redis.set(redis_cooldown_key, 2, ex=86400)

            trello_board = CommandArgs.trello_board
            #trello_binds_list = trello_board and await trello_board.get_list(lambda l: l.name.lower() == "bloxlink binds")

            #async with response.loading():
            if len_users > 1:
                for user in users:
                    if not user.bot:
                        try:
                            added, removed, nickname, errors, roblox_user = await guild_obligations(
                                user,
                                guild             = guild,
                                guild_data        = guild_data,
                                trello_board      = trello_board,
                                roles             = True,
                                nickname          = True,
                                dm                = False,
                                exceptions        = ("BloxlinkBypass", "UserNotVerified", "Blacklisted"),
                                cache             = not premium)
                        except BloxlinkBypass:
                            if len_users <= 10:
                                await response.info(f"{user.mention} **bypassed**")
                        except UserNotVerified:
                            if len_users <= 10:
                                await response.send(f"{REACTIONS['ERROR']} {user.mention} is **not linked to Bloxlink**")
                        except Blacklisted as b:
                            if len_users <= 10:
                                await response.send(f"{REACTIONS['ERROR']} {user.mention} has an active restriction.")
                        else:
                            if len_users <= 10:
                                await response.send(f"{REACTIONS['DONE']} **Updated** {user.mention}")
            else:
                user = users[0]

                if user.bot:
                    raise Message("Bots can't have Roblox accounts!", type="silly")

                old_nickname = user.display_name

                try:
                    added, removed, nickname, errors, roblox_user = await guild_obligations(
                        user,
                        guild             = guild,
                        guild_data        = guild_data,
                        trello_board      = trello_board,
                        roles             = True,
                        nickname          = True,
                        cache             = not premium,
                        dm                = False,
                        exceptions        = ("BloxlinkBypass", "Blacklisted", "CancelCommand", "UserNotVerified"))

                    _, embed = await format_update_embed(roblox_user, user, added=added, removed=removed, errors=errors, nickname=nickname if old_nickname != user.display_name else None, prefix=prefix, guild_data=guild_data, premium=premium)

                    if embed:
                        await response.send(embed=embed)
                        await post_event(guild, guild_data, "verification", f"{author.mention} ({author.id}) has **verified** as ``{roblox_user.username}``.", GREEN_COLOR)
                    else:
                        if premium:
                            await response.success("This user is all up-to-date; no changes were made.")
                        else:
                            await response.success("This user is all up-to-date; no changes were made.\n**Disclaimer:** it may take up to "
                                                   "__10 minutes__ for Bloxlink to recognize a __recent/new rank change__ due to caching.")

                except BloxlinkBypass:
                    raise Message("Since you have the ``Bloxlink Bypass`` role, I was unable to update your roles/nickname.", type="info")

                except Blacklisted as b:
                    if str(b):
                        raise Error(f"{user.mention} has an active restriction for: ``{b}``")
                    else:
                        raise Error(f"{user.mention} has an active restriction from Bloxlink.")

                except CancelCommand:
                    pass

                except UserNotVerified:
                    raise Error("This user is not linked to Bloxlink.")

            if cooldown:
                await self.redis.set(redis_cooldown_key, 3, ex=cooldown)

            if len_users > 10:
                await response.success("All users updated.")
