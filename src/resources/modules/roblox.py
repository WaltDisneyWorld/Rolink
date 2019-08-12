from ..structures.Bloxlink import Bloxlink
from ..exceptions import BadUsage, RobloxAPIError, CancelledPrompt, Message, CancelCommand
from typing import Tuple
from discord.errors import Forbidden, NotFound
from discord.utils import find
from discord import Embed, Member
from bs4 import BeautifulSoup
from datetime import datetime
from config import WORDS, RELEASE # pylint: disable=no-name-in-module
import json
import random
import asyncio


loop = asyncio.get_event_loop()

fetch = Bloxlink.get_module("utils", attrs="fetch")

API_URL = "https://api.roblox.com"
BASE_URL = "https://roblox.com"

@Bloxlink.module
class Roblox(Bloxlink.Module):
	cache = {"usernames_to_ids": {}, "roblox_users": {}, "discord_profiles": {}, "groups": {}}

	def __init__(self, _):
		pass

	@staticmethod
	async def get_roblox_id(username) -> Tuple[str, str]:
		username_lower = username.lower()
		roblox_cached_data = Roblox.cache["usernames_to_ids"].get(username_lower)

		if roblox_cached_data:
			return roblox_cached_data

		try:
			_, response = await fetch(f"{API_URL}/users/get-by-username/?username={username}", raise_on_failure=True)
		except RobloxAPIError:
			return None
		else:
			json_data = await response.json()
			correct_username, roblox_id = json_data.get("Username"), str(json_data.get("Id"))

			data = (roblox_id, correct_username)

			if correct_username:
				Roblox.cache["usernames_to_ids"][username_lower] = data

			return data

	@staticmethod
	async def get_roblox_username(roblox_id) -> Tuple[str, str]:
		roblox_user = Roblox.cache["roblox_users"].get(roblox_id)

		if roblox_user and roblox_user.verified:
			return roblox_user.id, roblox_user.username

		try:
			_, response = await fetch(f"{API_URL}/users/{roblox_id}", raise_on_failure=True)
		except RobloxAPIError:
			return None
		else:
			json_data = await response.json()
			correct_username, roblox_id = json_data.get("Username"), str(json_data.get("Id"))

			data = (roblox_id, correct_username)

			return data

	@staticmethod
	def generate_code():
		words = []

		for _ in range(4):
			x = random.randint(1, 2)

			words.append(f"{random.choice(WORDS)} {x == 1 and 'and' or 'or'}")

		words.append(random.choice(WORDS))

		return " oof ".join(words)


	@staticmethod
	async def validate_code(roblox_id, code):
		if RELEASE == "LOCAL":
			return True

		html_text, _ = await fetch(f"https://www.roblox.com/users/{roblox_id}/profile", raise_on_failure=True)

		return code in html_text

	async def verify_member(self, author, roblox, guild=None, author_data=None, primary_account=False):
		# TODO: make this insert a new DiscordProfile or append the account to it
		author_id = str(author.id)
		guild = guild or getattr(author, "guild", None)

		if isinstance(roblox, RobloxUser):
			roblox_id = str(roblox.id)
		else:
			roblox_id = str(roblox)

		author_data = author_data or await self.r.table("users").get(author_id).run() or {}
		roblox_accounts = author_data.get("robloxAccounts", {})
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
				"robloxID": primary_account and roblox_id or author_data.get("robloxID"),
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


	"""
	async def get_roles(self, author, roblox_user=None, *, guild=None, complete=True):
		if find(lambda r: r.name == "Bloxlink Bypass", author.roles):
			return [], [], [], []

		remove_roles = []
		add_roles = []

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
						if group_id_ == "virtualGroups":
							for virtual_group_name, data_ in data.items():
								virtual_group_resolver = get_virtual_group(virtual_group_name)

								if virtual_group_resolver:
									if isinstance(data_.get("moreData"), dict):
										for bind_id, bind_data in data_["moreData"].items():
											result = await virtual_group_resolver(author, roblox_user=user, bind_data=(bind_id, bind_data))

											if result:
												for role_id in bind_data.get("roles", []):
													role = find(lambda r: int(float(r.id)) == int(float(role_id)), guild.roles)

													if role:
														possible_roles.append(role)

														if not role in author.roles:
															add_roles.append(role)
											else:
												if not role in (*add_roles, *remove_roles, *possible_roles):
													if role in author.roles:
														remove_roles.append(role)

									else:

										result = await virtual_group_resolver(author, roblox_user=user, bind_data=data_)

										if result:
											for role_id in data_.get("roles", []):
												role = find(lambda r: int(float(r.id)) == int(float(role_id)), guild.roles)

												if role:
													possible_roles.append(role)

													if not role in author.roles:
														add_roles.append(role)
										else:
											if not role in (*add_roles, *remove_roles, *possible_roles):
												if role in author.roles:
													remove_roles.append(role)

						else:
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

		return add_roles, remove_roles, possible_nicknames
	"""
	pass

	"""
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
	"""


	async def update_member(self, author, *, nickname=True, roles=True, guild=None, roblox_user=None, author_data=None, guild_data=None):
		guild = guild or getattr(author, "guild", None)
		guild_id = guild and str(guild.id)

		added, removed = [], []

		if guild:
			if not isinstance(author, Member):
				author = await guild.fetch_member(author.id)

				if not author:
					raise CancelCommand

		if find(lambda r: r.name == "Bloxlink Bypass", author.roles):
			return added, removed

		if not roblox_user:
			roblox_user, _ = await self.get_user(author=author, guild=guild, author_data=author_data)

		if not (roblox_user or roblox_user.verified):
			# TODO: give unverified role
			return










	async def get_group(self, group_id):
		group_id = str(group_id)
		group = self.cache["groups"].get(group_id)

		if group and group.roles:
			return group

		text, _ = await fetch(f"{API_URL}/groups/{group_id}", raise_on_failure=False)

		try:
			json_data = json.loads(text)
		except json.decoder.JSONDecodeError:
			raise RobloxAPIError
		else:
			if json_data.get("Id"):
				if not group:
					group = Group(id=group_id, **json_data)
				else:
					group.load_json(json_data)

				self.cache["groups"][group_id] = group

				return group

	async def get_user(self, *args, author=None, guild=None, username=None, roblox_id=None, author_data=None, everything=False, basic_details=True, send_embed=False, response=None):
		guild = guild or getattr(author, "guild", False)
		guild_id = guild and str(guild.id)

		roblox_account = accounts = None
		embed = None

		if send_embed:
			if not response:
				raise BadUsage("Must supply response object for embed sending")

			embed = [Embed(title="Loading..."), response]


		if author:
			author_id = str(author.id)
			author_data = author_data or await self.r.table("users").get(author_id).run() or {}

			discord_profile = self.cache["discord_profiles"].get(author_id)

			if discord_profile:
				if guild:
					roblox_account = discord_profile.guilds.get(guild_id)
				else:
					roblox_account = discord_profile.primary_account

				if roblox_account:
					await roblox_account.sync(*args, author=author, embed=embed, everything=everything)
					return roblox_account, discord_profile.accounts

				return None, discord_profile.accounts

			author_data = author_data or await self.r.table("users").get(author_id).run() or {}
			roblox_accounts = author_data.get("robloxAccounts", {})
			accounts = roblox_accounts.get("accounts", [])
			guilds = roblox_accounts.get("guilds", {})

			roblox_account = guild and guilds.get(guild_id) or author_data.get("robloxID")

			if roblox_account:
				discord_profile = DiscordProfile(author_id)
				roblox_user = self.cache["roblox_users"].get(roblox_account)

				if not roblox_user:
					roblox_user = self.cache["roblox_users"].get(roblox_account) or RobloxUser(roblox_id=roblox_account, author_id=author_id)
					await roblox_user.sync(*args, author=author, embed=embed, everything=everything, basic_details=basic_details)

					if roblox_user.verified:
						self.cache["roblox_users"][roblox_account] = roblox_user
					else:
						return None, accounts

				if not roblox_user.verified:
					return None, accounts

				if guild:
					discord_profile.guilds[guild_id] = roblox_user
				else:
					discord_profile.primary_account = roblox_user

				self.cache["discord_profiles"][author_id] = discord_profile

				return roblox_user, accounts

			return None, accounts

		if username:
			if not roblox_id:
				roblox_id, username = await self.get_roblox_id(username)

		if not roblox_id:
			raise BadUsage("No roblox ID specified.")

		roblox_user = RobloxUser(username=username, roblox_id=roblox_id)
		await roblox_user.sync(*args, embed=embed, everything=everything, basic_details=basic_details)

		if roblox_user.verified:
			self.cache["roblox_users"][roblox_id] = roblox_user
			return roblox_user, None

		return None, None


	"""
	async def get_user(self, author=None, guild=None, *, username=None, roblox_id=None, author_data=None):
		guild = guild or getattr(author, "guild", False)
		guild_id = guild and str(guild.id)

		if author:
			author_id = str(author.id)
			#author_data = author_data or await self.r.table("users").get(author_id).run() or {}

			discord_profile = self.cache["discord_profiles"].get(author_id)

			if discord_profile:
				return discord_profile

			author_data = author_data or await self.r.table("users").get(author_id).run() or {}
			roblox_accounts = author_data.get("robloxAccounts", {})
			accounts = roblox_accounts.get("accounts", [])
			guilds = roblox_accounts.get("guilds", {})

			if username or roblox_id:
				if roblox_id:
					roblox_id = str(roblox_id) # possibly don't need to cast it to a string

				if not username:
					user_info = self.cache["roblox_ids_to_usernames"].get(id) # (roblox_id, correct_username)

					if username:
						roblox_user = self.cache["roblox_users"].get(user_info[1].lower())

						#if roblox_user:
						#	self.roblox_cache["author_users"][author_id] = (roblox_user, accounts)

						if roblox_user:
							return roblox_user, accounts # TODO: look into returning a RobloxUser with discord_id as main initialization and fields for primary acc and sub-accounts

				roblox_user = RobloxUser(id=id, username=username)
				await roblox_user.sync()

				if roblox_user.verified:
					self.cache["roblox_users"][roblox_user.username.lower()] = roblox_user
					#self.cache["author_users"][author_id] = (roblox_user, accounts)

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
	"""

	"""
	async def add_roles(self, author, roblox_user=None, *, guild=None, complete=True):
		if find(lambda r: r.name == "Bloxlink Bypass", author.roles):
			return [], [], []

		remove_roles = []
		add_roles = []

		possible_roles = []
		possible_nicknames = []

		roblox_user = roblox_user or await self.get_user(author, guild)

		if roblox_user:
			if not roblox_user.verified:
				await roblox_user.sync()

			user_groups = roblox_user.groups

			if roblox_user.incomplete:
				raise RobloxAPIError



		else:
			# TODO: give unverified role
			pass
	"""



	async def verify_as(self, author, guild=None, *, author_data=None, primary=False, response=None, username:str=None, roblox_id:str=None) -> bool:
		if not (username or roblox_id):
			raise BadUsage("Must supply either a username or roblox_id to verify_as.")

		guild = guild or author.guild
		author_data = author_data or await self.r.table("users").get(str(author.id)).run() or {}

		if not roblox_id:
			roblox_id, username = await self.get_roblox_id(username)

		if roblox_id:
			if roblox_id in author_data.get("robloxAccounts", {}).get("accounts", []) or author_data.get("robloxID") == roblox_id:
				# verify as the person, call self.get_roles(author, guild=guild, author_data=author_data)
				return True
			else:
				# prompts
				if response:
					messages = []

					try:
						args, messages1 = await response.prompt([
							{
								"prompt": f"Welcome, **{username}!** Please select a method of verification: ``code`` or ``game``",
								"type": "choice",
								"choices": ["code", "game"],
								"name": "verification_choice"
							}
						], return_messages=True)


						messages += messages1

						if args["verification_choice"] == "code":
							code = self.generate_code()

							msg1 = await response.send(f"To confirm that you own this Roblox account, please put this code in your description or status:")
							msg2 = await response.send(f"```{code}```")

							if msg1:
								messages.append(msg1)
							if msg2:
								messages.append(msg2)

							_, msg3 = await response.prompt([{
								"prompt": "Then, say ``done`` to continue.",
								"name": "verification_next",
								"type": "choice",
								"choices": ["done"]
							}], embed=False, return_messages=True)

							if msg3:
								messages += msg3

							if await self.validate_code(roblox_id, code):
								# user is now validated; add their roles
								await self.verify_member(author, roblox_id, guild=guild, author_data=author_data, primary_account=primary)
								return True

							failures = 0
							failed = False

							while not await self.validate_code(roblox_id, code):
								if failures == 5:
									failed = True
									break

								failures += 1

								_, messages2 = await response.prompt([
									{
										"prompt": "Unable to find the code on your profile. Please say ``done`` to search again or ``cancel`` to cancel.",
										"type": "choice",
										"choices": ["done"],
										"name": "retry"
									}
								], error=True, return_messages=True)

								messages += messages2

								attempt = await self.validate_code(roblox_id, code)

								if attempt:
									await self.verify_member(author, roblox_id, author_data=author_data, guild=guild, primary_account=primary)
									return True

							if failed:
								raise Message(f"{author.mention}, too many failed attempts. Please run this command again and retry.", type="error")

						elif args["verification_choice"] == "game":
							raise NotImplementedError

					# except CancelledPrompt:
					#	pass


					finally:
						if messages:
							for message in messages:
								try:
									await message.delete()
								except (Forbidden, NotFound):
									pass













	async def get_user_groups(self, roblox_id):
		# TODO
		pass




