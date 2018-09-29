from resources.module import get_module
get_user = get_module("roblox", attrs=["get_user"])


class Blacklist:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")
		self.r = kwargs.get("r")

	async def is_blacklisted(self, guild=None, author=None, roblox_id=None):
		blacklisted = await self.r.table("blacklisted").run()

		user = None

		if author:
			user, _ = await get_user(author=author)

		while await blacklisted.fetch_next():
			blacklist = await blacklisted.next()

			author = author or guild and guild.owner

			if author:

				if blacklist["id"] == str(author.id):
					return "You're blacklisted from the bot."
				else:
					if user:
						if blacklist["id"] == user.id:
							return "Your Roblox account is blacklisted from the bot."
			else:
				if blacklist["id"] == roblox_id:
					return "Your Roblox user is blacklisted."

		return False

def new_module():
	return Blacklist
