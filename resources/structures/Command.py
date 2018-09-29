class Command:
	def __init__(self, func, name=None, is_subcommand=False, **kwargs):
		self.name = name or func.__name__
		self.subcommands = {}
		self.description = func.__doc__ or "N/A"
		self.full_description = kwargs.get("full_description") or func.__doc__ or "N/A"
		self.aliases = kwargs.get("alias") or kwargs.get("aliases") or list()
		self.permissions = kwargs.get("permissions", dict())
		self.arguments = kwargs.get("arguments") or kwargs.get("args") or list()
		self.category = kwargs.get("category", "Miscellaneous")
		self.examples = kwargs.get("examples", list())
		self.hidden = kwargs.get("hidden") or self.category == "Developer"
		self.flags = kwargs.get("flags", dict())
		self.free_to_use = kwargs.get("free_to_use", False)
		self.flags_enabled = kwargs.get("flags_enabled") or kwargs.get("flags")
		self.is_subcommand = is_subcommand
		self.func = func

		self.usage = []
		command_args = kwargs.get("arguments")

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

	def add_subcommand(self, command):
		self.subcommands[command.name] = command
