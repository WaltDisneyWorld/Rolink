from config import release
from discord.errors import Forbidden, NotFound
from discord.utils import find
from resources.exceptions import RobloxAPIError, PermissionError
from aiohttp.client_exceptions import ClientOSError

from resources.module import get_module
get_user, get_roles, get_nickname = get_module("roblox", attrs=["get_user", "get_roles", "get_nickname"])
is_premium, post_event = get_module("utils", attrs=["is_premium", "post_event"])


class OnMemberJoin:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")
		self.r = kwargs.get("r")

	async def setup(self):
		@self.client.event
		async def on_member_join(member):
			try:
				guild = member.guild
				guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {}
				roblox_user, _ = await get_user(author=member, guild=member.guild)

				roles_add = []

				if member.bot:
					return

				if roblox_user:
					await roblox_user.fill_missing_details(complete=True)

					if guild_data.get("joinDM", True):
						if release == "MAIN" or (release == "PRO" and not guild.get_member(426537812993638400)):

							join_message = guild_data.get("welcomeMessage",
								"Welcome to {server-name}, **{roblox-name}!**")

							resolved_message = await get_nickname(author=member, roblox_user=roblox_user,
								guild_data=guild_data, template=join_message, ignore_trim=True)

							if resolved_message:
								try:
									await member.send(resolved_message)
								except Forbidden:
									pass

					if guild_data.get("autoVerification"):
						nickname = await get_nickname(author=member, roblox_user=roblox_user, guild_data=guild_data)
						verified_role_name = guild_data.get("verifiedRoleName", "Verified")[0:99]
						verified_role = find(
							lambda r: r.name == verified_role_name,
							guild.roles
						) or await guild.create_role(name=verified_role_name, reason="Missing Verified Role")
						unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

						if verified_role:
							roles_add.append(verified_role)

						if nickname:
							try:
								await member.edit(nick=nickname)
							except Forbidden:
								await post_event(
									"error",
									f"Failed to update {member.mention}'s nickname. Please ensure I have " \
										"the ``Manage Nickname`` permission, and drag my role above the other roles.",
									guild=guild,
									color=0xE74C3C
								)

					if guild_data.get("autoRoles"):
						add_r, _, possible_nicknames, _ = await get_roles(author=member, roblox_user=roblox_user, guild=guild)
						if add_r:
							roles_add = roles_add + add_r

						possible_nickname = None
						
						if len(possible_nicknames) == 1:
							possible_nickname = possible_nicknames[0][1]
						else:
							highest_role = sorted(possible_nicknames, key=lambda e: e[0].position, reverse=True)
							if highest_role:
								possible_nickname = highest_role[0][1]
						
						if possible_nickname:
							try:
								await member.edit(nick=possible_nickname)
							except Forbidden:
								await post_event(
									"error",
									f"Failed to update {member.mention}'s nickname. Please ensure I have " \
										"the ``Manage Nickname`` permission, and drag my role above the other roles.",
									guild=guild,
									color=0xE74C3C
								)

				else:
					unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

					if unverified_role:
						roles_add.append(unverified_role)

				is_p, _, _, _, _ = await is_premium(guild=guild)

				if is_p:

					if guild_data.get("groupLocked"):
						if not roblox_user:
							await member.kick(reason="GROUP-LOCK: Not linked on Bloxlink")
							return

						group_id = str(guild_data.get("groupID","0"))
						group = roblox_user.groups.get(group_id)

						if not group and group_id != "0":
							await member.kick(reason=f"GROUP-LOCK: not in linked group {group_id}")
							return

					age_limit = guild_data.get("ageLimit")
					if age_limit:

						if roblox_user:
							if roblox_user.age < age_limit:
								await member.kick(reason=f"AGE LIMIT: Not old enough: {roblox_user.age} < {age_limit}")
								return
						else:
							await member.kick(reason="AGE LIMIT: user not linked to Bloxlink")
							return

				if roles_add:
					await member.add_roles(*roles_add, reason="Adding roles on member join")

			except (Forbidden, NotFound, ClientOSError):
				pass
			except RobloxAPIError:
				# client.dispatch("on_member_join", a, b, c)
				# await queue
				pass
			except PermissionError: # pretty redundant, but w/e
				pass


