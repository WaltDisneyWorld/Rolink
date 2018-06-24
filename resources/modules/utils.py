from os import listdir
from random import choice, randint
from time import time
from math import ceil
from resources.modules.roblox import get_user

r = None


async def get_nickname(author, guild=None, roblox_user=None, guild_data=None):
	guild = guild or author.guild
	roblox_user = roblox_user or await get_user(author=author)
	if isinstance(roblox_user, tuple):
		roblox_user = roblox_user[0]

	if roblox_user:
		await roblox_user.fill_missing_details()
		if roblox_user.is_verified:
			guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
			template = guild_data.get("nicknameTemplate") or "{roblox-name}"

			group_rank, clan_tag = "Guest", ""

			if "{group-rank}" in template:
				group = roblox_user.groups.get(str(guild_data.get("groupID","0")))
				if group:
					group_rank = group.user_role

			if "{clan-tag}" in template:
				user_data = await r.table("users").get(str(author.id)).run() or {}
				clan_tags = user_data.get("clanTags", {})
				clan_tag = clan_tags.get(str(guild.id), "")

			return ("​" + template.replace(
				"{roblox-name}", roblox_user.username
			).replace(
				"{roblox-id}", roblox_user.id
			).replace(
				"{discord-name}", author.name
			).replace(
				"{discord-nick}", author.display_name
			).replace(
				"{group-rank}", group_rank
			).replace(
				"{clan-tag}", f'[{clan_tag.upper()}]'
			))[0:32]

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



async def setup(**kwargs):
	global r
	r = kwargs.get("r")