class DiscordProfile:
	__slots__ = "id", "primary_account", "accounts", "guilds"

	def __init__(self, author_id, **kwargs):
		self.id = author_id

		self.primary_account = kwargs.get("primary_account")
		self.accounts = kwargs.get("accounts", [])
		self.guilds = kwargs.get("guilds", {})

	def __eq__(self, other):
		return self.id == getattr(other, "id", None)

class Group(Bloxlink.Module):
	__slots__ = ("name", "description", "roles", "owner", "member_count",
				 "embed_url", "url", "user_rank", "user_role")

	def __init__(self, group_id=None, **kwargs):
		self.group_id = str(group_id)
		self.name = None
		self.description = None
		self.roles = None
		self.owner = None
		self.member_count = None
		self.embed_url = None
		self.url = self.group_id and f"https://www.roblox.com/My/Groups.aspx?gid={self.group_id}"

		self.user_rank = None
		self.user_role = None

		self.load_json(kwargs)

	def load_json(self, json_data):
		self.group_id = self.group_id or str(json_data["Id"])
		self.name = self.name or json_data.get("Name")
		self.description = self.description or json_data.get("Description") or json_data.get("description", "N/A")
		self.roles = self.rolesets = self.roles or json_data.get("Roles")
		self.owner = self.owner or json_data.get("Owner") or json_data.get("owner")
		self.member_count = self.member_count or json_data.get("memberCount")
		self.embed_url = self.embed_url or json_data.get("EmblemUrl")
		self.url = self.url or (self.group_id and f"https://www.roblox.com/My/Groups.aspx?gid={self.group_id}")

		self.user_rank = self.user_rank or (json_data.get("Rank") and str(json_data.get("Rank")).strip())
		self.user_role = self.user_role or (json_data.get("Role") and str(json_data.get("Role")).strip())

