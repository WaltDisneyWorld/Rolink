import json
import aiohttp
import asyncio
from config import WORD as word_list
from discord.utils import find
from discord.errors import Forbidden
from resources.structures.RobloxUser import RobloxUser
from resources.structures.Group import Group
from resources.modules.utils import post_event
from random import choice



r = None

roblox_cache = {
	"users": {},
	"author_users": {},
	"groups": {},
	"roblox_ids_to_usernames": {},
	"usernames_to_roblox_ids": {}
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
	user_cache = roblox_cache["users"].get(username.lower())

	if user_cache:
		id = user_cache.id
	else:
		id = roblox_cache["usernames_to_roblox_ids"].get(username.lower())
		if not id:
			username, id = await get_id_from_api(username)
			roblox_cache["usernames_to_roblox_ids"][username.lower()] = (id, username)
	if id:
		async with aiohttp.ClientSession() as session:
			response = await fetch(session, f'https://www.roblox.com/users/{id}/profile')
			response = response[0]

			if code in response:
				user = RobloxUser(username=username, id=id)
				await user.fill_missing_details()
				roblox_cache["users"][username.lower()] = user
				return True

	return False

async def get_id_from_api(username):
	user = roblox_cache["usernames_to_roblox_ids"].get(username.lower())
	if user:
		return user[1], user[0]

	async with aiohttp.ClientSession() as session:
		response = await fetch(session, api_url + "/users/get-by-username/" \
			"?username=" + username)
		response = response[0]

		try:
			response = json.loads(response)
		except json.decoder.JSONDecodeError:
			return None, None
		else:
			username_, id = response.get("Username"), str(response.get("Id"))
			roblox_cache["usernames_to_roblox_ids"][username.lower()] = (id, username_)
			return username_, id

	return None, None

async def get_username_from_api(id):
	id = str(id)

	user = roblox_cache["roblox_ids_to_usernames"].get(id)
	if user:
		return user[1], id

	async with aiohttp.ClientSession() as session:
		response = await fetch(session, api_url + "/users/" + id)
		response = response[0]
		try:
			response = json.loads(response)
		except json.decoder.JSONDecodeError:
			return None, None
		else:
			username = response.get("Username")
			roblox_cache["roblox_ids_to_usernames"][id] = (id, username)
			return username, str(response.get("Id"))

	return None, None

async def check_username(username, return_class_object=True):
	username, id = await get_id_from_api(username)

	if username and id:
		user = RobloxUser(username=username, id=id)

		return return_class_object and user or id

	return False

async def get_details(username=None, id=None, complete=False):
	id = str(id)
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
		user = roblox_cache["users"].get(username.lower())
	elif id:
		username = roblox_cache["roblox_ids_to_usernames"].get(id)

		if username:
			user = roblox_cache["users"].get(username[1].lower())
			username = username[1]
	
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
		username, id = await get_id_from_api(roblox_name)
		user_data["id"] = id
		user_data["username"] = username
	elif roblox_id and roblox_name:
		username, id = await get_id_from_api(roblox_name)
		if username and id:
			user_data["id"] = id
			user_data["username"] = username
	else:
		return user_data

	if complete and user_data.get("id"):
		async with aiohttp.ClientSession() as session:
			icon_url = await fetch(session, base_url + "bust-thumbnail/json?userId=" \
				+ user_data["id"] + "&height=180&width=180")
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

			badges_url = await fetch(session, base_url + "badges/roblox?userId="+user_data["id"])
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
		user = roblox_cache["author_users"].get(author_id)

		if user:
			return user[0], user[1] # user, accounts

		user_data = await r.table("users").get(author_id).run() or {}
		roblox_accounts = user_data.get("robloxAccounts", {})
		accounts = roblox_accounts.get("accounts", [])
		guilds = roblox_accounts.get("guilds", {})

		if username or id:
			if id:
				id = str(id)

			if not username:
				username = roblox_cache["roblox_ids_to_usernames"].get(id)

				if username:
					user = roblox_cache["users"].get(username[1].lower())
					roblox_cache["author_users"][author_id] = (user, accounts)

					if user:
						return user, accounts

			user = RobloxUser(id=id, username=username)
			await user.fill_missing_details()

			if user.is_verified:
				roblox_cache["users"][user.username.lower()] = user
				roblox_cache["author_users"][author_id] = (user, accounts)

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
						roblox_cache["users"][user.username.lower()] = user
						roblox_cache["author_users"][author_id] = (user, accounts)

						return user, accounts
					else:
						return None, accounts
				else:
					if user_data.get("robloxID"):
						user = RobloxUser(id=user_data.get("robloxID"))
						await user.fill_missing_details()

						if user.is_verified:
							roblox_cache["users"][user.username.lower()] = user
							roblox_cache["author_users"][author_id] = (user, accounts)

							return user, accounts

					return None, accounts
			else:
				return None, accounts

	elif username or id:
		user = RobloxUser(id=id, username=username)
		await user.fill_missing_details()

		if user.is_verified:
			roblox_cache["users"][user.username.lower()] = user
			return user, []

		else:
			return None, []

async def get_user_groups(author=None, roblox_id=None, roblox_user=None):
	groups = {}

	"""
	if roblox_id:
		async with aiohttp.ClientSession() as session:
			response = await fetch(session, api_url + "/users/" + roblox_id + \
				"/groups")
			response = response[0]

			try:
				response = json.loads(response)
				for group_json in response:
					group = Group(group_json["Id"], **group_json)
					groups[group.id] = group

				return groups

			except json.decoder.JSONDecodeError:
				return {}
	"""
	if author and not roblox_id:
		if not roblox_user:
			roblox_user, _ = get_user(author=author)
			roblox_id = roblox_user and roblox_user.id

		if roblox_user.groups:
			return roblox_user.groups

	if roblox_id:
		roblox_user = roblox_user or RobloxUser(id=roblox_id)

		if roblox_user.groups:
			return roblox_user.groups

		if not roblox_user.id:
			await roblox_user.fill_missing_details()

		if not roblox_user.is_verified:
			return {}

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

async def get_roles(author, guild=None, complete=True):
	remove_roles = []
	add_roles = []
	errors = []
	possible_roles = []

	guild = guild or author.guild
	user, _ = await get_user(author=author)

	unverified_role = None

	if guild:

		if not user:
			unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

			if unverified_role:
				return [unverified_role], [], []
			else:
				return [], [], []

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
				errors.append("Unable to create Verified Role: please drag my role above "
				"the other roles and ensure I have the Manage Roles permission.")

		if verified_role:
			add_roles.append(verified_role)

		if complete:

			user_groups = await get_user_groups(author=author, roblox_user=user)

			role_binds = guild_data.get("roleBinds")
			group_id = guild_data.get("groupID")

			if role_binds:
				if isinstance(role_binds, list):
					role_binds = role_binds[0]

				for group_id_, data in role_binds.items():
					group = user_groups.get(group_id_)

					for rank, role_id in data.items():

						num = False

						try:
							num = int(rank) # doing this to capture negative bind values
						except ValueError:
							pass

						if group:
							user_rank = group.user_rank
							role = find(lambda r: r.id == int(role_id), guild.roles)

							if role:

								if rank.lower() == "all" or user_rank == rank or (num and num < 0 and int(user_rank) >= abs(num)):
									possible_roles.append(role)
									if not role in author.roles:
										add_roles.append(role)
								else:
									if not role in (*add_roles, *remove_roles, *possible_roles):
										if role in author.roles:
											remove_roles.append(role)
						else:
							if rank.lower() == "guest" or num == 0:
								role = find(lambda r: r.id == int(role_id), guild.roles)

								if role and not role in (*add_roles, *possible_roles) and not role in author.roles:
									add_roles.append(role)

			if group_id and group_id != "0":
				rank = await get_rank(user, group_id=group_id)
				group = await get_group(group_id)

				if rank:
					role = find(lambda r: r.name == rank, guild.roles)

					if not role:
						try:
							await guild.create_role(name=rank, reason="Creating missing group role")
						except Forbidden:
							errors.append("failed to create missing group role " + rank)

					if group and group.roles:
						for roleset in group.roles:
							member_role = find(lambda r: r.name == roleset["Name"], author.roles)
							if member_role:
								if rank != roleset:
									remove_roles.append(member_role)

					if role:
						add_roles.append(role)

	remove_roles = not guild_data.get("allowOldRoles") and [x for x in remove_roles if not x in (*add_roles, *possible_roles)] or []
	add_roles = [x for x in add_roles if not x in author.roles]

	return add_roles, remove_roles, errors

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
				clan_tag = clan_tag and f"[{clan_tag.upper()}]" or ""


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
				"{clan-tag}", clan_tag
			))[0:31]


