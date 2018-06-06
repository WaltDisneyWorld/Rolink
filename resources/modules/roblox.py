import json
import aiohttp
from resources.structures import RobloxUser
from resources.framework import config
from random import choice

word_list = config.WORD


r = None


roblox_cache = {
	"roblox_ids_to_usernames": {},
	"usernames_to_roblox_ids": {},
	"roblox_ids_to_usernames": {},
	"discord_ids_to_roblox_ids": {},
	"author_users": {},
	"users": {}

}

base_url = "https://api.roblox.com/"

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def generate_code():
	words = []
	for _ in range(5):
		words.append(choice(word_list))
	return " ".join(words)

async def validate_code(username, code):
	user_cache = roblox_cache["users"].get(username)
	if user_cache:
		id = user_cache.id
	else:
		username, id = await get_id_from_api(username)
	if id:
		async with aiohttp.ClientSession() as session:
			response = await fetch(session, f'https://www.roblox.com/users/{id}/profile')
			return code in response

	return False

async def get_id_from_api(username):
	if roblox_cache["usernames_to_roblox_ids"].get(username):
		return username, roblox_cache["usernames_to_roblox_ids"][username]

	async with aiohttp.ClientSession() as session:
		response = await fetch(session, base_url + "/users/get-by-username/" \
			"?username=" + username)
		try:
			response = json.loads(response)
		except json.decoder.JSONDecodeError:
			return None, None
		else:
			roblox_cache["usernames_to_roblox_ids"][username] = response.get("Id")
			return response.get("Username"), response.get("Id")
	return None, None

async def get_username_from_api(id):
	if roblox_cache["roblox_ids_to_usernames"].get(id):
		return roblox_cache["roblox_ids_to_usernames"][id], id

	async with aiohttp.ClientSession() as session:
		response = await fetch(session, base_url + "/users/" + id)
		try:
			response = json.loads(response)
		except json.decoder.JSONDecodeError:
			return None, None
		else:
			username = response.get("Username")
			roblox_cache["roblox_ids_to_usernames"][id] = username
			return username, response.get("Id")
	return None, None

async def check_username(username, return_class_object=True):
	user_cache = roblox_cache["users"].get(username)
	if user_cache:
		return (return_class_object and user_cache) or user_cache.id
	else:
		username, id = await get_id_from_api(username)
		if username and id:
			user = RobloxUser(username=username, id=id)
			roblox_cache["users"][username] = user
			return (return_class_object and user) or id
		return False

async def check_id(id, return_class_object=True):
	username = roblox_cache["roblox_ids_to_usernames"].get(id)
	if username:
		user_cache = roblox_cache["users"].get(username)
		if user_cache:
			return (return_class_object and user_cache) or username
	else:
		username, id = await get_id_from_api(username)
		if username and id:
			user = RobloxUser(username=username, id=id)
			roblox_cache["users"][username] = user
			return (return_class_object and user) or username
		return False


async def get_details(username=None, id=None, complete=False):
	user_data = {
		"username": None,
		"id": None,
		"extras": {
			"avatar": None,
			"groups": {},
			"membership": None,
			"presence": None
		}

	}
	user = None
	if username:
		user = roblox_cache["users"].get(username)
	elif id:
		username = roblox_cache["roblox_ids_to_usernames"].get(id)
		if username:
			user = roblox_cache["users"].get(username)
	if user and user.is_verified:
		if user.id:
			user_data["id"] = user.id
		if user.username:
			user_data["username"] = user.username
		if complete:
			if user.avatar:
				user_data["extras"]["avatar"] = user.avatar
			if user.groups:
				user_data["extras"]["groups"] = user.groups
			if user.membership:
				user_data["extras"]["membership"] = user.membership
			if user.presence:
				user_data["extras"]["presence"] = user.presence

	roblox_name = user_data.get("username") or username
	roblox_id = user_data.get("id") or id

	if not roblox_name and roblox_id:
		# get username from id
		username, roblox_id = await get_username_from_api(roblox_id)
		user_data["username"] = username
		user_data["id"] = roblox_id
	elif not roblox_id and roblox_name:
		# get id from username
		name, id = await get_id_from_api(roblox_name)
		user_data["id"] = id
		user_data["username"] = name

	if complete:
		pass #TODO

	return user_data

