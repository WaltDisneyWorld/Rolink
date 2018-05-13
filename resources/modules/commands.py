from resources.framework import *


commands = dict()


class Command:
	def __init__(self, name, func, **kwargs):
		self.name = name
		self.subcommands = []
		self.description = func.__doc__ or "N/A"
		self.aliases = kwargs.get("alias") or kwargs.get("aliases") or list()
		self.permissions = kwargs.get("permissions", list())
		self.arguments = kwargs.get("arguments", list())
		self.func = func


def command(command_name=None, **kwargs):
	def wrapper(func):
		new_command = Command(command_name, func, **kwargs)
		commands[command_name] = new_command

	return wrapper


for command_name in get_files("commands/"):
	print(command_name)