class RobloxUser(Bloxlink.Module):
	__slots__ = ("username", "id", "discord_id", "verified", "complete", "more_details", "groups",
				 "avatar", "membership", "presence", "badges", "description", "banned", "age",
				 "join_date", "profile_link", "session", "embed")

	def __init__(self, *, username=None, roblox_id=None, discord_id=None, **kwargs):
		self.username = username
		self.id = roblox_id
		self.discord_id = discord_id

		self.verified = False
		self.complete = False
		self.more_details = False
		self.partial = False

		self.groups = kwargs.get("groups", {})
		self.avatar = kwargs.get("avatar")
		self.membership = kwargs.get("membership")
		self.presence = kwargs.get("presence")
		self.badges = kwargs.get("badges", [])
		self.description = kwargs.get("description", "")
		self.banned = kwargs.get("banned", False)

		self.embed = None

		self.age = 0
		self.join_date = None
		self.profile_link = roblox_id and f"https://www.roblox.com/users/{roblox_id}/profile"
	"""
				*args,
				username = self.username,
				roblox_id = self.id,
				everything=everything,
				roblox_user=self
	"""
	@staticmethod
	async def get_details(*args, author=None, username=None, roblox_id=None, everything=False, basic_details=False, roblox_user=None, embed=None):
		if everything:
			basic_details = True

		roblox_data = {
			"username": username,
			"id": roblox_id,
			"groups": {},
			"presence": None,
			"membership": None,
			"badges": [],
			"avatar": None,
			"profile_link": roblox_id and f"https://www.roblox.com/users/{roblox_id}/profile",
			"extras": {
				"description": "",
				"age": 0,
				"join_date": None,
				"banned": False
			}
		}


		roblox_user_from_cache = None

		if username:
			cache_find = Roblox.cache["usernames_to_ids"].get(username)

			if cache_find:
				roblox_id, username = cache_find

			if roblox_id:
				roblox_user_from_cache = Roblox.cache["roblox_users"].get(roblox_id)

		if roblox_user_from_cache and roblox_user_from_cache.verified:
			roblox_data["id"] = roblox_id or roblox_user_from_cache.id
			roblox_data["username"] = username or roblox_user_from_cache.username
			roblox_data["groups"] = roblox_user_from_cache.groups
			roblox_data["avatar"] = roblox_user_from_cache.avatar
			roblox_data["membership"] = roblox_user_from_cache.membership
			roblox_data["presence"] = roblox_user_from_cache.presence
			roblox_data["badges"] = roblox_user_from_cache.badges
			roblox_data["extras"]["description"] = roblox_user_from_cache.description
			roblox_data["extras"]["age"] = roblox_user_from_cache.age
			roblox_data["extras"]["join_date"] = roblox_user_from_cache.join_date
			roblox_data["extras"]["banned"] = roblox_user_from_cache.banned

		if roblox_id and not username:
			roblox_id, username = await Roblox.get_roblox_username(roblox_id)
			roblox_data["username"] = username
			roblox_data["id"] = roblox_id
		elif not roblox_id and username:
			roblox_id, username = await Roblox.get_roblox_id(username)
			roblox_data["username"] = username
			roblox_data["id"] = roblox_id

		if not (username and roblox_id):
			return None

		if embed:
			sent_embed = await embed[1].send(embed=embed[0])

			if not sent_embed:
				embed = None
			else:
				embed.append(sent_embed)

				if basic_details or "username" in args:
					embed[0].add_field(name="Username", value=username)

				if basic_details or "id" in args:
					embed[0].add_field(name="ID", value=roblox_id)


		if roblox_user:
			roblox_user.username = username
			roblox_user.id = roblox_id


		async def avatar():
			if roblox_data.get("avatar"):
				avatar_url = roblox_data["avatar"]
			else:
				avatar_url, _ = await fetch(f"{BASE_URL}/bust-thumbnail/json?userId={roblox_data['id']}&height=180&width=180")

				try:
					avatar_url = json.loads(avatar_url)
				except json.decoder.JSONDecodeError:
					raise RobloxAPIError
				else:
					avatar_url = avatar_url.get("Url")

					if roblox_user:
						roblox_user.avatar = avatar_url

					roblox_data["avatar"] = avatar_url

			if embed:
				embed[0].set_thumbnail(url=avatar_url)
				embed[0].set_author(name=author and str(author) or roblox_data["username"], icon_url=author and author.avatar_url, url=roblox_data.get("profile_link")) # unsure what this does with icon_url if there's no author

		async def presence():
			if roblox_data.get("presence"):
				presence = roblox_data["presence"]
			else:
				presence, _ = await fetch(f"{BASE_URL}/presence/user?userId={roblox_data['id']}")

				try:
					presence = json.loads(presence)
				except json.decoder.JSONDecodeError:
					raise RobloxAPIError
				else:
					presence_type = presence.get("UserPresenceType")

					if presence_type is 0:
						presence = "offline"
					elif presence_type is 1:
						presence = "browsing the website"
					elif presence_type is 2:
						if presence.get("PlaceID") is not None:
							presence = f"playing [{presence.get('LastLocation')}](https://www.roblox.com/games/{presence.get('PlaceId')}/-"
						else:
							presence = "in game"
					elif presence_type is 3:
						presence = "creating"

				if roblox_user:
					roblox_user.presence = presence

				roblox_data["presence"] = presence

			if embed:
				embed[0].add_field(name="Presence", value=presence)

		async def membership_and_badges():
			badges = roblox_data["badges"]

			if roblox_data["membership"]:
				membership = roblox_data["membership"]
			else:
				data, _ = await fetch(f"{BASE_URL}/badges/roblox?userId={roblox_data['id']}")

				membership = None

				try:
					data = json.loads(data)
				except json.decoder.JSONDecodeError:
					raise RobloxAPIError

				for badge in data.get("RobloxBadges", []):
					if badge["Name"] == "Outrageous Builders Club":
						membership = "OBC"
					elif badge["Name"] == "Turbo Builders Club":
						membership = "TBC"
					elif badge["Name"] == "Builders Club":
						membership = "BC"
					else:
						membership = "NBC"
						badges.append(badge["Name"])

				#roblox_data["badges"] = badges
				roblox_data["membership"] = membership

				if roblox_user:
					roblox_user.badges = badges
					roblox_user.membership = membership

			if embed:
				if membership != "NBC":
					embed[0].add_field(name="Membership", value=membership)

				embed[0].add_field(name="Badges", value=", ".join(badges))

		async def groups():
			groups = roblox_data["groups"]

			if roblox_data.get("groups"):
				groups = roblox_data["groups"]
			else:
				group_json, _ = await fetch(f"{API_URL}/users/{roblox_data['id']}/groups")

				try:
					group_json = json.loads(group_json)
				except json.decoder.JSONDecodeError:
					raise RobloxAPIError
				else:
					for group_data in group_json:
						group_id = str(group_data["Id"])
						groups[group_id] = Group(group_id, **group_data)

					if roblox_user:
						roblox_user.groups = groups

			if embed:
				embed[0].add_field(name="Groups", value=(", ".join(x.name for x in groups.values()))[:1000])


		async def profile():
			if roblox_data["extras"].get("description") or roblox_data["extras"].get("age"):
				description = roblox_data["extras"].get("description")
				age = roblox_data["extras"].get("age")
				join_date = roblox_data["extras"].get("join_date")
				banned = roblox_data["extras"].get("banned")
			else:
				banned = description = age = join_date = None

				try:
					data, _ = await fetch(f"{BASE_URL}/users/{roblox_data['id']}/profile")
					soup = BeautifulSoup(data, "html.parser")

					for text in soup.body.find_all("p", attrs={"class":"text-lead"}):
						text = text.text

						if "/" in text:
							text = text[:text.index("Place")]
							roblox_data["extras"]["join_date"] = text
							join_date = text

							today = datetime.today()
							datetime_object = datetime.strptime(text, '%m/%d/%Y')

							age = (today - datetime_object).days
							roblox_data["extras"]["age"] = age

							# break

						desc = soup.body.find('div', attrs={'class':'profile-about-content'})
						description = desc and desc.text.strip("Read More")
						roblox_data["extras"]["description"] = description

						if desc is None:
							roblox_data["extras"]["banned"] = True
							banned = True

					if roblox_user:
						roblox_user.banned = banned
						roblox_user.description = description
						roblox_user.age = age
						roblox_user.join_date = join_date

				except RobloxAPIError:
					roblox_data["extras"]["banned"] = True
					banned = True


			if embed:
				if banned:
					pass # TODO: set description to say account is banned

				embed[0].add_field(name="Join Date", value=join_date)
				embed[0].add_field(name="Account Age", value=f"{age} days old")

				embed[0].add_field(name="Description", value=description[:1000].strip("\n"))

				embed[0].title = None

				await embed[2].edit(embed=embed[0])

		# fast operations
		if basic_details or "avatar" in args:
			await avatar()

		if basic_details or "presence" in args:
			await presence()

		if basic_details or "membership" in args or "badges" in args:
			await membership_and_badges()

		if basic_details or "groups" in args:
			await groups()

		if not everything:
			embed[0].title = None

		if embed:
			if embed[0] != embed:
				await embed[2].edit(embed=embed[0])

		# slow operations
		if everything or "description" in args or "blurb" in args or "age" in args or "banned" in args:
			await profile()

		return roblox_data

	async def sync(self, *args, author=None, basic_details=False, embed=None, everything=False):
		try:
			await self.get_details(
				*args,
				username = self.username,
				roblox_id = self.id,
				everything = everything,
				basic_details = basic_details,
				embed = embed,
				roblox_user = self,
				author=author
			)

			#if not self.groups:
			#	self.set_groups(await self.get_groups(roblox_id=self.id))

		except RobloxAPIError:
			self.complete = False

			if self.discord_id and self.id:
				# TODO: set username from database
				self.partial = True # only set if there is a db entry for the user with the username
			else:
				raise RobloxAPIError
		else:
			self.complete = True
			self.verified = True
			self.partial = False
			self.profile_link = self.profile_link or f"https://www.roblox.com/users/{self.id}/profile"


	"""
	def set_groups(self, groups):
		self.groups = groups

	def add_group(self, group):
		if not self.groups.get(group.name):
			self.groups[group.name] = group
	"""

	def __eq__(self, other):
		return self.id == getattr(other, "id", None) or self.username == getattr(other, "username", None)

	def __str__(self):
		return self.id


