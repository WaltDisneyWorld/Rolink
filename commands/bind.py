async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="bind", category="Administration", permissions={
		"raw": "manage_guild"
	}, arguments=[
		{
			"prompt": "Which group would you like to apply this bind to?\n" \
				"Please specify the group ID.",
			"type": "number",
			"min": 1,
			"max": 13,
			"name": "group"
		},
		{
			"prompt": "Please specify either the name or ID of a role in your server " \
				"that you would like to use for this bind.",
			"type": "role",
			"name": "role"
		},
		{
			"prompt": "What rank would you like to receive role **{role.name}**? Please specify a sequence " \
				"of ranks as such: ``1,2,3,4,5-7``, with each number corresponding to a rank ID or a " \
				"sequence of ranks. Use - to denote a range, example: ``5-7`` means ranks 5, 6, and 7.\n" \
				"You can specify ``all`` to include ``everyone`` in the group, and you can negate the number " \
				"to catch everyone with that rank number _and above._ Example: -10 means everyone with rank " \
				"10 _and above._",
			"type": "string",
			"name": "ranks",
			"min": 1,
			"max": 20
		}
	])
	async def setup_command(message, response, args):
		"""creates a new server bind"""

		group_id = str(args.parsed_args["group"])
		role = args.parsed_args["role"]
		ranks = (args.parsed_args["ranks"].replace(" ", "")).split(",")

		guild_id = str(message.guild.id)

		new_ranks = []

		for x in ranks:
			if x.isdigit():
				print("1", flush=True)
				new_ranks.append(str(x))
				continue
			elif x == "all":
				print("2", flush=True)
				new_ranks.append("all")
				continue
			elif x[:1] == "-":
				print(x, flush=True)
				try:
					int(x)
					new_ranks.append(x)
					print("4", flush=True)
				except ValueError:
					pass
				continue

			x = x.split("-")

			if not len(x) == 2:
				return await response.error("**Bind error:** sequences must contain 2 numbers.")

			x1, x2 = x[0].isdigit() and int(x[0]), x[1].isdigit() and int(x[1])

			if not x1:
				return await response.error("**Bind error:** {} is not a number.".format(x[0]))
			elif not x2:
				return await response.error("**Bind error:** {} is not a number.".format(x[1]))

			if x2-x1 > 10:
				return await response.error("**Bind error:** too many numbers in range.")

			for y in range(x1, x2+1):
				new_ranks.append(str(y))

		role_binds = (await r.table("guilds").get(guild_id).run() or {}).get("roleBinds") or {}

		role_binds[group_id] = role_binds.get(group_id) or {}

		for x in new_ranks:
			role_binds[group_id][x] = str(role.id)

		if len(role_binds) > 10:
			return await response.error("**Bind error:** No more than 10 bounded groups are allowed.")
		elif len(role_binds[group_id]) > 30:
			return await response.error("**Bind error:** Too many binds for group **{}**.".format(
				group_id
			))

		await r.table("guilds").insert({
			"id": guild_id,
			"roleBinds": role_binds
		}, conflict="update").run()

		await response.success("Successfully bounded rank ID(s): ``{}`` with discord role **{}!**".format(
			", ".join(new_ranks),
			role.name

		))
