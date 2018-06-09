from resources.framework import get_files, loop
from resources.structures import Command, Response, Argument, parse_flags
from resources.module import new_module
from resources.framework import config
from resources.modules.permissions import check_permissions
import traceback

prefix_list = config.PREFIX

commands = dict()



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

	flags, flag_str = parse_flags(content)

	new_args = Argument(message, args=args, command=command)
	_, is_cancelled = await new_args.call_prompt(flag_str=flag_str, skip_args=skipable_args)

	new_args.flags = flags

	return new_args, is_cancelled

async def parse_message(message):
	content = message.content
	channel = message.channel
	author = message.author

	if Argument.is_in_prompt(author): return

	for prefix in prefix_list:
		if content[:len(prefix)].lower() == prefix.lower():

			after = content[len(prefix):]
			args = after.split(" ")
			command_name = args[0]
			del args[0]
			after = " ".join(args)

			if command_name:
				command_name = command_name.lower()

				for index, command in commands.items():

					if index == command_name or command_name in command.aliases:

						response = Response(message, command_name)
						permission_success, permission_error = check_permissions(command, channel, author)

						if permission_success:
							args, is_cancelled = await get_args(message, after, args, command)

							if not is_cancelled:
								try:
									await command.func(message, response, args)
								except Exception as e:
									await response.error("This command has **failed execution**!\n" \
										f'**Error:** ``{e}``')
									traceback.print_exc()
						else:
							await response.error("You don't satisfy the required permissions: "
							f'``{permission_error}``')


for command_name in [f.replace(".py", "") for f in get_files("commands/")]:
	loop.create_task(new_module("commands", command_name))
