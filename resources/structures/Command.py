class Command:
	def __init__(self, func, name=None, **kwargs):
		self.name = name or func.__name__
		self.subcommands = []
		self.description = func.__doc__ or "N/A"
		self.aliases = kwargs.get("alias") or kwargs.get("aliases") or list()
		self.permissions = kwargs.get("permissions", list())
		self.arguments = kwargs.get("arguments", list())
		self.func = func
