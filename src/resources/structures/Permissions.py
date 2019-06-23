class Permissions:
	"""Contains permission attributes for commands"""

	def __init__(self, roles=None, **kwargs):
		self.allowed = {"roles":[], "discord_perms": []}
		self.exceptions = {"roles":[], }

		self.bloxlink_role = False

		if roles:
			self.allowed["roles"] = roles

	def build(self, *args, roles=None):
		if roles:
			self.allowed["roles"] += roles

		for arg in args:
			if arg in ("BLOXLINK_ADMIN", "BLOXLINK_MANAGER", "BLOXLINK_UPDATER", "BLOXLINK_MODERATOR"):
				self.bloxlink_role = arg.replace("_", " ").title()
			elif arg in ("MANAGE_ROLES", "BAN_MEMBERS", "KICK_MEMBERS", "MANAGE_SERVER"):
				self.allowed["discord_perms"].append(arg.replace("_", "").title())

		return self

	"""
	def only(self, *args, roles=None):
		if roles:
			self.only["roles"] += roles

		for arg in args:
			if arg in ("BLOXLINK_ADMIN", "BLOXLINK_MANAGER", "BLOXLINK_UPDATER"):
				self.bloxlink_roles_exceptions = False
				setattr(self, arg, True)

		return self
	"""

	def exception(self, *args, roles=None):
		if roles:
			self.exceptions["roles"] += roles

		return self
