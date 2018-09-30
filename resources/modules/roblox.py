import json
import re
import asyncio
import aiohttp
from discord.utils import find
from config import WORD, RETRY_AFTER
from discord.errors import Forbidden
from resources.structures.RobloxUser import RobloxUser, RobloxUserInit
from resources.structures.Group import Group
from random import choice, randint
from bs4 import BeautifulSoup
from datetime import datetime

from resources.exceptions import RobloxAPIError, PermissionError, GroupNotFound
from aiohttp.client_exceptions import ClientOSError

from resources.module import get_module
post_event, is_premium = get_module("utils", attrs=["post_event", "is_premium"])


api_url = "https://api.roblox.com/"
base_url = "https://roblox.com/"


async def fetch(session, url, raise_on_failure=True, retry=RETRY_AFTER):
	try:
		async with session.get(url) as response:
			text = await response.text()
			if raise_on_failure:
				if response.status != 200:
					if retry != 0:
						retry -= 1
						await asyncio.sleep(1.0)

						return await fetch(session, url, raise_on_failure=raise_on_failure, retry=retry)

					raise RobloxAPIError

			if text == "The service is unavailable.":
				raise RobloxAPIError

			return text, response
	except ClientOSError:
		# todo: raise HttpError with non-roblox URLs
		raise RobloxAPIError


