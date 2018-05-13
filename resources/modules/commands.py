from resources.framework import get_files
from resources.structures import Command


commands = dict()




def command(command_name=None, **kwargs):
	def wrapper(func):
		new_command = Command(command_name, func, **kwargs)
		commands[command_name] = new_command

	return wrapper


for name in get_files("commands/"):
	print(name)

