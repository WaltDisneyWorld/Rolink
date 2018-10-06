from resources.exceptions import GroupNotFound
from asyncio import sleep
from discord.errors import DiscordException
from discord import Embed
import dateutil.parser

from resources.module import get_module
get_group_shout, get_group, get_user = get_module("roblox", attrs=["get_group_shout", "get_group", "get_user"])
is_premium = get_module("utils", attrs=["is_premium"])

last_shouts = {}

class TimedActions:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")
		self.r = kwargs.get("r")

	async def group_shouts(self):
		while True:
			feed = await self.r.table("guilds").filter(
				lambda guild: guild.has_fields("groupShout") and guild.has_fields("groupID")
			).run()

			while await feed.fetch_next():
				guild = await feed.next()

				try:
					actual_guild = self.client.get_guild(int(guild.get("actualId", "1")))

					if actual_guild:
						profile = await is_premium(guild=actual_guild)
						if profile.is_premium:
							group_id = str(guild.get("groupID"))

							if group_id:
								group_shout = guild.get("groupShout", {})
								channel = int(group_shout.get("channel", 0))
								channel = self.client.get_channel(channel)

								if channel:

									try:
										shout = await get_group_shout(group_id)
									except GroupNotFound:
										continue
									
									if not shout.get("shout"):
										continue

									datetime = dateutil.parser.parse(shout["shout"]["updated"])

									if group_shout.get("lastShout") != shout["shout"]["updated"]:
										group_shout["lastShout"] = shout["shout"]["updated"]

										await self.r.table("guilds").get(guild["id"]).update({
											"groupShout": group_shout
										}).run()

										group = await get_group(group_id)

										if group_shout.get("default"):
											embed = Embed(
												title="Group Shout",
												description=f'Shouted by: {shout["shout"]["poster"]["username"]}',
												timestamp=datetime
											)

											embed.set_author(
												name=shout["name"],
												icon_url=group.embed_url,
												url=group.url
											)

											embed.add_field(
												name="Shout:",
												value=shout["shout"]["body"]
											)

											if group_shout.get("prependContent"):
												try:
													await channel.send(content=group_shout.get("prependContent"), embed=embed)
												except DiscordException:
													pass
											else:
												try:
													await channel.send(embed=embed)
												except DiscordException:
													pass
										else:
											if "{group-rank}" in group_shout["format"]:
												user, _ = await get_user(id=shout["shout"]["poster"]["userId"])
												await user.fill_missing_details()

												user_group = user.groups.get(group_id)

												if user_group:
													group_rank = user_group.user_role
												else:
													group_rank = "Guest"
											else:
												group_rank = "Guest"

											if group_shout.get("cleanContent"):
												new_shout = shout["shout"]["body"].replace("@", "@\u200b")
											else:
												new_shout = shout["shout"]["body"]

											if new_shout:

												message = group_shout["format"].replace(
													"{group-name}", shout["name"]
												).replace(
													"{group-shout}", new_shout
												).replace(
													"{group-id}", group_id
												).replace(
													"{roblox-name}", shout["shout"]["poster"]["username"]
												).replace(
													"{roblox-id}", str(shout["shout"]["poster"]["userId"])
												).replace(
													"{group-rank}", group_rank
												)

												try:
													await channel.send(message)
												except DiscordException:
													pass
							else:
								# remove from db
								pass
				except:
					await sleep(60)

			await sleep(60)

	async def setup(self):
		await self.group_shouts()

def new_module():
	return TimedActions