async def give_roblox_stuff(author, roblox_user=None, complete=False, guild=None):
	guild = guild or author.guild
	roblox_user = roblox_user or await get_user(author=author)

	if isinstance(roblox_user, tuple):
		roblox_user = roblox_user[0]

	if not roblox_user:
		return [], [], []

	await roblox_user.fill_missing_details()

	if not roblox_user.is_verified:
		return [], [], []

	nickname = await get_nickname(author, roblox_user=roblox_user)
	add_roles, remove_roles, errors = await get_roles(author, complete=complete)
	added, removed = [], []

	if errors:
		for error in errors:
			await post_event(
				"error",
				error,
				guild=guild,
				color=0xE74C3C
			)

	if nickname:
		if author.nick != nickname:
			try:
				await author.edit(nick=nickname)
			except Forbidden:
				await post_event(
					"error",
					f"Failed to update {author.mention}'s nickname. Please ensure I " \
						"have the ``Manage Nickname`` permission, and drag my role above the other roles.",
					guild=guild,
					color=0xE74C3C
				)

	if remove_roles:
		try:
			await author.remove_roles(*remove_roles, atomic=True, reason="Removing old group roles")
			for role in remove_roles:
				removed.append(role.name)
		except Forbidden:
			await post_event(
				"error",
					f"Failed to remove {author.mention}'s role(s). Please ensure I " \
						"have the ``Manage Roles`` permission, and drag my role above the other roles.",
				guild=guild,
				color=0xE74C3C
			)
	if add_roles:
		try:
			await author.add_roles(*add_roles, atomic=True, reason="Adding group roles")
			for role in add_roles:
				added.append(role.name)
		except Forbidden:
			await post_event(
				"error",
					f"Failed to add role(s) to {author.mention}. Please ensure I " \
						"have the ``Manage Roles`` permission, and drag my role above the other roles.",
				guild=guild,
				color=0xE74C3C
			)
			errors.append("Failed to add group role. Please ensure I have the ``Manage Roles`` " \
			"permission, and drag my role above the other roles.")

	return added, removed, errors


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

