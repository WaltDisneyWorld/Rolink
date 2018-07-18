from resources.modules.utils import is_premium, post_event
from resources.modules.roblox import get_user, get_roles, get_nickname
from discord.errors import Forbidden
from discord.utils import find


async def setup(**kwargs):
	client = kwargs.get("client")
	r = kwargs.get("r")

	@client.event
	async def on_member_join(member):
		guild = member.guild
		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
		roblox_user, _ = await get_user(author=member, guild=member.guild)

		roles_add = []

		if member.bot:
			return

		if roblox_user:
			await roblox_user.fill_missing_details(complete=True)

			if guild_data.get("autoVerification"):
				nickname = await get_nickname(author=member, roblox_user=roblox_user, guild_data=guild_data)
				verified_role_name = guild_data.get("verifiedRoleName", "Verified")
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
		else:
			unverified_role = find(lambda r: r.name == "Unverified", guild.roles)

			if unverified_role:
				roles_add.append(unverified_role)

		if await is_premium(guild=guild):
			if roblox_user:
				if guild_data.get("autoRoles"):
					add_r, _, _ = await get_roles(author=member, guild=guild)
					if add_r:
						roles_add = roles_add + add_r

			if guild_data.get("groupLocked"):
				if not roblox_user:
					await member.kick(reason="GROUP-LOCK: Not linked on Bloxlink")
					return

				group_id = str(guild_data.get("groupID","0"))
				group = roblox_user.groups.get(group_id)

				if not group and group_id != "0":
					print(group_id, type(group_id), flush=True)
					await member.kick(reason=f"GROUP-LOCK: not in linked group {group_id}")
					return

			age_limit = guild_data.get("ageLimit")
			if age_limit:
				if roblox_user:
					print("checking age", flush=True)
					if roblox_user and roblox_user.age < age_limit:
						await member.kick(reason=f"AGE LIMIT: Not old enough: {roblox_user.age} < {age_limit}")
						return
				else:
					await member.kick(reason="AGE LIMIT: user not linked to Bloxlink")
					return


		if roles_add:
			await member.add_roles(*roles_add, reason="Adding roles on member_join")
