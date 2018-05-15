from resources.framework import get_files
from resources.structures import Command, Response
from resources.module import new_module
from resources.settings import PREFIX as prefix_list
from resources.modules.permissions import check_permissions


commands = dict()




def new_command(name=None, **kwargs):
	def wrapper(func):
		command = Command(func, name, **kwargs)
		commands[name or func.__name__] = command

	return wrapper


async def parse_message(message):
	content = message.content
	channel = message.channel
	guild = message.guild
	author = message.author

	for prefix in prefix_list:
		if content[:len(prefix)].lower() == prefix.lower():
			after = content[len(prefix):]
			args = after.split(" ")
			command_name = args[0]
			if command_name:
				command_name = command_name.lower()
				if commands.get(command_name):
					command = commands.get(command_name)
					response = Response(message, command_name)
					permission_success, permission_error = check_permissions(command, channel, author)
					if permission_success:
						try:
							await command.func(message, response)
						except Exception as e:
							await response.error(f':exclamation: This command has **failed execution**!\n'
							f'**Error:** ``{e}``')
					else:
						await response.error(":exclamation: You don't satisfy the required permissions: "
						f'``{permission_error}``')


for command_name in [f.replace(".py", "") for f in get_files("commands/")]:
	new_module("commands", command_name)
