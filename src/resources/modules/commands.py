import re
import traceback
from concurrent.futures._base import CancelledError
from discord.errors import Forbidden, NotFound, HTTPException
from discord.utils import find
from ..exceptions import PermissionError, CancelledPrompt, Message, CancelCommand, RobloxAPIError, RobloxDown, Error # pylint: disable=redefined-builtin
from ..structures import Command, Bloxlink, Args
from resources.constants import MAGIC_ROLES # pylint: disable=import-error


get_prefix = Bloxlink.get_module("utils", attrs="get_prefix")
get_board = Bloxlink.get_module("trello", attrs="get_board")

Locale = Bloxlink.get_module("locale")
Response = Bloxlink.get_module("response")
Arguments = Bloxlink.get_module("arguments")

commands = {}

@Bloxlink.module
class Commands(Bloxlink.Module):
    def __init__(self):
        pass

    async def more_args(self, content_modified, arg_container, command_args):
        arguments = Arguments(None, arg_container)
        parsed_args = {}

        messages = []

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


            arguments = Arguments(skipped_args, arg_container)
            parsed_args, messages = await arguments.prompt(command_args, return_messages=True)
            # TODO: catch PermissionError from resolver and post the event

        arg_container.add(
            parsed_args = parsed_args,
            string_args = content_modified and content_modified.split(" ") or [],
            prompt = arguments.prompt,
            prompt_messages = messages
        )

        return messages

    async def parse_message(self, message, guild_data=None):
        guild = message.guild
        content = message.content
        author = message.author
        channel = message.channel

        channel_id = channel and str(channel.id)
        guild_id = guild and str(guild.id)

        guild_data = guild_data or (guild and (await self.r.db("canary").table("guilds").get(guild_id).run() or {"id": guild_id})) or {}
        trello_board = await get_board(guild_data=guild_data, guild=guild)
        prefix, _ = await get_prefix(guild=guild, guild_data=guild_data, trello_board=trello_board)

        client_match = re.search(f"<@!?{self.client.user.id}>", content)
        check = (content[:len(prefix)].lower() == prefix.lower() and prefix) or client_match and client_match.group(0)
        check_verify_channel = False

        if check:
            after = content[len(check):].strip()
            args = after.split(" ")
            command_name = args[0] and args[0].lower()
            del args[0]

            if command_name:
                for index, command in dict(commands).items():
                    if index == command_name or command_name in command.aliases:
                        ignored_channels = guild_data.get("ignoredChannels", {})

                        if ignored_channels.get(channel_id):
                            if not find(lambda r: r.name in MAGIC_ROLES, author.roles):
                                if guild.owner != author:
                                    author_perms = author.guild_permissions

                                    if not (author_perms.manage_guild or author_perms.administrator):
                                        return

                        if not (command.dm_allowed or guild):
                            try:
                                await channel.send("This command does not support DM. Please run it in a server.")
                            except Forbidden:
                                pass
                            finally:
                                return

                        fn = command.fn
                        subcommand_attrs = {}

                        if args:
                            # subcommand checking
                            subcommand = command.subcommands.get(args[0])
                            if subcommand:
                                fn = subcommand
                                subcommand_attrs = getattr(fn, "__subcommandattrs__", None)
                                del args[0]

                        after = args and " ".join(args) or ""

                        CommandArgs = Args(
                            command_name = command_name,
                            message = message,
                            guild_data = guild_data,
                            flags = {},
                            prefix = prefix,
                            has_permission = False
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
                            await command.check_permissions(author, locale, permissions=subcommand_attrs.get("permissions"))
                        except PermissionError as e:
                            if subcommand_attrs.get("allow_bypass"):
                                CommandArgs.has_permission = False
                            elif command.permissions.allow_bypass:
                                CommandArgs.has_permission = False
                            else:
                                await response.error(e)

                                return

                        else:
                            CommandArgs.has_permission = True

                        messages = []

                        try:
                            messages = await self.more_args(after, CommandArgs, subcommand_attrs.get("arguments") or command.arguments)
                            response.prompt = CommandArgs.prompt # pylint: disable=no-member
                            await fn(CommandArgs)
                        except PermissionError as e:
                            if e.args:
                                await response.error(e)
                            else:
                                await response.error(locale("permissions.genericError"))
                        except Forbidden:
                            if e.args:
                                await response.error(e)
                            else:
                                await response.error(locale("permissions.genericError"))
                        except RobloxAPIError:
                            await response.error("The Roblox API returned an error; are you supplying the correct ID to this command?")
                        except RobloxDown:
                            await response.error("The Roblox API is currently offline; please wait until Roblox is back online before re-running this command.")
                        except CancelledPrompt as e:
                            if e.args:
                                await response.send(f"**{locale('prompt.cancelledPrompt')}:** {e}")
                            else:
                                await response.send(f"**{locale('prompt.cancelledPrompt')}.**")

                            if messages:
                                for message in messages:
                                    try:
                                        await message.delete()
                                    except (Forbidden, NotFound, HTTPException):
                                        pass

                        except Message as e:
                            message_type = "send" if e.type == "info" else e.type
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
                            # TODO: save command and args to a database and then re-execute it when the bot restarts
                            await response.send("I'm sorry, but Bloxlink is currently restarting for updates. Your command will be re-executed when the bot restarts.")
                        except Exception as e:
                            await response.error(locale("errors.commandError"))
                            Bloxlink.error(traceback.format_exc(), title=f"Error source: {command_name}.py")

                        break

                else:
                    check_verify_channel = True
            else:
                check_verify_channel = True
        else:
            check_verify_channel = True

        if check_verify_channel and guild:
            verify_channel_id = guild_data.get("verifyChannel")

            if verify_channel_id and channel_id == verify_channel_id:
                if not find(lambda r: r.name in MAGIC_ROLES, author.roles):
                    try:
                        await message.delete()
                    except (Forbidden, NotFound):
                        pass






    @staticmethod
    def new_command(command_structure):
        c = command_structure()
        command = Command(c)
        subcommands = {}

        Bloxlink.log(f"Adding command {command.name}")

        for attr_name in dir(command_structure):
            attr = getattr(c, attr_name)

            if callable(attr) and hasattr(attr, "__issubcommand__"):
                command.subcommands[attr_name] = attr
                #subcommands[attr_name] = attr

        commands[command.name] = command

        return command_structure
