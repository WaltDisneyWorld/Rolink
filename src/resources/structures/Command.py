from inspect import iscoroutinefunction
from ..exceptions import PermissionError


class Command:
	def __init__(self, command):
		self.name = command.__class__.__name__.replace("Command", "").lower()
		self.subcommands = {}
		self.description = command.__doc__ or "N/A"
		self.dm_allowed = getattr(command, "dm_allowed", False)
		self.full_description = getattr(command, "full_description", self.description)
		self.aliases = getattr(command, "aliases", [])
		self.permissions = getattr(command, "permissions", {})
		self.arguments = getattr(command, "arguments", [])
		self.category = getattr(command, "category", "Miscellaneous")
		self.examples = getattr(command, "examples", [])
		self.hidden = getattr(command, "hidden", self.category == "Developer")
		self.flags = getattr(command, "flags", {})
		self.free_to_use = getattr(command, "free_to_use", False)
		self.fn = command.__main__
		self.cooldown = getattr(command, "cooldown", 0)

		self.usage = []
		command_args = self.arguments

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


	def __str__(self):
		return self.name

	def __repr__(self):
		return str(self)

	async def check_permissions(self, author, locale, permissions=None):
		permissions = permissions or self.permissions

		if callable(permissions):
			try:
				if iscoroutinefunction(permissions):
					if not await permissions(author):
						raise PermissionError
				else:
					if not permissions(author):
						raise PermissionError

			except PermissionError:
				raise PermissionError("You do not meet the required permissions for this command.")
