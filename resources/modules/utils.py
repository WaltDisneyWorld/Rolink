from os import listdir
from random import choice, randint
from time import time
from math import ceil
from discord import Embed
from discord.utils import find
from discord.errors import Forbidden
from config import ERROR_CHANNEL

r = None
error_channel = None


async def get_prefix(guild):
	guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

	prefix = guild_data.get("prefix")
	if prefix and prefix != "!":
		return prefix


def get_files(directory:str):
	return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__"]

async def is_premium(guild=None, author=None):
	author = author or (guild and guild.owner)

	if author:
		author_data = await r.table("users").get(str(author.id)).run() or {}

		premium = author_data.get("premium", {})
		premium = premium if not isinstance(premium, bool) else {}
		expiry = premium and premium.get("expiry")

		if not expiry and expiry !=0:
			return (False, None, {})

		t = time()
		is_p = expiry == 0 or expiry > t

		return (is_p, expiry != 0 and expiry > t and ceil((expiry - t)/86400) or 0, author_data.get("redeemed", {}))


async def generate_code(prefix="bloxlink", duration=31, max_uses=1):
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

	if not await r.table("keys").get(code).run():

		await r.table("keys").insert({
			"key": code,
			"duration": duration,
			"uses": max_uses
		}).run()

		return code

async def get_expiry(code):
	pass

async def give_premium(author, duration=31, code="Manual Input", author_data=None, override=False):
	author_id = str(author.id)
	author_data = author_data or await r.table("users").get(author_id).run()

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

	await r.table("users").insert({
		"id": author_id,
		"premium": {"expiry": ceil(to_change)},
		"redeemed": redeemed
	}, conflict="update").run()

	return (duration, False)

async def delete_code(code):
	entry = await r.table("keys").get(code).run()
	if entry:
		await r.table("keys").get(code).delete().run()

async def redeem_code(author, code):
	entry = await r.table("keys").get(code).run()
	author_data = await r.table("users").get(str(author.id)).run() or {}

	if author_data.get("redeemed", {}).get(code):
		return (1, True)

	if entry:
		duration, already_redeemed = await give_premium(
			author,
			duration=entry.get("duration", 31),
			author_data = author_data,
			code=code,
			override=False
		)
		await delete_code(code)

		return (duration, already_redeemed)
	else:
		return (None, None)

async def post_event(event_name, text, guild=None, guild_data=None, channel=None, color=None):
	event_name_post = f"Bloxlink {event_name.title()} Event"

	if not channel:

		if not guild_data:
			if guild:
				guild_data = await r.table("guilds").get(str(guild.id)).run()

		if guild_data and not guild:
			guild = find(lambda g: g.id == int(guild_data.get("id")), client.guilds)

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

async def get_log_channel():
	await client.wait_for("ready")
	error_c = [guild.get_channel(ERROR_CHANNEL) for guild in client.guilds if guild.get_channel(ERROR_CHANNEL)][0]

	global error_channel
	error_channel = error_c

async def log_error(description, title="Uncaught Exception", color=0xE74C3C):
	embed = Embed(title=title, description=description, color=color)

	await error_channel.send(embed=embed)



async def setup(**kwargs):
	global r
	global client
	r = kwargs.get("r")
	client = kwargs.get("client")

	client.loop.create_task(get_log_channel())
