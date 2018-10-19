from asyncio import sleep
from json import loads
from json.decoder import JSONDecodeError

from resources.exceptions import RobloxAPIError

from resources.module import get_module
is_premium, fetch = get_module("utils", attrs=["is_premium", "fetch"])

API_URL = "https://api.roblox.com/"




class VirtualGroups:
	def __init__(self, **kwargs):
		self.cache = {}

	async def setup(self):
		while True:
			await sleep(200)
			self.cache.clear()

	@staticmethod
	async def get_devforum_profile(username):
		try:
			response = await fetch(f"https://devforum.roblox.com/users/{username}.json")
			response = response[0]
			json = loads(response)
		except (RobloxAPIError, JSONDecodeError):
			return None
		else:
			return json.get("user")

	async def devForum_bind(self, author, roblox_user, **kwargs): # the capital F is there for a reason; see get_virtual_group
		if self.cache.get(roblox_user.id, {}).get("devforum") is not None:
			return self.cache.get(roblox_user.id, {}).get("devforum")

		devforum_profile = await self.get_devforum_profile(roblox_user.username)

		if devforum_profile:
			access = devforum_profile.get("trust_level", 0) > 0

			self.cache[roblox_user.id] = self.cache.get(roblox_user.id) or {}

			if access:
				self.cache[roblox_user.id]["devforum"] = True
				return True
			else:
				self.cache[roblox_user.id]["devforum"] = False


	async def premium_bind(self, author, **kwargs):
		DonatorProfile = await is_premium(author=author)
		return DonatorProfile.is_premium

	async def asset_bind(self, author, roblox_user, bind_data, **kwargs):
		if self.cache.get(roblox_user.id, {}).get(bind_data[0]) is not None:
			return self.cache.get(roblox_user.id, {}).get(bind_data[0])

		try:
			response = await fetch("https://inventory.roblox.com/v1/users/{}/items/{}/{}".format(
				roblox_user.id,
				bind_data[1].get("type", "Asset"),
				bind_data[0]
			))

			response = loads(response[0])

			self.cache[roblox_user.id] = self.cache.get(roblox_user.id) or {}

			if response.get("data"):
				self.cache[roblox_user.id][bind_data[0]] = True
				return True
			else:
				self.cache[roblox_user.id][bind_data[0]] = False

		except RobloxAPIError:
			return False

	def get_virtual_group(self, name):
		name = name.replace("Bind", "_bind")

		if hasattr(self, name):
			return getattr(self, name)


def new_module():
	return VirtualGroups
