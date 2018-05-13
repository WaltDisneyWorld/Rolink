class Command:
	def __init__(self, name, func, **kwargs):
		self.name = name
		self.subcommands = []
		self.description = func.__doc__ or "N/A"
		self.aliases = kwargs.get("alias") or kwargs.get("aliases") or list()
		self.permissions = kwargs.get("permissions", list())
		self.arguments = kwargs.get("arguments", list())
		self.func = func
