import re
import traceback
from ..structures import Command, Bloxlink, Args
from ..exceptions import PermissionError, CancelledPrompt
from discord.errors import Forbidden


get_prefix = Bloxlink.get_module("utils", attrs="get_prefix")

Locale = Bloxlink.get_module("locale")
Response = Bloxlink.get_module("response")
Arguments = Bloxlink.get_module("arguments")

commands = {}

@Bloxlink.module
class Commands:
	def __init__(self, args):
		self.args = args

	async def get_args(self, message, args, response, content, command, locale):
		arguments = Arguments(message, None, response, locale)
		parsed_args = {}

		if args:
			arg_len = len(args)
			skipped_args = []
			split = content.split(" ")
			temp = []

			for arg in split:
				if arg.startswith('"') and arg.endswith('"'):
					arg = arg.replace('"', "")

				if len(skipped_args) + 1 == arg_len:
					t = content.replace('"', "").replace(" ".join(skipped_args), "").strip()
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

			arguments = Arguments(message, skipped_args, response, locale)
			parsed_args = await arguments.call_prompt(args)
			# TODO: catch PermissionError from resolver and post the event

		args = Args(
			parsed_args = parsed_args,
			string_args = content and content.split(" ") or [],
			call_prompt = arguments.call_prompt
		)

		return args

	async def parse_message(self, message, guild_data=None):
		guild = message.guild
		content = message.content
		author = message.author
		channel = message.channel

		guild_data = guild_data or (guild and await self.args.r.table("guilds").get(str(guild.id)).run()) or {}

		prefix = await get_prefix(guild=guild, guild_data=guild_data)

		client_match = re.search(f"<@!?{self.args.client.user.id}>", content)
		check = client_match and client_match.group(0) or (content[:len(prefix)].lower() == prefix.lower() and prefix)

		if not check: return

		after = content[len(check):].strip()
		args = after.split(" ")
		command_name = args[0] and args[0].lower()
		del args[0]
		after = args and " ".join(args) or ""

		if command_name:
			for index, command in dict(commands).items():
				if index == command_name or command_name in command.aliases:
					if not command.dm_allowed and not guild:
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

					locale = Locale(guild_data and guild_data.get("locale", "en") or "en")
					response = Response(message, locale=locale, guild_data=guild_data, command_name=command_name)

					try:
						await command.check_permissions(author, locale, permissions=subcommand_attrs.get("permissions"))
					except PermissionError as e:
						await response.error(e)
					else:

						try:
							resolved_args = await self.get_args(message, subcommand_attrs.get("arguments") or command.arguments, response, after, command, locale)
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
								await fn(message, response, resolved_args)
							except CancelledPrompt as e:
								if e.args:
									await response.send(f"**{locale('prompt.cancelledPrompt')}:** {e}")
								else:
									await response.send(f"**{locale('prompt.cancelledPrompt')}.**")
							except Exception as e:
								await response.error(locale("errors.commandError"))
								print(e, flush=True)
								traceback.print_exc()
								# TODO: post error to channel


	@staticmethod
	def new_command(command_structure):
		command = Command(command_structure())

		for attr_name in dir(command_structure):
			attr = getattr(command_structure, attr_name)

			if callable(attr) and hasattr(attr, "__issubcommand__"):
				command.subcommands[attr.__name__] = attr

		commands[command.name] = command
