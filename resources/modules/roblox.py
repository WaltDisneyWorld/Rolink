import json
import aiohttp
from discord.utils import find
from discord.errors import Forbidden
from resources.structures import RobloxUser, Group
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
	"users": {},
	"groups": {}

}

api_url = "https://api.roblox.com/"
base_url = "https://roblox.com/"


async def fetch(session, url):
	async with session.get(url) as response:
		return await response.text(), response

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
			response = response[0]
			return code in response

	return False

async def get_id_from_api(username):
	if roblox_cache["usernames_to_roblox_ids"].get(username):
		return username, roblox_cache["usernames_to_roblox_ids"][username]

	async with aiohttp.ClientSession() as session:
		response = await fetch(session, api_url + "/users/get-by-username/" \
			"?username=" + username)
		response = response[0]
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
		response = await fetch(session, api_url + "/users/" + id)
		response = response[0]
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
			"presence": None,
			"badges": []
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
			if user.badges:
				user_data["extras"]["badges"] = user.badges

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
	elif roblox_id and roblox_name:
		name, id = await get_id_from_api(roblox_name)
		if name and id:
			user_data["id"] = id
			user_data["username"] = name
	else:
		return user_data

	if complete and user_data["id"]:
		async with aiohttp.ClientSession() as session:
			icon_url = await fetch(session, base_url + "bust-thumbnail/json?userId=" \
				+ str(user_data["id"]) + "&height=180&width=180")
			icon_url = icon_url[0]
			try:
				icon_url = json.loads(icon_url)
				user_data["extras"]["avatar"] = icon_url.get("Url")
			except json.decoder.JSONDecodeError:
				pass

			presence_url = await fetch(session, base_url + "presence/user?userId=" \
				+ str(user_data["id"]))
			presence_url = presence_url[0]
			try:
				presence_url = json.loads(presence_url)
				presence = presence_url.get("LastLocation")

				if presence == "Playing":
					presence = "playing a game"
				elif presence == "Offline":
					presence = "offline"
				elif presence == "Online" or presence == "Website":
					presence = "browsing the website"
				elif presence == "Creating":
					presence = "in studio"

				user_data["extras"]["presence"] = presence

			except json.decoder.JSONDecodeError:
				pass

			badges_url = await fetch(session, base_url + "badges/roblox?userId="+str(user_data["id"]))
			badges_url = badges_url[0]

			try:
				badges = json.loads(badges_url)
				if badges.get("RobloxBadges"):
					for badge in badges["RobloxBadges"]:
						if badge["Name"] == "Outrageous Builders Club":
							user_data["extras"]["membership"] = "OBC"
						elif badge["Name"] == "Turbo Builders Club":
							user_data["extras"]["membership"] = "TBC"
						elif badge["Name"] == "Builders Club":
							user_data["extras"]["membership"] = "BC"
						else:
							user_data["extras"]["badges"].append(badge["Name"])
							user_data["extras"]["membership"] = "NBC"

			except json.decoder.JSONDecodeError:
				pass

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

async def get_user_groups(author, roblox_user=None):
	groups = {}

	roblox_user = roblox_user or get_user(author=author)

	if roblox_user.groups:
		return roblox_user.groups

	if not roblox_user.id:
		roblox_user.fill_missing_details()

	if not roblox_user.is_verified:
		return {}

	roblox_id = str(roblox_user.id)

	async with aiohttp.ClientSession() as session:
		response = await fetch(session, api_url + "/users/" + roblox_id + \
			"/groups")
		response = response[0]

		try:
			response = json.loads(response)
			for group_json in response:
				group = Group(group_json["Id"], **group_json)
				roblox_user.add_group(group)
				groups[group.id] = group

		except json.decoder.JSONDecodeError:
			return {}

	return groups


async def get_rank(roblox_user, group=None, group_id=None):
	if not group and group_id:
		group_id = str(group_id)
		group = roblox_cache["groups"].get(group_id) or Group(id=group_id)
		if not roblox_cache["groups"].get(group_id):
			roblox_cache["groups"][group_id] = group
	elif group and not group_id:
		group_id = group.id

	if not group_id:
		return

	async with aiohttp.ClientSession() as session:
		response = await fetch(session, base_url + "Game/LuaWebService/HandleSocialRequest.ashx?" \
			f'method=GetGroupRole&playerid={roblox_user.id}&groupid={group_id}')
		response = response[0]

		return response != "Guest" and response.strip()

async def get_roles(author, guild=None):
	remove_roles = []
	add_roles = []
	errors = []
	error_num = 0

	guild = guild or author.guild
	user, _ = await get_user(author=author)

	unverified_role = None

	if guild:

		if not user:
			unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

			if unverified_role:
				return [unverified_role]
			else:
				return [], [], ["1) not verified"]

		guild_id = str(guild.id)

		guild_data = await r.table("guilds").get(guild_id).run() or {}

		verified_role_name = guild_data.get("verifiedRoleName", "Verified")
		verified_role = find(lambda r: r.name == verified_role_name, guild.roles)

		if not verified_role:
			try:
				verified_role = await guild.create_role(
					name=verified_role_name,
					reason="Verified Role"
				)
			except Forbidden:
				error_num += 1
				errors.append(str(error_num) + ") Unable to create Verified Role: please drag my role above"
				"the other roles and ensure I have the Manage Roles permission.")

		if verified_role:
			add_roles.append(verified_role)

		user_groups = await get_user_groups(author=author, roblox_user=user)

		role_binds = guild_data.get("roleBinds")
		group_id = guild_data.get("groupID")

		if role_binds:

			for group_id_, data in role_binds.items():

				if user_groups.get(group_id_):

					group = user_groups.get(group_id_)

					for rank, role_id in data.items():

						try:
							num = int(rank)
						except ValueError:
							pass

						user_rank = group.user_rank

						role = find(lambda r: r.id == int(role_id), guild.roles)

						if role:
							if rank == "all" or user_rank == rank or (num and num < 0 and int(user_rank) >= abs(num)):
								if not role in author.roles:
									add_roles.append(role)
							else:
								if role in author.roles:
									remove_roles.append(role)
		if group_id and group_id != "0":
			rank = await get_rank(user, group_id=group_id)
			role = find(lambda r: r.name == rank, guild.roles)

			if not role:
				try:
					await guild.create_role(name=rank, reason="Adding missing group role")
				except Forbidden:
					error_num += 1
					errors.append(str(error_num)+") failed to create missing group role " \
						+ rank)

			if role:
				add_roles.append(role)
			else:
				error_num += 1
				errors.append(str(error_num)+") not in the linked group")



	remove_roles = [x for x in remove_roles if not x in add_roles]

	return add_roles, remove_roles, errors

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


async def get_group(group_id):
	group_id = str(group_id)
	if roblox_cache["groups"].get(group_id):
		return roblox_cache["groups"].get(group_id)
	else:
		async with aiohttp.ClientSession() as session:
			response = await fetch(session, api_url + "/groups/" + group_id)
			response = response[0]

			try:
				response = json.loads(response)

				if response.get("Id"):
					group = Group(id=response["Id"], **response)
					roblox_cache["groups"][group_id] = group
					return group

			except json.decoder.JSONDecodeError:
				return {}


async def setup(**kwargs):
	global r
	r = kwargs.get("r")
