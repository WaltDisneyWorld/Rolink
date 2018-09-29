from resources.exceptions import RobloxAPIError

roblox_module = None


class RobloxUserInit:

	def __init__(self, module):

		global roblox_module
		roblox_module = module


class RobloxUser:

	def __init__(self, username=None, id=None, **kwargs):
		self.username = username
		self.id = str(id)

		self.is_complete = False
		self.is_verified = False
		self.incomplete = False

		self.groups = kwargs.get("groups", {})
		self.avatar = kwargs.get("avatar")
		self.membership = kwargs.get("membership")
		self.presence = kwargs.get("presence")
		self.badges = kwargs.get("badges", [])
		self.groups = kwargs.get("groups", {})
		self.description = kwargs.get("description", "")
		self.is_banned = kwargs.get("banned", False)

		self.age = 0
		self.age_string = None
		self.profile_link = id and f"https://www.roblox.com/users/{id}/profile"

	async def fill_missing_details(self, complete=False):

		if (not self.is_verified or self.incomplete) or (complete and not self.is_complete):
			data = await roblox_module.get_details(
				username=self.username,
				id = self.id,
				complete = complete
			)

			if data["username"] and data["id"]:
				self.username = data["username"]
				self.id = str(data["id"])
				self.profile_link = self.profile_link or f"https://www.roblox.com/users/{self.id}/profile"
				self.is_verified = True

				try:
					self.add_groups(await roblox_module.get_user_groups(roblox_id=self.id))
					self.incomplete = False
				except RobloxAPIError:
					self.groups = {}
					self.incomplete = True

			if not self.is_complete and complete:
				self.avatar = data["extras"].get("avatar")
				self.membership = data["extras"].get("membership")
				self.presence = data["extras"].get("presence")
				self.badges = data["extras"].get("badges")
				self.age_string = data["extras"].get("age_string")
				self.age = data["extras"].get("age")
				self.description = data["extras"].get("description")
				self.is_banned = data["extras"].get("is_banned")

				if not self.incomplete:
					self.is_complete = True

	def add_group(self, group):
		if not self.groups.get(group.name):
			self.groups[group.name] = group

	def add_groups(self, groups):
		self.groups = groups