async def get_user(username=None, id=None, author=None, guild=None, bypass=False):
	guild = guild or (hasattr(author, "guild") and author.guild)
	guild_id = guild and str(guild.id)

	if author:
		author_id = str(author.id)

		user_data = await r.table("users").get(author_id).run() or {}
		roblox_accounts = user_data.get("robloxAccounts", {})
		accounts = roblox_accounts.get("accounts", [])
		guilds = roblox_accounts.get("guilds", {})

		if username or id:
			user = RobloxUser(id=id, username=username)
			await user.fill_missing_details()
			if user.is_verified:
				if guild:
					if guilds.get(guild_id) == user.id:
						return user, accounts
					else:
						return None, accounts
				else:
					return user, accounts
			else:
				return None, accounts
		else:
			if guild:
				if guilds.get(guild_id):
					user = RobloxUser(id=guilds.get(guild_id))
					await user.fill_missing_details()
					if user.is_verified:
						return user, accounts
					else:
						return None, accounts
				else:
					return None, accounts
			else:
				return None, accounts
	elif username or id:
		user = RobloxUser(id=id, username=username)
		await user.fill_missing_details()
		if user.is_verified:
			return user, []
		else:
			return None, []



async def mass_filter(accounts=[], isIDs=True, isUsernames=False):
	parsed_accounts = []
	users = []

	isIDs = not isUsernames
	isUsernames = not isIDs

	for roblox_account in accounts:
		user = RobloxUser(id=isIDs and roblox_account, username=isUsernames and roblox_account)
		await user.fill_missing_details()
		if user.is_verified:
			parsed_accounts.append(user.username)
			users.append(user)

	return parsed_accounts, users

async def verify_member(author, roblox, guild=None, primary_account=None):
	author_id = str(author.id)
	guild = guild or (hasattr(author, "guild") and author.guild)
	if isinstance(roblox, RobloxUser):
		roblox_id = str(roblox.id)
	else:
		roblox_id = str(roblox)
	user_data = await r.table("users").get(author_id).run() or {}
	roblox_accounts = user_data.get("robloxAccounts", {})
	roblox_list = roblox_accounts.get("accounts", [])
	if guild:
		guild_list = roblox_accounts.get("guilds", {})
		guild_list[str(guild.id)] = roblox_id
		roblox_accounts["guilds"] = guild_list
	if not roblox_id in roblox_list:
		roblox_list.append(roblox_id)
		roblox_accounts["accounts"] = roblox_list
	await r.table("users").insert(
		{
			"id": author_id,
			"robloxID": primary_account and roblox_id or user_data.get("robloxID"),
			"robloxAccounts": roblox_accounts
		},
		conflict="update"
	).run()

async def unverify_member(author, roblox):
	author_id = str(author.id)
	success = False
	if isinstance(roblox, RobloxUser):
		roblox_id = str(roblox.id)
	else:
		roblox_id = str(roblox)
	user_data = await r.table("users").get(author_id).run()
	roblox_accounts = user_data.get("robloxAccounts", {})
	roblox_list = roblox_accounts.get("accounts", [])
	guilds = roblox_accounts.get("guilds", {})
	if roblox_id in roblox_list:
		roblox_list.remove(roblox_id)
		roblox_accounts["accounts"] = roblox_list
		success = True
	for i,v in guilds.items():
		if v == roblox_id:
			guilds[i] = None
			roblox_accounts["guilds"] = guilds
			success = True
	await r.table("users").insert(
		{
			"id": author_id,
			"robloxAccounts": roblox_accounts
		},
		conflict="update"
	).run()
	return success


async def setup(client, command, rethinkdb, *args, **kwargs):
	global r
	r = rethinkdb
