import re
import traceback
from discord.errors import Forbidden
from ..exceptions import PermissionError, CancelledPrompt, Message # pylint: disable=redefined-builtin
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
			parsed_args = await arguments.call_prompt(command_args)
			# TODO: catch PermissionError from resolver and post the event

		arg_container.add(
			parsed_args = parsed_args,
			string_args = content_modified and content_modified.split(" ") or [],
			call_prompt = arguments.call_prompt,
		)

	async def parse_message(self, message, guild_data=None):
		guild = message.guild
		content = message.content
		author = message.author
		channel = message.channel

		guild_data = guild_data or (guild and await self.args.r.table("guilds").get(str(guild.id)).run()) or {}
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
		after = args and " ".join(args) or ""

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
							subcommand_attrs = fn.__subcommandattrs__
							del args[0]

					CommandArgs = Args(
						command_name = command_name,
						message = message,
						guild_data = guild_data
					)

					locale = Locale(guild_data and guild_data.get("locale", "en") or "en")
					response = Response(CommandArgs)

					CommandArgs.add(locale=locale, response=response)

					try:
						await command.check_permissions(author, locale, permissions=subcommand_attrs.get("permissions"))
					except PermissionError as e:
						await response.error(e)
					else:

						try:
							await self.more_args(after, CommandArgs, subcommand_attrs.get("arguments") or command.arguments)
						except CancelledPrompt as e:
							if e.args:
								await response.send(f"**{locale('prompt.cancelledPrompt')}:** {e}")
							else:
								await response.send(f"**{locale('prompt.cancelledPrompt')}.**")
						except PermissionError as e:
							if e.args:
								await response.error(e)
							else:
								await response.error(locale("permissions.genericError"))
						else:
							try:
								await fn(CommandArgs)
							except CancelledPrompt as e:
								if e.args:
									await response.send(f"**{locale('prompt.cancelledPrompt')}:** {e}")
								else:
									await response.send(f"**{locale('prompt.cancelledPrompt')}.**")
							except Message as e:
								if e.args:
									await response.send(e)
								else:
									await response.send("This command closed unexpectedly.")
							except Exception as e:
								await response.error(locale("errors.commandError"))
								Bloxlink.error(e, title=f"Error from !{command_name}")


	@staticmethod
	def new_command(command_structure):
		command = Command(command_structure())

		for attr_name in dir(command_structure):
			attr = getattr(command_structure, attr_name)

			if callable(attr) and hasattr(attr, "__issubcommand__"):
				command.subcommands[attr.__name__] = attr

		commands[command.name] = command
