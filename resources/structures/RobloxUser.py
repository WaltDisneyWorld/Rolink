get_details = None

class RobloxUser:
	def __init__(self, username=None, id=None, **kwargs):
		self.username = username
		self.id = id

		self.is_complete = False
		self.is_verified = False

		self.groups = kwargs.get("groups", {})
		self.avatar = kwargs.get("avatar")
		self.membership = kwargs.get("membership")
		self.presence = kwargs.get("presence")
		self.badges = kwargs.get("badges", [])
		self.groups = kwargs.get("groups", {})

	async def fill_missing_details(self, complete=False):
		global get_details
		if not get_details:
			from resources.modules.roblox import get_details

		if not self.is_verified or (complete and not self.is_complete):
			data = await get_details(
				username=self.username,
				id = self.id,
				complete = complete
			)

			if data["username"] and data["id"]:
				self.username = data["username"]
				self.id = data["id"]
				self.is_verified = True

		if not self.is_complete and complete:
			self.avatar = data["extras"].get("avatar")
			self.membership = data["extras"].get("membership")
			self.presence = data["extras"].get("presence")
			self.badges = data["extras"].get("badges")
			self.is_complete = True
	def add_group(self, group):
		if not self.groups.get(group.name):
			self.groups[group.name] = group
