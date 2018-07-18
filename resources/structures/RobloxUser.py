get_details = None
get_user_groups = None

class RobloxUser:
	def __init__(self, username=None, id=None, **kwargs):
		self.username = username
		self.id = str(id)

		self.is_complete = False
		self.is_verified = False

		self.groups = kwargs.get("groups", {})
		self.avatar = kwargs.get("avatar")
		self.membership = kwargs.get("membership")
		self.presence = kwargs.get("presence")
		self.badges = kwargs.get("badges", [])
		self.groups = kwargs.get("groups", {})

		self.age = 0
		self.age_string = None

	async def fill_missing_details(self, complete=False):
		global get_details
		global get_user_groups
		if not get_details:
			from resources.modules.roblox import get_details, get_user_groups

		if not self.is_verified or (complete and not self.is_complete):
			data = await get_details(
				username=self.username,
				id = self.id,
				complete = complete
			)

			if data["username"] and data["id"]:
				self.username = data["username"]
				self.id = str(data["id"])
				self.is_verified = True
				self.add_groups(await get_user_groups(roblox_id=self.id))

		if not self.is_complete and complete:
			self.avatar = data["extras"].get("avatar")
			self.membership = data["extras"].get("membership")
			self.presence = data["extras"].get("presence")
			self.badges = data["extras"].get("badges")
			self.age_string = data["extras"].get("age_string")
			self.age = data["extras"].get("age")

			self.is_complete = True

	def add_group(self, group):
		if not self.groups.get(group.name):
			self.groups[group.name] = group

	def add_groups(self, groups):
		self.groups = groups
