from os import listdir
from random import choice, randint
from time import time
from math import ceil
from discord import Embed
from discord.utils import find
from discord.errors import Forbidden
from config import ERROR_CHANNEL, RELEASE
from resources.structures.DonatorProfile import DonatorProfile

from resources.module import get_module
is_patron = get_module("patreon", attrs=["is_patron"])

#is_patron = lambda u: u


class Utils:

	def __init__(self, **kwargs):
		self.r = kwargs.get("r")
		self.client = kwargs.get("client")
		self.error_channel = None

	async def get_prefix(self, guild, guild_data=None):
		if RELEASE == "MAIN" and guild.get_member(469652514501951518):
			return "!!"

		guild_data = guild_data or await self.r.table("guilds").get(str(guild.id)).run() or {}
		prefix = guild_data.get("prefix")

		if prefix and prefix != "!":
			return prefix


	def get_files(self, directory:str):
		return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__"]

	async def is_premium(self, guild=None, author=None):
		author = author or (guild and guild.owner)

		if author:

			# patreon stuff
			profile = await is_patron(author)
			if profile.is_premium:
				print("patreon stuff", flush=True)
				return profile

			# selly stuff
			author_data = await self.r.table("users").get(str(author.id)).run() or {}

			premium = author_data.get("premium", {})
			premium = premium if not isinstance(premium, bool) else {}
			expiry = premium and premium.get("expiry")
			# tier = premium and premium.get("tier", "bronze")

			if not expiry and expiry != 0:
				return DonatorProfile(author, False)

			t = time()
			is_p = expiry == 0 or expiry > t
			days = expiry != 0 and expiry > t and ceil((expiry - t)/86400) or 0

			"""
			if tier == "bronze":
				activated_guilds = premium.get("activatedGuilds", [])



				if isinstance(activated_guilds, dict):
					activated_guilds = []

				if not str(guild.id) in activated_guilds:
					return (False, days, {}, "bronze", is_p)

			"""

			if is_p:
				print("loading selly stuff", flush=True)

				profile = DonatorProfile(author, True)
				profile.load_selly({
					"days": days,
					"codes_redeemed": author_data.get("redeemed", {})
				})

				return profile
			else:
				print("1", flush=True)
				return DonatorProfile(author, False)
		else:
			print("2", flush=True)
			return DonatorProfile(author, False)
	
		print("returning nothing", flush=True)


	async def generate_code(self, prefix="bloxlink", duration=31, max_uses=1, tier="bronze"):
		abc = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
		numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]

		async def generate():
			code = [prefix]

			for _ in range(2):
				code.append("-")

				for _ in range(6):
					ran = randint(1, 2)
					ran = choice(ran == 1 and abc or numbers)
					code.append(ran)

			return "".join(code).upper()

		code = await generate()

		if not await self.r.table("keys").get(code).run():

			await self.r.table("keys").insert({
				"key": code,
				"duration": duration,
				"uses": max_uses,
				"tier": tier
			}).run()

			return code


	async def give_premium(self, author, duration=31, code="Manual Input", author_data=None, override=False, tier="bronze"):
		author_id = (isinstance(author, int) and str(author)) or (isinstance(author, str) and author) or str(author.id)
		author_data = author_data or await self.r.table("users").get(author_id).run() or {}

		redeemed = author_data.get("redeemed", {})
		premium_data = author_data.get("premium", {})
		premium_data = premium_data if not isinstance(author_data.get("premium"), bool) else {}
		had_premium = premium_data.get("expiry")

		to_change = 1
		t = time()

		if had_premium == 0:
			return (-1, False)
		elif not override and redeemed.get(code):
			return (1, True)

		if duration == 0:
			# lifetime premium
			to_change = 0
		elif had_premium and had_premium > t:
			# premium is still active; add time to it
			to_change = (duration * 86400) + had_premium
		else:
			# premium expired
			to_change = (duration * 86400) + t

		redeemed[code] = duration

		await self.r.table("users").insert({
			"id": author_id,
			"premium": {"expiry": ceil(to_change), "tier": tier},
			"redeemed": redeemed,
		}, conflict="update").run()

		return (duration, False)

	async def delete_code(self, code):
		entry = await self.r.table("keys").get(code).run()
		if entry:
			await self.r.table("keys").get(code).delete().run()

	async def redeem_code(self, author, code):
		entry = await self.r.table("keys").get(code).run()
		author_data = await self.r.table("users").get(str(author.id)).run() or {}

		if author_data.get("redeemed", {}).get(code):
			return (1, True)

		if entry:
			"""
			if entry.get("tier", "bronze") != author_data.get("premium", {}).get("tier", "bronze"):
				return (-2, False)
			"""

			duration, already_redeemed = await self.give_premium(
				author,
				duration=entry.get("duration", 31),
				author_data=author_data,
				code=code,
				override=False,
				# tier=entry.get("tier", "bronze")
			)
			if duration != -1:
				await self.activate_guild(guild=author.guild, author=author)
				await self.delete_code(code)

			return (duration, already_redeemed)
		else:
			return (None, None)

	async def activate_guild(self, guild, author):
		if guild.owner != author:
			return False, "You must own the server to activate premium."

		profile = await self.is_premium(author=author)

		if profile.is_premium:

			if profile.tier == "bronze":
				user_data = await self.r.table("users").get(str(author.id)).run()
				premium = user_data.get("premium", {})
				activated_guilds = premium.get("activatedGuilds", [])
				allowed = premium.get("activationCount", 1)

				if allowed > len(activated_guilds):
					activated_guilds.append(str(guild.id))
					premium["activatedGuilds"] = activated_guilds
					allowed -= 1
					premium["activationCount"] = allowed

					await self.r.table("users").insert({
						"id": str(author.id),
						"premium": premium
					}, conflict="update").run()

					return True, None
				else:
					return False, "You have too many activated servers. You must deactivate one with !deactivate."

			elif profile.tier == "pro":
				return False, "You already have Pro! You don't need to activate the server."
		else:
			return False, "You aren't subscribed to a tier."

		return False, "test"

	async def deactivate_guild(self, guild, author):
		profile = await self.is_premium(author=author)

		if profile.is_premium:

			if profile.tier == "bronze":
				user_data = await self.r.table("users").get(str(author.id)).run()
				premium = user_data.get("premium", {})
				activated_guilds = premium.get("activatedGuilds", [])
				allowed = premium.get("activationCount", 1)

				if str(guild.id) in activated_guilds:
					activated_guilds.remove(str(guild.id))
				else:
					return False, "This server doesn't have premium."

				premium["activatedGuilds"] = activated_guilds
				allowed += 1
				premium["activationCount"] = allowed

				await self.r.table("users").insert({
					"id": str(author.id),
					"premium": premium
				}, conflict="update").run()

				return True, None

			elif profile.tier == "pro":
				return False, "You already have Pro! You don't need to activate the server."
		else:
			return False, "You aren't subscribed to a tier."

	async def transfer_premium(self, original_user, new_user):
		pass

	async def post_event(self, event_name, text, guild=None, guild_data=None, channel=None, color=None):
		event_name_post = f"Bloxlink {event_name.title()} Event"

		if not channel:
			if not guild_data:
				if guild:
					guild_data = await self.r.table("guilds").get(str(guild.id)).run()

			if guild_data and not guild:
				guild = find(lambda g: g.id == int(guild_data.get("id")), self.client.guilds)

			if guild and guild_data:
				log_channels = guild_data.get("logChannels")

				if log_channels:
					channel_id = log_channels.get(event_name)

					if channel_id:
						channel_id = int(channel_id)
						channel = find(lambda c: c.id == channel_id, guild.text_channels)

		if channel:
			if color:
				embed = Embed(title=event_name_post, description=text, color=color)
			else:
				embed = Embed(title=event_name_post, description=text)

			try:
				await channel.send(embed=embed)
			except Forbidden:

				try:
					await channel.send(f"**{event_name_post}** ➜ {text}")
				except Forbidden:
					pass
			else:
				return True

		return False

	async def get_log_channel(self):
		await self.client.wait_for("ready")
		error_c = [guild.get_channel(ERROR_CHANNEL) for guild in self.client.guilds if guild.get_channel(ERROR_CHANNEL)][0]

		self.error_channel = error_c

	async def log_error(self, description, title="Uncaught Exception", color=0xE74C3C):
		embed = Embed(title=title, description=description, color=color)

		await self.error_channel.send(embed=embed)

	async def setup(self):
		self.client.loop.create_task(self.get_log_channel())

def new_module():
	return Utils
