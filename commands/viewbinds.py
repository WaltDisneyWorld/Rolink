from discord import Embed
from discord.utils import find

from resources.exceptions import RobloxAPIError

from resources.module import get_module
get_group = get_module("roblox", attrs=["get_group"])

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="viewbinds", category="Binds", permissions={
		"raw": "manage_guild"
	}, aliases=["viewbind"])
	async def viewbinds(message, response, args, prefix):
		"""view group/virtual group binds"""

		guild = message.guild

		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
		role_binds = guild_data.get("roleBinds") or {}

		embed = Embed(title="Bloxlink Binds")

		if not role_binds:
			embed = Embed(title="Bloxlink Binds", description=f"You have no binds! Say ``{prefix}bind``" \
				" to make a new bind.")
			return await response.send(embed=embed)

		virtual_groups = {}

		for group_id, bind in dict(role_binds).items():
			binds = []

			if group_id == "virtualGroups":
				for virtual_group_name, data in bind.items():
					role_ids = data.get("roles", [])
					roles = []

					if role_ids:
						for role_id in role_ids:
							role = find(lambda r: r.id == int(role_id), guild.roles)

							if role:
								roles.append(role.name)
					if roles:
						virtual_groups[virtual_group_name] = roles
					else:
						roles = {}

						if data.get("moreData", {}):
							for bind_id, bind_data in data["moreData"].items():
								roles[bind_id] = []

								for role_id in bind_data.get("roles", []):
									role = find(lambda r: r.id == int(role_id), guild.roles)

									if role:
										roles[bind_id].append(role.name)
						if roles:
							virtual_groups[virtual_group_name] = roles
			else:

				for rank, data in bind.items():
					roles = []

					if not isinstance(data, dict):
						data = {"nickname": None, "roles": [str(data)]}

					rank = ((rank in ("0", 0, "guest")) and "Guest Role") or rank
					role_data = data.get("roles", [])

					for role_id in role_data:
						role = find(lambda r: r.id == int(role_id), guild.roles)

						if role and role.name:
							roles.append(role.name)
						else:
							role_data.remove(role_id)
							if not role_data:
								role_binds.pop(group_id, None)
								guild_data["roleBinds"] = role_binds

								await r.table("guilds").insert({
									**guild_data
								}, conflict="replace").run()
							else:
								data["roles"] = role_data
								role_binds.get(group_id, {})[rank] = data

								await r.table("guilds").get(str(guild.id)).update({
									"roleBinds": role_binds
								}).run()

					if roles:
						binds.append(f'**Rank:** {rank} ➜ **Role(s):** {", ".join(roles)} ➜ ' \
							f'**Nickname:** {data.get("nickname")}')

				if binds:
					if group_id not in ("0", 0, "guest"):
						try:
							group = await get_group(group_id)

							if group:
								embed.add_field(name=f"{group.name} ({group_id})", value=("\n".join(binds)), inline=False)

						except RobloxAPIError:
							embed.add_field(name=f"Invalid Group: {group_id}", value=("\n".join(binds)), inline=False)

		if virtual_groups:
			text_buffer = []

			for virtual_group, data in virtual_groups.items():
				if isinstance(data, dict):
					for bind_id, roles in data.items():
						text_buffer.append(f'**{virtual_group}** ➜ **ID:** {bind_id} ➜ **Role(s):** {", ".join(roles)}')
				else:
					text_buffer.append(f'**{virtual_group}** ➜ **Role(s):** {", ".join(data)}')

			embed.add_field(name="Virtual Groups", value="\n".join(text_buffer))


		embed.set_author(name=guild.name, icon_url=guild.icon_url)
		embed.set_footer(text=f"Use {prefix}delbind to delete a bind, or {prefix}bind to add a new bind.")

		
		await response.send(embed=embed)
