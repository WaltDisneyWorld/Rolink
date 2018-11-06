from resources.module import get_module
get_group = get_module("roblox", attrs=["get_group"])

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="massbind", category="Premium", permissions={
		"raw": "manage_guild"
	}, arguments=[
		{
			"prompt": "Which **group** would you like to create binds for?\n" \
				"Please specify the **group ID.**",
			"type": "number",
			"min": 1,
			"max": 13,
			"name": "group"
		}
	], examples=[
		"massbind 1337"
	])
	async def massbind(message, response, args, prefix):
		"""creates binds & roles to match the group roleset"""

		guild = message.guild

		group_id = str(args.parsed_args["group"])
		guild_id = str(guild.id)

		group = await get_group(group_id)

		role_binds = (await r.table("guilds").get(guild_id).run() or {}).get("roleBinds") or {}
		if isinstance(role_binds, list):
			role_binds = role_binds[0]		
		role_binds[group_id] = role_binds.get(group_id) or {}

		for roleset in group.rolesets:
			rank_num = str(roleset["Rank"])
			rank = role_binds[group_id].get(rank_num, {})
			role = await guild.create_role(name=roleset["Name"])

			if not isinstance(rank, dict):
				rank = {"nickname": None, "roles": [str(rank)]}
				if str(role.id) not in rank["roles"]:
					rank["roles"].append(str(role.id))
			else:
				if not str(role.id) in rank.get("roles", []):
					rank["roles"] = rank.get("roles") or []
					rank["roles"].append(str(role.id))
					rank["nickname"] = None

			role_binds[group_id][rank_num] = rank

		await r.table("guilds").insert({
			"id": guild_id,
			"roleBinds": role_binds
		}, conflict="update").run()

		await response.success("Successfully **bounded** roles for the group rolesets!")





		
