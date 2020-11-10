import re
import traceback
import time
import math
import asyncio
import sentry_sdk
from concurrent.futures._base import CancelledError
from inspect import iscoroutinefunction
from discord.errors import Forbidden, NotFound, HTTPException
from discord.utils import find
from discord import Embed, Object, Member
from ..exceptions import PermissionError, CancelledPrompt, Message, CancelCommand, RobloxAPIError, RobloxDown, Error # pylint: disable=redefined-builtin, import-error
from ..structures import Bloxlink, Args, Permissions, Locale, Arguments, Response # pylint: disable=import-error
from ..constants import MAGIC_ROLES, OWNER, DEFAULTS, RELEASE, SERVER_INVITE # pylint: disable=import-error


get_prefix = Bloxlink.get_module("utils", attrs=["get_prefix"])
get_features = Bloxlink.get_module("premium", attrs=["get_features"])
get_board, get_options = Bloxlink.get_module("trello", attrs=["get_board", "get_options"])
get_addon_commands = Bloxlink.get_module("addonsm", attrs="get_addon_commands")
cache_get, cache_set, cache_pop = Bloxlink.get_module("cache", attrs=["get", "set", "pop"])


flag_pattern = re.compile(r"--?(.+?)(?: ([^-]*)|$)")

commands = {}

