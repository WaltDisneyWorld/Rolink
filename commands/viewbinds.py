from discord import Embed
from discord.utils import find

from resources.module import get_module
get_group = get_module("roblox", attrs=["get_group"])

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="viewbinds", category="Binds", permissions={
		"raw": "manage_guild"
	}, aliases=["viewbind"])
	async def viewbinds(message, response, args, prefix):
		"""view group binds"""

		guild = message.guild

		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
		role_binds = guild_data.get("roleBinds") or {}

		embed = Embed(title="Bloxlink Binds")

		if not role_binds:
			embed = Embed(title="Bloxlink Binds", description=f"You have no binds! Say ``{prefix}bind``" \
				" to make a new bind.")
			return await response.send(embed=embed)

		for group_id, bind in dict(role_binds).items():
			binds = []

			for rank, data in bind.items():
				roles = []

				if not isinstance(data, dict):
					data = {"nickname": None, "roles": [str(data)]}

				rank = ((rank == "0" or rank == "guest") and "Guest Role") or rank
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
							role_binds[group_id][rank] = data

							await r.table("guilds").get(str(guild.id)).update({
								"roleBinds": role_binds
							}).run()

				if roles:
					binds.append(f'**Rank:** {rank} ➜ **Role(s):** {", ".join(roles)} ➜ ' \
						f'**Nickname:** {data.get("nickname")}')

			if binds:
				group = await get_group(group_id)

				if group:
					embed.add_field(name=f"{group.name} ({group_id})", value=("\n".join(binds))[0:1023], inline=False)

		embed.set_author(name=guild.name, icon_url=guild.icon_url)
		embed.set_footer(text=f"Use {prefix}delbind to delete a bind, or {prefix}bind to add a new bind.")

		return await response.send(embed=embed)
