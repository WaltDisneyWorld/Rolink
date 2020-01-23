import re
import traceback
from concurrent.futures._base import CancelledError
from discord.errors import Forbidden, NotFound, HTTPException
from ..exceptions import PermissionError, CancelledPrompt, Message, CancelCommand, RobloxAPIError, RobloxDown, Error # pylint: disable=redefined-builtin
from ..structures import Command, Bloxlink, Args


get_prefix = Bloxlink.get_module("utils", attrs="get_prefix")
get_board = Bloxlink.get_module("trello", attrs="get_board")

Locale = Bloxlink.get_module("locale")
Response = Bloxlink.get_module("response")
Arguments = Bloxlink.get_module("arguments")

commands = {}
trello_boards = {}

@Bloxlink.module
class Commands:
	def __init__(self, args):
		self.args = args

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
				if arg.startswith('"') and arg.endswith('"'):
					arg = arg.replace('"', "")

				if len(skipped_args) + 1 == arg_len:
					t = content_modified.replace('"', "").replace(" ".join(skipped_args), "").strip()
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

		guild_data = guild_data or (guild and (await self.args.r.table("guilds").get(str(guild.id)).run() or {"id": str(guild.id)})) or {}
		trello_board = await get_board(guild_data=guild_data, guild=guild)
		prefix = await get_prefix(guild=guild, guild_data=guild_data, trello_board=trello_board)

		client_match = re.search(f"<@!?{self.args.client.user.id}>", content)
		check = client_match and client_match.group(0) or (content[:len(prefix)].lower() == prefix.lower() and prefix)

		if not check:
			return

		after = content[len(check):].strip()
		args = after.split(" ")
		command_name = args[0] and args[0].lower()
		del args[0]

		if command_name:
			for index, command in dict(commands).items():
				if index == command_name or command_name in command.aliases:
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
						if command.subcommands.get(args[0]):
							fn = command.subcommands.get(args[0])
							subcommand_attrs = getattr(fn, "__subcommandattrs__", None)
							del args[0]

					after = args and " ".join(args) or ""

					CommandArgs = Args(
						command_name = command_name,
						message = message,
						guild_data = guild_data,
						flags = {},
						prefix = prefix
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
						await response.error(e)
					else:
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




	@staticmethod
	def new_command(command_structure):
		command = Command(command_structure())

		for attr_name in dir(command_structure):
			attr = getattr(command_structure, attr_name)

			if callable(attr) and hasattr(attr, "__issubcommand__"):
				command.subcommands[attr.__name__] = attr

		commands[command.name] = command
