class Command:
	def __init__(self, func, name=None, is_subcommand=False, **kwargs):
		self.name = name or func.__name__
		self.subcommands = {}
		self.description = func.__doc__ or "N/A"
		self.aliases = kwargs.get("alias") or kwargs.get("aliases") or list()
		self.permissions = kwargs.get("permissions", dict())
		self.arguments = kwargs.get("arguments") or kwargs.get("args") or list()
		self.category = kwargs.get("category", "Miscellaneous")
		self.hidden = kwargs.get("hidden", False)
		self.flags = kwargs.get("flags", dict())
		self.free_to_use = kwargs.get("free_to_use", False)
		self.is_subcommand = is_subcommand
		self.func = func
	def add_subcommand(self, command):
		self.subcommands[command.name] = command
