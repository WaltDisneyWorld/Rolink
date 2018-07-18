from discord import Embed
from discord.utils import find
from resources.modules.roblox import get_group

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
			embed = Embed(title="Bloxlink Binds", description="You have no binds! Say ``!bind``" \
				" to make a new bind.")
			return await response.send(embed=embed)

		for group_id, bind in role_binds.items():
			binds = []

			for rank, role_id in bind.items():
				rank = ((rank == "0" or rank == "guest") and "Guest Role") or rank
				role = find(lambda r: r.id == int(role_id), guild.roles)
				role_name = role and role.name or "invalid bind (role deleted)"
				binds.append(f"**Rank:** {rank} ➜ **Role:** {role_name}")

			if binds:
				group = await get_group(group_id)

				if group:
					embed.add_field(name=f"{group.name} ({group_id})", value="\n".join(binds), inline=False)

		embed.set_author(name=guild.name, icon_url=guild.icon_url)
		embed.set_footer(text="Use !delbind to delete a bind, or !bind to add a new bind.")

		return await response.send(embed=embed)