"""
async def setup(**kwargs):
	client = kwargs.get("client")
	r = kwargs.get("r")

	@client.event
	async def on_member_join(member):
		try:
			guild = member.guild
			guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
			roblox_user, _ = await get_user(author=member, guild=member.guild)

			roles_add = []

			if member.bot:
				return

			if roblox_user:
				await roblox_user.fill_missing_details(complete=True)

				if guild_data.get("joinDM", True):
					if release == "MAIN" or (release == "PRO" and not guild.get_member(426537812993638400)):

						join_message = guild_data.get("welcomeMessage",
							"Welcome to {server-name}, **{roblox-name}!**")

						resolved_message = await get_nickname(author=member, roblox_user=roblox_user,
							guild_data=guild_data, template=join_message, ignore_trim=True)

						if resolved_message:
							try:
								await member.send(resolved_message)
							except Forbidden:
								pass

				if guild_data.get("autoVerification"):
					nickname = await get_nickname(author=member, roblox_user=roblox_user, guild_data=guild_data)
					verified_role_name = guild_data.get("verifiedRoleName", "Verified")[0:99]
					verified_role = find(
						lambda r: r.name == verified_role_name,
						guild.roles
					) or await guild.create_role(name=verified_role_name, reason="Missing Verified Role")
					unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

					if verified_role:
						roles_add.append(verified_role)

					if nickname:
						try:
							await member.edit(nick=nickname)
						except Forbidden:
							await post_event(
								"error",
								f"Failed to update {member.mention}'s nickname. Please ensure I have " \
									"the ``Manage Nickname`` permission, and drag my role above the other roles.",
								guild=guild,
								color=0xE74C3C
							)

				if guild_data.get("autoRoles"):
					add_r, _, possible_nicknames, _ = await get_roles(author=member, roblox_user=roblox_user, guild=guild)
					if add_r:
						roles_add = roles_add + add_r

					possible_nickname = None
					
					if len(possible_nicknames) == 1:
						possible_nickname = possible_nicknames[0][1]
					else:
						highest_role = sorted(possible_nicknames, key=lambda e: e[0].position, reverse=True)
						if highest_role:
							possible_nickname = highest_role[0][1]
					
					if possible_nickname:
						try:
							await member.edit(nick=possible_nickname)
						except Forbidden:
							await post_event(
								"error",
								f"Failed to update {member.mention}'s nickname. Please ensure I have " \
									"the ``Manage Nickname`` permission, and drag my role above the other roles.",
								guild=guild,
								color=0xE74C3C
							)

			else:
				unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

				if unverified_role:
					roles_add.append(unverified_role)

			is_p, _, _, _, _ = await is_premium(guild=guild)

			if is_p:

				if guild_data.get("groupLocked"):
					if not roblox_user:
						await member.kick(reason="GROUP-LOCK: Not linked on Bloxlink")
						return

					group_id = str(guild_data.get("groupID","0"))
					group = roblox_user.groups.get(group_id)

					if not group and group_id != "0":
						await member.kick(reason=f"GROUP-LOCK: not in linked group {group_id}")
						return

				age_limit = guild_data.get("ageLimit")
				if age_limit:

					if roblox_user:
						if roblox_user.age < age_limit:
							await member.kick(reason=f"AGE LIMIT: Not old enough: {roblox_user.age} < {age_limit}")
							return
					else:
						await member.kick(reason="AGE LIMIT: user not linked to Bloxlink")
						return

			if roles_add:
				await member.add_roles(*roles_add, reason="Adding roles on member join")

		except (Forbidden, NotFound, ClientOSError):
			pass
		except RobloxAPIError:
			# client.dispatch("on_member_join", a, b, c)
			# await queue
			pass
		except PermissionError: # pretty redundant, but w/e
			pass
"""

def new_module():
	return OnMemberJoin