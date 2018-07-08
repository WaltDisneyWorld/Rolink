import traceback
import re
from config import PREFIX as default_prefix
from asyncio import get_event_loop
from resources.modules.utils import get_files, get_prefix, log_error
from resources.module import new_module
from resources.modules.permissions import check_permissions

from resources.structures.Command import Command
from resources.structures.Argument import Argument
from resources.structures.Response import Response


from bot import client
loop = client.loop


commands = dict()
commands_list = get_files("commands/")
processed_messages = []



def new_command(name=None, **kwargs):
	def wrapper(func):
		command = Command(func, name, **kwargs)
		commands[name or func.__name__] = command

	return wrapper


async def get_args(message, content="", args=None, command=None):
	if args:
		skipable_args = content.split(" | ")
	else:
		args = []
		skipable_args = []

	flags, flag_str = None, None

	if command.flags_enabled:
		flags, flag_str = Argument.parse_flags(content)

	new_args = Argument(message, args=args, command=command)
	_, is_cancelled = await new_args.call_prompt(flag_str=flag_str, skip_args=skipable_args)

	new_args.flags = flags

	return new_args, is_cancelled

async def parse_message(message):
	content = message.content
	channel = message.channel
	author = message.author
	guild = message.guild or (author and author.guild)

	if Argument.is_in_prompt(author):
		return

	if not guild or not author or not channel:
		return

	guild_prefix = await get_prefix(guild)
	prefix = guild_prefix or default_prefix

	client_match = re.search(f"<@!?{client.user.id}>", content)

	check = client_match and client_match.group(0) or (content[:len(prefix)].lower() == prefix.lower() and prefix)

	if check:

		after = content[len(check):].strip()
		args = after.split(" ")
		command_name = args[0]
		del args[0]
		after = " ".join(args)

		if command_name:
			command_name = command_name.lower()

			for index, command in dict(commands).items():

				if index == command_name or command_name in command.aliases:

					if len(processed_messages) > 5000:
						processed_messages.clear()

					processed_messages.append(message.id)

					response = Response(message, command_name)
					permission_success, permission_error = await check_permissions(command, channel, author)

					if permission_success:
						args, is_cancelled = await get_args(message, after, args, command)

						if not is_cancelled:
							try:
								await command.func(message, response, args)
							except Exception as e:
								await response.error("Oops! Something went wrong while executing the command.")
								
								error = traceback.format_exc()
								await log_error(error, f'{e.__class__.__name__} from {command_name}')
								
								traceback.print_exc()
					else:
						await response.error("You don't satisfy the required permissions: "
						f'``{permission_error}``')


for command_name in [f.replace(".py", "") for f in commands_list]:
	loop.create_task(new_module("commands", command_name))