@Bloxlink.module
class Commands(Bloxlink.Module):
    def __init__(self):
        pass

    async def more_args(self, content_modified, CommandArgs, command_args, arguments):
        parsed_args = {}

        if command_args:
            arg_len = len(command_args)
            skipped_args = []
            split = content_modified.split(" ")
            temp = []

            for arg in split:
                if arg:
                    if arg.startswith('"') and arg.endswith('"'):
                        arg = arg.replace('"', "")

                    if len(skipped_args) + 1 == arg_len:
                        # t = content_modified.replace('"', "").replace(" ".join(skipped_args), "").strip() # PROBLEM HERE
                        t = content_modified.replace('"', "")
                        toremove = " ".join(skipped_args)

                        if t.startswith(toremove):
                            t = t[len(toremove):]

                        t = t.strip()

                        skipped_args.append(t)

                        break

                    if arg.startswith('"') or (temp and not arg.endswith('"')):
                        temp.append(arg.replace('"', ""))

                    elif arg.endswith('"'):
                        temp.append(arg.replace('"', ""))
                        skipped_args.append(" ".join(temp))
                        temp.clear()

                    else:
                        skipped_args.append(arg)

            parsed_args = await arguments.prompt(command_args, skipped_args=skipped_args)
            # TODO: catch PermissionError from resolver and post the event


        return parsed_args, content_modified and content_modified.split(" ") or []


    async def parse_message(self, message, guild_data=None):
        guild = message.guild
        content = message.content
        author = message.author
        channel = message.channel

        channel_id = channel and str(channel.id)
        guild_id = guild and str(guild.id)

        guild_data = guild_data or (guild and (await self.r.table("guilds").get(guild_id).run() or {"id": guild_id})) or {}
        trello_board = await get_board(guild_data=guild_data, guild=guild)
        prefix, _ = await get_prefix(guild=guild, guild_data=guild_data, trello_board=trello_board)

        client_match = re.search(f"<@!?{self.client.user.id}>", content)
        check = (content[:len(prefix)].lower() == prefix.lower() and prefix) or client_match and client_match.group(0)
        check_verify_channel = False

        trello_options = {}
        trello_options_checked = True

        if check:
            after = content[len(check):].strip()
            args = after.split(" ")
            command_name = args[0] and args[0].lower()
            del args[0]

            if command_name:
                # TODO: merge commands from add-ons
                guild_addons = guild_data.get("addons")

                if guild_addons:
                    addon_commands = get_addon_commands(guild_data)

                    if addon_commands:
                        pass # TODO

                for index, command in commands.items():
                    if index == command_name or command_name in command.aliases:
                        donator_profile = None
                        actually_dm = command.dm_allowed and not guild

                        if guild and RELEASE == "PRO" and command_name not in ("donate", "transfer", "eval", "status"):
                            donator_profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)

                            if not donator_profile.features.get("pro"):
                                try:
                                    await channel.send(f"Server not authorized to use Pro. Please use the ``{prefix}donate`` command to see information on "
                                                        "how to get Bloxlink Pro.")

                                except (Forbidden, NotFound):
                                    pass

                                finally:
                                    return

                        ignored_channels = guild_data.get("ignoredChannels", {})

                        if ignored_channels.get(channel_id):
                            if guild.owner != author and not find(lambda r: r.name in MAGIC_ROLES, author.roles):
                                author_perms = author.guild_permissions

                                if not (author_perms.manage_guild or author_perms.administrator):
                                    return

                        blacklisted_discord = await cache_get("blacklist:discord_ids", author.id, primitives=True)

                        if blacklisted_discord is not None:
                            blacklist_text = blacklisted_discord and f"has an active restriction for: ``{blacklisted_discord}``" or "has an active restriction from Bloxlink."

                            try:
                                await channel.send(f"{author.mention} {blacklist_text}")
                            except (Forbidden, NotFound):
                                pass
                            finally:
                                return

                        if guild and not isinstance(author, Member):
                            try:
                                author = await guild.fetch_member(author.id)
                            except NotFound:
                                raise CancelCommand

                        if command.cooldown and self.cache:
                            redis_cooldown_key = f"cooldown_cache:{index}:{author.id}"

                            if not donator_profile or (donator_profile and not donator_profile.features.get("premium")):
                                donator_profile, _ = await get_features(author)

                            if not donator_profile.features.get("premium"):
                                on_cooldown = await self.cache.get(redis_cooldown_key)

                                if on_cooldown:
                                    cooldown_time = await self.redis.ttl(redis_cooldown_key)

                                    embed = Embed(title="Slow down!")
                                    embed.description = "This command has a short cooldown since it's relatively expensive for the bot. " \
                                                        f"You'll need to wait **{cooldown_time}** more second(s).\n\nDid you know? " \
                                                        "**[Bloxlink Premium](https://www.patreon.com/join/bloxlink?)** subscribers NEVER " \
                                                        f"see any cooldowns. Find out more information with ``{prefix}donate``."

                                    try:
                                        m = await channel.send(embed=embed)
                                    except (NotFound, Forbidden):
                                        pass
                                    else:
                                        await asyncio.sleep(10)

                                        try:
                                            await m.delete()
                                            await message.delete()
                                        except (NotFound, Forbidden):
                                            pass

                                    return

                                await self.cache.set(redis_cooldown_key, True, expire_time=command.cooldown)

                        if not (command.dm_allowed or guild):
                            try:
                                await channel.send("This command does not support DM; please run it in a server.")
                            except Forbidden:
                                pass
                            finally:
                                return

                        fn = command.fn
                        subcommand_attrs = {}
                        subcommand = False

                        if args:
                            # subcommand checking
                            subcommand = command.subcommands.get(args[0])
                            if subcommand:
                                fn = subcommand
                                subcommand_attrs = getattr(fn, "__subcommandattrs__", None)
                                del args[0]

                        after = args and " ".join(args) or ""

                        CommandArgs = Args(
                            command_name = index,
                            real_command_name = command_name,
                            message = message,
                            guild_data = guild_data,
                            flags = {},
                            prefix = prefix,
                            has_permission = False,
                        )

                        if getattr(fn, "__flags__", False):
                            flags, flags_str = command.parse_flags(after)
                            content = content.replace(flags_str, "")
                            message.content = content
                            after = after.replace(flags_str, "")
                            CommandArgs.flags = flags

                        locale = Locale(guild_data and guild_data.get("locale", "en") or "en")
                        response = Response(CommandArgs)

                        CommandArgs.add(locale=locale, response=response, trello_board=trello_board)

                        try:
                            await command.check_permissions(author, guild, locale, dm=actually_dm, **subcommand_attrs)
                        except PermissionError as e:
                            if subcommand_attrs.get("allow_bypass"):
                                CommandArgs.has_permission = False
                            elif command.permissions.allow_bypass:
                                CommandArgs.has_permission = False
                            else:
                                await response.error(e)

                                return

                        except Message as e:
                            message_type = "send" if e.type == "info" else e.type
                            response_fn = getattr(response, message_type, response.send)

                            if e.args:
                                await response_fn(e)

                            if subcommand_attrs.get("allow_bypass"):
                                CommandArgs.has_permission = False
                            elif command.permissions.allow_bypass:
                                CommandArgs.has_permission = False
                            else:
                                return

                        else:
                            CommandArgs.has_permission = True

                        if subcommand:
                            command_args = subcommand_attrs.get("arguments")
                        else:
                            command_args = command.arguments

                        arguments = Arguments(CommandArgs)

                        try:
                            parsed_args, string_args = await self.more_args(after, CommandArgs, command_args, arguments)
                            CommandArgs.add(parsed_args=parsed_args, string_args=string_args, prompt=arguments.prompt)
                            response.prompt = arguments.prompt # pylint: disable=no-member

                            await fn(CommandArgs)
                        except PermissionError as e:
                            if e.args:
                                await response.error(e)
                            else:
                                await response.error(locale("permissions.genericError"))
                        except Forbidden as e:
                            if e.args:
                                await response.error(e)
                            else:
                                await response.error(locale("permissions.genericError"))
                        except RobloxAPIError:
                            await response.error("The Roblox API returned an error; are you supplying the correct ID to this command?")
                        except RobloxDown:
                            await response.error("The Roblox API is currently offline; please wait until Roblox is back online before re-running this command.")
                        except CancelledPrompt as e:
                            arguments.cancelled = True

                            guild_data = guild_data or (guild and (await self.r.table("guilds").get(guild_id).run() or {"id": guild_id})) or {}

                            if trello_board:
                                trello_options, _ = await get_options(trello_board)
                                guild_data.update(trello_options)
                                trello_options_checked = True

                            if (e.type == "delete" and not e.dm) and guild_data.get("promptDelete", DEFAULTS.get("promptDelete")):
                                try:
                                    await message.delete()
                                except (Forbidden, NotFound):
                                    pass
                            else:
                                if e.args:
                                    await response.send(f"**{locale('prompt.cancelledPrompt')}:** {e}", dm=e.dm, no_dm_post=True)
                                else:
                                    await response.send(f"**{locale('prompt.cancelledPrompt')}.**", dm=e.dm, no_dm_post=True)

                        except Message as e:
                            message_type = "send" if e.type == "send" else e.type
                            response_fn = getattr(response, message_type, response.send)

                            if e.args:
                                await response_fn(e)
                            else:
                                await response_fn("This command closed unexpectedly.")
                        except Error as e:
                            if e.args:
                                await response.error(e)
                            else:
                                await response.error("This command has unexpectedly errored.")
                        except CancelCommand as e:
                            if e.args:
                                await response.send(e)
                        except NotImplementedError:
                            await response.error("The option you specified is currently not implemented, but will be coming soon!")
                        except CancelledError:
                            pass
                        except Exception as e:
                            """
                            error_id = Bloxlink.error(e, command=command_name, user=(author.id, str(author)), guild=guild and f"id:{guild.id}")

                            if error_id:
                                await response.error("We've experienced an unexpected error. You may report this "
                                                     f"error with ID ``{error_id}`` in our support server: {SERVER_INVITE}.")
                            else:
                                await response.error("An unexpected error occured.")
                            """

                            await response.error(locale("errors.commandError"))
                            Bloxlink.error(traceback.format_exc(), title=f"Error source: {command_name}.py")

                        finally:
                            messages = arguments.messages + response.delete_message_queue

                            if arguments.dm_post:
                                if arguments.cancelled:
                                    content = f"{author.mention}, **this DM prompt has been cancelled.**"
                                else:
                                    content = f"{author.mention}, **this DM prompt has finished.**"

                                try:
                                    await arguments.dm_post.edit(content=content)
                                except (NotFound, Forbidden):
                                    pass


                            if messages:
                                if not trello_options_checked and trello_board:
                                    trello_options, _ = await get_options(trello_board)
                                    guild_data.update(trello_options)
                                    trello_options_checked = True

                                if not actually_dm and guild_data.get("promptDelete", DEFAULTS.get("promptDelete")):#
                                    for message in arguments.messages + response.delete_message_queue:
                                        try:
                                            await message.delete()
                                        except (Forbidden, NotFound):
                                            pass

                        break

                else:
                    check_verify_channel = True
            else:
                check_verify_channel = True
        else:
            check_verify_channel = True

        if check_verify_channel and guild:
            if not isinstance(author, Member):
                try:
                    author = await guild.fetch_member(author.id)
                except NotFound:
                    return

            verify_channel_id = guild_data.get("verifyChannel")

            if verify_channel_id and channel_id == verify_channel_id:
                if not find(lambda r: r.name in MAGIC_ROLES, author.roles):
                    try:
                        await message.delete()
                    except (Forbidden, NotFound):
                        pass


    def new_command(self, command_structure):
        c = command_structure()
        command = Command(c)

        Bloxlink.log(f"Adding command {command.name}")

        for attr_name in dir(command_structure):
            attr = getattr(c, attr_name)

            if callable(attr) and hasattr(attr, "__issubcommand__"):
                command.subcommands[attr_name] = attr

        commands[command.name] = command

        self.loop.create_task(self.inject_command(command))

        return command_structure

    async def inject_command(self, command):
        subcommands = []

        if command.subcommands:
            for subcommand_name, subcommand in command.subcommands.items():
                subcommand_description = subcommand.__doc__ or "N/A"
                subcommands.append({"id": subcommand_name, "description": subcommand_description})

        if RELEASE == "MAIN":
            await self.r.db("bloxlink").table("commands").insert({
                "id": command.name,
                "description": command.description,
                #"usage": command.usage,
                "category": command.category,
                "hidden": command.hidden,
                "subcommands": subcommands
            }, conflict="replace").run()