class Roblox:
	def __init__(self, **kwargs):
		self.r = kwargs.get("r")
		self.session = kwargs.get("session")
		self.client = kwargs.get("client")
		self.roblox_cache = {
			"users": {},
			"author_users": {},
			"groups": {},
			"roblox_ids_to_usernames": {},
			"usernames_to_roblox_ids": {}
		}
		RobloxUserInit(self)

	async def generate_code(self):
		words = []

		for i in range(5):
			x = randint(1,2)

			words.append(choice(WORD))

			if i != 4:
				words.append(x == 1 and "and" or "or")

		return " lol ".join(words)

	async def validate_code(self, username, code):
		user_cache = self.roblox_cache["users"].get(username.lower())

		if user_cache:
			id_ = user_cache.id
		else:
			id_ = self.roblox_cache["usernames_to_roblox_ids"].get(username.lower())

			if not id_:
				username_, id_ = await self.get_id_from_api(username)
				self.roblox_cache["usernames_to_roblox_ids"][username_.lower()] = (id_, username)
			else:
				id_ = id_[0]
		if id_:

			response = await fetch(self.session, f'https://www.roblox.com/users/{id_}/profile', raise_on_failure=True)
			response = response[0]

			if code in response:
				user = RobloxUser(username=username, id=id_)
				await user.fill_missing_details()
				self.roblox_cache["users"][username.lower()] = user

				return True

		return False
	
	async def get_id_from_api(self, username):
		user = self.roblox_cache["usernames_to_roblox_ids"].get(username.lower())
		if user:
			return user[1], user[0]

		
		response = await fetch(self.session, api_url + "users/get-by-username/" \
			"?username=" + username, raise_on_failure=True)
		response = response[0]

		try:
			response = json.loads(response)
		except json.decoder.JSONDecodeError:
			return None, None
		else:
			username_, id = response.get("Username"), str(response.get("Id"))
			self.roblox_cache["usernames_to_roblox_ids"][username.lower()] = (id, username_)
			return username_, id

		return None, None

	async def get_username_from_api(self, id):
		id = str(id)

		user = self.roblox_cache["roblox_ids_to_usernames"].get(id)
		if user:
			return user[1], id


		response = await fetch(self.session, api_url + "users/" + id, raise_on_failure=True)
		response = response[0]
		try:
			response = json.loads(response)
		except json.decoder.JSONDecodeError:
			return None, None
		else:
			username = response.get("Username")
			self.roblox_cache["roblox_ids_to_usernames"][id] = (id, username)
			return username, str(response.get("Id"))

		return None, None

	async def check_username(self, username, return_class_object=True):
		username, id = await self.get_id_from_api(username)

		if username and id:
			user = RobloxUser(username=username, id=id)

			return return_class_object and user or id

		return False

	async def get_details(self, username=None, id=None, complete=False, raise_on_failure=True):
		id = str(id)

		user_data = {
			"username": None,
			"id": None,
			"extras": {
				"avatar": None,
				"groups": {},
				"membership": None,
				"presence": None,
				"badges": [],
				"age": 0,
				"age_string": None,
				"is_banned": False
			}

		}

		user = None

		if username:
			user = self.roblox_cache["users"].get(username.lower())
		elif id:
			username = self.roblox_cache["roblox_ids_to_usernames"].get(id)

			if username:
				user = self.roblox_cache["users"].get(username[1].lower())
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
				if user.age:
					user_data["extras"]["age"] = user.age
				if user.age_string:
					user_data["extras"]["age_string"] = user.age_string


		roblox_name = user_data.get("username") or username
		roblox_id = user_data.get("id") or id

		if not roblox_name and roblox_id:
			# get username from id
			username, roblox_id = await self.get_username_from_api(roblox_id)
			user_data["username"] = username
			user_data["id"] = roblox_id
		elif not roblox_id and roblox_name:
			# get id from username
			username, id = await self.get_id_from_api(roblox_name)
			user_data["id"] = id
			user_data["username"] = username
		elif roblox_id and roblox_name:
			username, id = await self.get_id_from_api(roblox_name)
			if username and id:
				user_data["id"] = id
				user_data["username"] = username
		else:
			return user_data

		if complete and user_data.get("id"):

			async def coro1():
				icon_url = await fetch(self.session, base_url + "bust-thumbnail/json?userId=" \
					+ user_data["id"] + "&height=180&width=180", raise_on_failure=raise_on_failure)
				icon_url = icon_url[0]

				try:
					icon_url = json.loads(icon_url)
					user_data["extras"]["avatar"] = icon_url.get("Url")
				except json.decoder.JSONDecodeError:
					raise RobloxAPIError

				presence_url = await fetch(self.session, base_url + "presence/user?userId=" \
					+ str(user_data["id"]), raise_on_failure=raise_on_failure)
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
					raise RobloxAPIError

				#print("coro1 done", flush=True)

			async def coro2():
				badges_url = await fetch(self.session, base_url + "badges/roblox?userId="+user_data["id"],
				raise_on_failure=raise_on_failure)
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
					raise RobloxAPIError
				#print("coro2 done", flush=True)

			async def coro3():

				try:

					#print("3.0 done", flush=True)
					user_page = await fetch(self.session, f'{base_url}users/{user_data["id"]}/profile')
					user_page = user_page[0]
					#print("3.1 done", flush=True)

					soup = BeautifulSoup(user_page, 'html.parser')
					#print("3.2 done", flush=True)

					for text in soup.body.find_all('p', attrs={'class':'text-lead'}):
						text = text.text

						if "/" in text:
							text = text[:text.index("Place")]
							user_data["extras"]["age_string"] = text

							today = datetime.today()
							datetime_object = datetime.strptime(text, '%m/%d/%Y')

							difference = today - datetime_object

							user_data["extras"]["age"] = difference.days

							break

					desc = soup.body.find('div', attrs={'class':'profile-about-content'})
					user_data["extras"]["description"] = desc and desc.text.strip("Read More")

					if desc is None:
						user_data["extras"]["is_banned"] = True

				except RobloxAPIError:
					user_data["extras"]["is_banned"] = True

			futures = []

			futures.append(asyncio.ensure_future(coro1()))
			futures.append(asyncio.ensure_future(coro2()))
			futures.append(asyncio.ensure_future(coro3()))

			await asyncio.gather(*futures)

		return user_data

	async def get_user(self, username=None, id=None, author=None, guild=None, bypass=False, raise_on_failure=True):
		guild = guild or (hasattr(author, "guild") and author.guild)
		guild_id = guild and str(guild.id)

		if author:
			author_id = str(author.id)
			user = self.roblox_cache["author_users"].get(author_id)

			if user:
				return user[0], user[1] # user, accounts

			user_data = await self.r.table("users").get(author_id).run() or {}
			roblox_accounts = user_data.get("robloxAccounts", {})
			accounts = roblox_accounts.get("accounts", [])
			guilds = roblox_accounts.get("guilds", {})

			if username or id:
				if id:
					id = str(id)

				if not username:
					username = self.roblox_cache["roblox_ids_to_usernames"].get(id)

					if username:
						user = self.roblox_cache["users"].get(username[1].lower())
						self.roblox_cache["author_users"][author_id] = (user, accounts)

						if user:
							return user, accounts

				user = RobloxUser(id=id, username=username)
				await user.fill_missing_details()

				if user.is_verified:
					self.roblox_cache["users"][user.username.lower()] = user
					self.roblox_cache["author_users"][author_id] = (user, accounts)

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
							self.roblox_cache["users"][user.username.lower()] = user
							self.roblox_cache["author_users"][author_id] = (user, accounts)

							return user, accounts
						else:
							return None, accounts
					else:
						if user_data.get("robloxID"):
							user = RobloxUser(id=user_data.get("robloxID"))
							await user.fill_missing_details()

							if user.is_verified:
								self.roblox_cache["users"][user.username.lower()] = user
								self.roblox_cache["author_users"][author_id] = (user, accounts)

								return user, accounts

						return None, accounts
				else:
					if user_data.get("robloxID"):
						user = RobloxUser(id=user_data.get("robloxID"))
						await user.fill_missing_details()

						return user, accounts
					else:
						return None, accounts

		elif username or id:
			user = RobloxUser(id=id, username=username)
			await user.fill_missing_details()

			if user.is_verified:
				self.roblox_cache["users"][user.username.lower()] = user
				return user, []

			else:
				return None, []

	async def get_user_groups(self, author=None, roblox_id=None, roblox_user=None, raise_on_failure=True):
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
				roblox_user, _ = await self.get_user(author=author)
				roblox_id = roblox_user and roblox_user.id

			if roblox_user.groups:
				return roblox_user.groups

		if roblox_id:
			roblox_user = roblox_user or RobloxUser(id=roblox_id)

			if roblox_user.groups:
				return roblox_user.groups

			response = await fetch(self.session, api_url + "users/" + roblox_id + \
				"/groups", raise_on_failure=True)
			response = response[0]

			try:
				response = json.loads(response)
				if isinstance(response, str):
					# await log_error(response, "Line 430 roblox.py - group json error")

					raise RobloxAPIError # UserNotFound

				try:

					for group_json in response:
						group = Group(group_json["Id"], **group_json)
						roblox_user.add_group(group)
						groups[group.id] = group
				except TypeError:
					# await log_error(f"{response} - {roblox_id}", "Line 442 roblox.py - group json error")

					raise RobloxAPIError # UserNotFound

			except json.decoder.JSONDecodeError:
				return {}

		return groups

	async def get_rank(self, roblox_user, group=None, group_id=None):
		if not group and group_id:
			group_id = str(group_id)
			group = self.roblox_cache["groups"].get(group_id) or Group(id=group_id)

			if not self.roblox_cache["groups"].get(group_id):
				self.roblox_cache["groups"][group_id] = group

		elif group and not group_id:
			group_id = group.id

		if not group_id:
			return

		response = await fetch(self.session, base_url + "Game/LuaWebService/HandleSocialRequest.ashx?" \
			f'method=GetGroupRole&playerid={roblox_user.id}&groupid={group_id}', raise_on_failure=True)
		response = response[0]

		return response != "Guest" and response.strip()

	async def get_roles(self, author, roblox_user=None, guild=None, complete=True):
		remove_roles = []
		add_roles = []
		errors = []
		possible_roles = []
		possible_nicknames = []

		top_role_nickname = None

		guild = guild or author.guild

		user = roblox_user or await self.get_user(author=author)

		if isinstance(user, tuple):
			user = user[0]

		if user:
			if user.is_verified:
				user_groups = user.groups
			else:
				user_groups = await self.get_user_groups(author=author, roblox_user=user)
			if user.incomplete:
				raise RobloxAPIError


		unverified_role = None
		role = None

		if guild:
			unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

			if not user:
				unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

				if unverified_role:
					return [unverified_role], [], [], []
				else:
					return [], [], [], []
			else:
				if unverified_role in author.roles:
					remove_roles.append(unverified_role)

			guild_id = str(guild.id)

			guild_data = await self.r.table("guilds").get(guild_id).run() or {}

			suspended_rank = guild_data.get("suspendedRank")

			if suspended_rank:
				main_group = str(guild_data.get("groupID")) or "1"

				if user_groups.get(main_group):
					if user_groups.get(main_group).user_role == suspended_rank:
						return [], [], [], []

			verified_role_name = guild_data.get("verifiedRoleName", "Verified")[0:99]
			verified_role = find(lambda r: r.name == verified_role_name, guild.roles)

			if not verified_role:
				try:
					verified_role = await guild.create_role(
						name=verified_role_name[0:99],
						reason="Verified Role"
					)
				except Forbidden:
					raise PermissionError("Sorry, I wasn't able to create the Verified role. "
					"Please drag my role above the other roles and ensure I have the Manage Roles permission.")

			if verified_role:
				add_roles.append(verified_role)

			if complete:

				user_groups = user_groups or await self.get_user_groups(author=author, roblox_user=user)

				role_binds = guild_data.get("roleBinds")
				group_id = guild_data.get("groupID")

				if role_binds:
					if isinstance(role_binds, list):
						role_binds = role_binds[0]

					for group_id_, data in role_binds.items():
						group = user_groups.get(str(group_id_))

						for rank, data_ in data.items():
							if not isinstance(data_, dict):
								data_ = {"nickname": None, "roles": [str(data_)]}

							num = False

							try:
								num = int(rank) # doing this to capture negative bind values
							except ValueError:
								pass

							if group:
								user_rank = group.user_rank

								for role_id in data_.get("roles", []):
									role = find(lambda r: int(float(r.id)) == int(float(role_id)), guild.roles)

									if role:

										if rank.lower() == "all" or user_rank == rank or (num and num < 0 and int(user_rank) >= abs(num)):
											possible_roles.append(role)

											nickname = data_.get("nickname")

											if nickname:

												if role == author.top_role:
													top_role_nickname = await self.get_nickname(author=author, template=nickname, roblox_user=user)

												resolved_nickname = await self.get_nickname(author=author, template=nickname, roblox_user=user)

												if resolved_nickname and not resolved_nickname in possible_nicknames:
													possible_nicknames.append([role, resolved_nickname])
													# possible_nicknames.append(resolved_nickname)

											if not role in author.roles:
												add_roles.append(role)
										else:
											if not role in (*add_roles, *remove_roles, *possible_roles):
												if role in author.roles:
													remove_roles.append(role)
							else:
								for role_id in data_.get("roles", []):
									role_id = str(role_id)
									role = find(lambda r: int(float(r.id)) == int(float(role_id)), guild.roles)

									if role:
										if rank.lower() == "guest" or num is 0:
											possible_roles.append(role)
											if not role in (*author.roles, *add_roles):
												add_roles.append(role)
										else:
											if not role in (*add_roles, *remove_roles, *possible_roles):
												if role in author.roles:
													remove_roles.append(role)

				if group_id and group_id != "0":
					if user.groups.get(str(group_id)):
						group = user.groups.get(str(group_id))
						group_ = await self.get_group(group_id)
						roles = None

						if group_:
							roles = group_.roles

						rank = group.user_role
						role = find(lambda r: r.name == rank[0:99], guild.roles)

						if not role:
							if guild_data.get("dynamicRoles"):
								try:
									role = await guild.create_role(name=rank[0:99], reason="Creating missing group role")
								except Forbidden:
									raise PermissionError("Sorry, I wasn't able to create the role. "
									"Please ensure I have the Manage Roles permission. Refer to "
									"<https://support.discordapp.com/hc/en-us/articles/214836687-Role-Management-101> "
									"for more information.")

						if group and roles:
							for roleset in roles:
								member_role = find(lambda r: r.name == roleset["Name"].strip(), author.roles)

								if member_role:
									if rank != roleset:
										if not role in (*add_roles, *remove_roles, *possible_roles):
											remove_roles.append(member_role)

						if role:
							possible_roles.append(role)

							if not role in author.roles:
								add_roles.append(role)

						else:
							if not role in (*add_roles, *remove_roles, *possible_roles):
								if role in author.roles:
									remove_roles.append(role)
					else:
						if not role in (*add_roles, *remove_roles, *possible_roles):
							if role in author.roles:
								remove_roles.append(role)

		if guild_data.get("allowOldRoles"):
			if unverified_role and unverified_role in remove_roles:
				remove_roles = [unverified_role]
			else:
				remove_roles = []
		else:
			remove_roles = [x for x in remove_roles if x not in (*add_roles, *possible_roles)]

		add_roles = [x for x in add_roles if not x in author.roles]

		if top_role_nickname:
			possible_nicknames = [[author.top_role, top_role_nickname]]

		return add_roles, remove_roles, possible_nicknames, errors


	async def get_nickname(self, author, guild=None, template=None, roblox_user=None, ignore_trim=False, guild_data=None):

		guild = guild or author.guild
		roblox_user = roblox_user or await self.get_user(author=author)

		if isinstance(roblox_user, tuple):
			roblox_user = roblox_user[0]

		roblox_user = roblox_user or RobloxUser(username=None, id=None)

		guild_data = guild_data or await self.r.table("guilds").get(str(guild.id)).run() or {}

		if roblox_user:
			await roblox_user.fill_missing_details()

		"""

		if guild_data.get("nicknameLuaCode"):
			if await is_premium(guild=guild):
				success, nickname = await run_sandboxed(guild_data["nicknameLuaCode"], {
					"name": author.name,
					"id": str(author.id),
					"discrim": author.discriminator,
					"roblox_name": roblox_user.username,
					"roblox_id": roblox_user.id,
					"is_verified": bool(roblox_user),
					"groups": roblox_user.groups
				})
				print(success, nickname, flush=True)

				if success and nickname:
					return nickname
			"""

		if roblox_user:

			if roblox_user.is_verified:
				template = template or guild_data.get("nicknameTemplate") or "{roblox-name}"

				if "{disable-nicknaming}" in template:
					return None


				group_rank, clan_tag = "Guest", ""

				if "{group-rank}" in template:
					group = roblox_user.groups.get(str(guild_data.get("groupID","0")))

					if group:
						user_role = group.user_role
						brackets_match = re.search(r"\[(.*)\]", user_role)

						if brackets_match:
							group_rank = brackets_match.group(0)
						else:
							group_rank = group.user_role

				if "{clan-tag}" in template:
					user_data = await self.r.table("users").get(str(author.id)).run() or {}
					clan_tags = user_data.get("clanTags", {})
					clan_tag = clan_tags.get(str(guild.id), "")
					clan_tag = clan_tag and f"[{clan_tag.upper()}]" or ""

				for rank in re.findall(r"\{group-rank-(.*?)\}", template):
					group = roblox_user.groups.get(rank)
					role = group and group.user_role or "Guest"
					template = template.replace("{group-rank-"+rank+"}", role)


				template = template.replace(
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
				).replace(
					"{server-name}", guild.name
				)

				if ignore_trim:
					return template

				return template[0:31]


	async def give_roblox_stuff(self, author, roblox_user=None, complete=False, guild=None):
		guild = guild or author.guild
		roblox_user = roblox_user or await self.get_user(author=author)

		if isinstance(roblox_user, tuple):
			roblox_user = roblox_user[0]

		if not roblox_user:
			return [], [], []

		await roblox_user.fill_missing_details()

		if not roblox_user.is_verified:
			return [], [], []

		nickname = await self.get_nickname(author, roblox_user=roblox_user)
		add_roles, remove_roles, possible_nicknames, errors = await self.get_roles(author, roblox_user=roblox_user, complete=complete)
		added, removed = [], []

		if errors:
			for error in errors:
				await post_event(
					"error",
					error,
					guild=guild,
					color=0xE74C3C
				)

		if remove_roles:
			try:
				await author.remove_roles(*remove_roles, atomic=True, reason="Removing old group roles")
				for role in remove_roles:
					removed.append(role.name)
			except Forbidden:
				"""
				await post_event(
					"error",
						f"Failed to remove {author.mention}'s role(s). Please ensure I " \
							"have the ``Manage Roles`` permission, and drag my role above the other roles.",
					guild=guild,
					color=0xE74C3C
				)
				"""
				if author.top_role > guild.me.top_role:
					raise PermissionError("Sorry, this person has a higher role than me, so I can't "
					"update their roles due to Discord limitations. Please drag my role above the other roles.")

				#raise PermissionError("Sorry, I couldn't update this person's roles. Please ensure I "
				#"have the Manage Roles permission, and drag my role above the other roles.")
		if add_roles:
			try:
				await author.add_roles(*add_roles, atomic=True, reason="Adding group roles")
				for role in add_roles:
					added.append(role.name)
			except Forbidden:
				"""
				await post_event(
					"error",
						f"Failed to add role(s) to {author.mention}. Please ensure I " \
							"have the ``Manage Roles`` permission, and drag my role above the other roles.",
					guild=guild,
					color=0xE74C3C
				)
				errors.append("Failed to add group role. Please ensure I have the ``Manage Roles`` " \
				"permission, and drag my role above the other roles.")
				"""
				if author.top_role > guild.me.top_role:
					raise PermissionError("Sorry, this person has a higher role than me, so I can't "
					"update their roles due to Discord limitations. Please drag my role above the other roles.")

				raise PermissionError("Sorry, I couldn't add roles to this person. Please ensure "
				"I have the Manage Roles permission, and drag my role above the other roles.")

		if nickname or possible_nicknames:

			if possible_nicknames:
				if len(possible_nicknames) == 1:
					nickname = possible_nicknames[0][1]
				else:
					# get highest role with a nickname
					highest_role = sorted(possible_nicknames, key=lambda e: e[0].position, reverse=True)
					if highest_role:
						nickname = highest_role[0][1]


			if guild.owner == author:
				raise PermissionError("Sorry, I can't update the nickname of the server owner due to "
				"Discord limitations. You may edit your own nickname, or just ignore this error message."
				f"\nNickname: ``{nickname}``")
			else:
				if author.nick != nickname:
					try:
						await author.edit(nick=nickname)
					except Forbidden:
						"""
						await post_event(
							"error",
							f"Failed to update {author.mention}'s nickname. Please ensure I " \
								"have the ``Manage Nickname`` permission, and drag my role above the other roles.",
							guild=guild,
							color=0xE74C3C
						)
						"""
						if author.top_role > guild.me.top_role:
							raise PermissionError("Sorry, this person has a higher role than me, so I can't "
							"update their roles due to Discord limitations. Please drag my role above the other roles."
							f"\nNickname: ``{nickname}``")

						raise PermissionError("Sorry, I can't update this person's nickname. Please ensure I "
						"have the Manage Nickname permission, and drag my role above the other roles."
						f"\nNickname: ``{nickname}``")

		return added, removed, errors


	async def mass_filter(self, accounts=[], isIDs=True, isUsernames=False):
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

	async def verify_member(self, author, roblox, guild=None, primary_account=False):
		author_id = str(author.id)
		guild = guild or (hasattr(author, "guild") and author.guild)

		if isinstance(roblox, RobloxUser):
			roblox_id = str(roblox.id)
		else:
			roblox_id = str(roblox)

		user_data = await self.r.table("users").get(author_id).run() or {}
		roblox_accounts = user_data.get("robloxAccounts", {})
		roblox_list = roblox_accounts.get("accounts", [])

		if guild:
			guild_list = roblox_accounts.get("guilds", {})
			guild_list[str(guild.id)] = roblox_id
			roblox_accounts["guilds"] = guild_list

		if not roblox_id in roblox_list:
			roblox_list.append(roblox_id)
			roblox_accounts["accounts"] = roblox_list

		await self.r.table("users").insert(
			{
				"id": author_id,
				"robloxID": primary_account and roblox_id or user_data.get("robloxID"),
				"robloxAccounts": roblox_accounts
			},
			conflict="update"
		).run()

	async def unverify_member(self, author, roblox):
		author_id = str(author.id)
		success = False

		if isinstance(roblox, RobloxUser):
			roblox_id = str(roblox.id)
		else:
			roblox_id = str(roblox)

		user_data = await self.r.table("users").get(author_id).run()
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

		await self.r.table("users").insert(
			{
				"id": author_id,
				"robloxAccounts": roblox_accounts
			},
			conflict="update"
		).run()

		return success

	async def get_group_shout(self, group_id):
		"""gets the group shout. not cached."""

		text, response = await fetch(self.session, f"https://groups.roblox.com/v1/groups/{group_id}", raise_on_failure=False)

		if response.status != 200:
			raise GroupNotFound

		try:
			response = json.loads(text)
			return response

		except json.decoder.JSONDecodeError:
			return {}


	async def get_group(self, group_id):
		group_id = str(group_id)
		group = self.roblox_cache["groups"].get(group_id)

		if (group and not group.roles) or not group:

			response = await fetch(self.session, api_url + "groups/" + group_id, raise_on_failure=True)
			response = response[0]

			try:
				response = json.loads(response)

				if response.get("Id"):
					if not group:
						group = Group(id=response["Id"], **response)
					else:
						group.load_json(**response)

					self.roblox_cache["groups"][group_id] = group
					return group

			except json.decoder.JSONDecodeError:
				return {}
		else:
			return group

	async def get_note(self, author=None, roblox_id=None, roblox_user=None):
		notes = []

		if roblox_id:
			# check bloxlink group for rank

			note = await self.r.table("notes").get(roblox_id).run()
			if note:
				note = note.get("note")
				if note:
					notes.append(note)

			if roblox_user:
				user = roblox_user
			else:
				user, _ = await self.get_user(id=roblox_id)
				if user:
					await user.fill_missing_details()

			if user:

				if user.groups.get("3587262"):
					group = user.groups.get("3587262")
					note = group.user_role in ("Mods", "Helpers") and "Bloxlink Staff"

					if note:
						notes.append(note)

		if author:
			is_p, _, _, _ , _ = await is_premium(author=author)
			if is_p:
				notes.append("Bloxlink Donator")

		return notes

	async def auto_cleanup(self):
		while True:
			await asyncio.sleep(600)

			self.roblox_cache = {
				"users": {},
				"author_users": {},
				"groups": {},
				"roblox_ids_to_usernames": {},
				"usernames_to_roblox_ids": {}
			}

	async def clear_user_from_cache(self, author):
		author_id = str(author.id)

		user = self.roblox_cache["author_users"].get(author_id)
		if user:
			self.roblox_cache["author_users"].pop(author_id, None)

			user_ = self.roblox_cache["users"].get(user[0].username.lower())

			if user_:
				self.roblox_cache["users"].pop(user[0].username.lower(), None)

			if user[1]:
				for account in user[1]:
					if self.roblox_cache["users"].get(account.lower()):
						self.roblox_cache["users"].pop(account.lower(), None)

	async def setup(self):
		await self.auto_cleanup()



def new_module():
	return Roblox