async def verify_member(author, roblox, guild=None, primary_account=False):
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
	group = roblox_cache["groups"].get(group_id)

	if (group and not group.roles) or not group:
		async with aiohttp.ClientSession() as session:
			response = await fetch(session, api_url + "/groups/" + group_id)
			response = response[0]

			try:
				response = json.loads(response)

				if response.get("Id"):
					if not group:
						group = Group(id=response["Id"], **response)
					else:
						group.load_json(**response)

					roblox_cache["groups"][group_id] = group
					return group

			except json.decoder.JSONDecodeError:
				return {}

async def auto_cleanup():
	while True:
		await asyncio.sleep(600)
		global roblox_cache

		roblox_cache = {
			"users": {},
			"author_users": {},
			"groups": {},
			"roblox_ids_to_usernames": {},
			"usernames_to_roblox_ids": {}
		}

async def clear_user_from_cache(author):
	author_id = str(author.id)

	user = roblox_cache["author_users"].get(author_id)
	if user:
		roblox_cache["author_users"].pop(author_id, None)

		user_ = roblox_cache["users"].get(user[0].username.lower())

		if user_:
			roblox_cache["users"].pop(user[0].username.lower(), None)

		if user[1]:
			for account in user[1]:
				if roblox_cache["users"].get(account.lower()):
					roblox_cache["users"].pop(account.lower(), None)


async def setup(**kwargs):
	global r
	r = kwargs.get("r")
	client = kwargs.get("client")
	client.loop.create_task(auto_cleanup())