class Command:
    def __init__(self, command):
        self.name = command.__class__.__name__.replace("Command", "").lower()
        self.subcommands = {}
        self.description = command.__doc__ or "N/A"
        self.dm_allowed = getattr(command, "dm_allowed", False)
        self.full_description = getattr(command, "full_description", self.description)
        self.aliases = getattr(command, "aliases", [])
        self.permissions = getattr(command, "permissions", Permissions())
        self.arguments = getattr(command, "arguments", [])
        self.category = getattr(command, "category", "Miscellaneous")
        self.examples = getattr(command, "examples", [])
        self.hidden = getattr(command, "hidden", self.category == "Developer")
        self.free_to_use = getattr(command, "free_to_use", False)
        self.fn = command.__main__
        self.cooldown = getattr(command, "cooldown", 0)
        self.premium = self.permissions.premium or self.category == "Premium"
        self.developer_only = self.permissions.developer_only or self.category == "Developer" or getattr(command, "developer_only", False) or getattr(command, "developer", False)

        self.usage = []
        command_args = self.arguments

        if command_args:
            for arg in command_args:
                if arg.get("optional"):
                    if arg.get("default"):
                        self.usage.append(f'[{arg.get("name")}={arg.get("default")}]')
                    else:
                        self.usage.append(f'[{arg.get("name")}]')
                else:
                    self.usage.append(f'<{arg.get("name")}>')

        self.usage = " | ".join(self.usage) if self.usage else ""

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    async def check_permissions(self, author, guild, locale, dm=False, permissions=None, **kwargs):
        permissions = permissions or self.permissions

        if author.id == OWNER:
            return True

        if permissions.developer_only or self.developer_only:
            if author.id != OWNER:
                raise PermissionError("This command is reserved for the Bloxlink Developer.")

        if (kwargs.get("premium", self.premium) or permissions.premium) and not kwargs.get("free_to_use", self.free_to_use):
            prem, _ = await get_features(Object(id=guild.owner_id), guild=guild)

            if not prem.features.get("premium"):
                prem, _ = await get_features(author)

                if not prem.attributes["PREMIUM_ANYWHERE"]:
                    raise Message("This command is reserved for Bloxlink Premium subscribers!\n"
                                  "The server owner must have premium for this to work. If you "
                                  "would like the server owner to have premium instead, please use the ``!transfer`` "
                                  "command.\nYou may subscribe to Bloxlink Premium on Patreon: https://patreon.com/bloxlink", type="silly")

        try:
            if not dm:
                author_perms = author.guild_permissions

                for role_exception in permissions.exceptions["roles"]:
                    if find(lambda r: r.name == role_exception, author.roles):
                        return True

                if permissions.bloxlink_role:
                    role_name = permissions.bloxlink_role

                    if find(lambda r: r.name == "Bloxlink Admin", author.roles):
                        return True
                    else:
                        if role_name == "Bloxlink Manager":
                            if author_perms.manage_guild or author_perms.administrator:
                                pass
                            else:
                                raise PermissionError("You need the ``Manage Server`` permission to run this command.")

                        elif role_name == "Bloxlink Moderator":
                            if author_perms.kick_members or author_perms.ban_members or author_perms.administrator:
                                pass
                            else:
                                raise PermissionError("You need the ``Kick`` or ``Ban`` permission to run this command.")

                        elif role_name == "Bloxlink Updater":
                            if author_perms.manage_guild or author_perms.administrator or author_perms.manage_roles or find(lambda r: r.name == "Bloxlink Updater", author.roles):
                                pass
                            else:
                                raise PermissionError("You either need: a role called ``Bloxlink Updater``, the ``Manage Roles`` "
                                                    "role permission, or the ``Manage Server`` role permission.")

                        elif role_name == "Bloxlink Admin":
                            if author_perms.administrator:
                                pass
                            else:
                                raise PermissionError("You need the ``Administrator`` role permission to run this command.")

                if permissions.allowed.get("discord_perms"):
                    for perm in permissions.allowed["discord_perms"]:
                        if perm == "Manage Server":
                            if author_perms.manage_guild or author_perms.administrator:
                                pass
                            else:
                                raise PermissionError("You need the ``Manage Server`` permission to run this command.")
                        else:
                            if not getattr(author_perms, perm, False) and not perm.administrator:
                                raise PermissionError(f"You need the ``{perm}`` permission to run this command.")


                for role in permissions.allowed["roles"]:
                    if not find(lambda r: r.name == role, author.roles):
                        raise PermissionError(f"Missing role: ``{role}``")

            if permissions.allowed.get("functions"):
                for function in permissions.allowed["functions"]:

                    if iscoroutinefunction(function):
                        data = [await function(author)]
                    else:
                        data = [function(author)]

                    if not data[0]:
                        raise PermissionError

                    if isinstance(data[0], tuple):
                        if not data[0][0]:
                            raise PermissionError(data[0][1])

        except PermissionError as e:
            if e.args:
                raise PermissionError(e)

            raise PermissionError("You do not meet the required permissions for this command.")

    def parse_flags(self, content):
        flags = {m.group(1): m.group(2) or True for m in flag_pattern.finditer(content)}

        if flags:
            try:
                content = content[content.index("--"):]
            except ValueError:
                try:
                    content = content[content.index("-"):]
                except ValueError:
                    return {}, ""

        return flags, flags and content or ""