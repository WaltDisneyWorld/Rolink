from asyncio import sleep
from json import loads

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

	async def premium_bind(self, author, **kwargs):
		DonatorProfile = await is_premium(author=author)
		return DonatorProfile.is_premium

	async def asset_bind(self, author, roblox_user, bind_data, **kwargs):
		if self.cache.get(roblox_user.id, {}).get(bind_data[0]):
			return True

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

	def get_virtual_group(self, name):
		name = name.replace("Bind", "_bind")

		if hasattr(self, name):
			return getattr(self, name)


def new_module():
	return VirtualGroups
