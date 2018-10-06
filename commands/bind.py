from config import TEMPLATES, DONATOR_EMBED

from resources.module import get_module
is_premium = get_module("utils", attrs=["is_premium"])


async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="bind", category="Binds", permissions={
		"raw": "manage_guild"
	}, arguments=[
		{
			"prompt": "Which **group** would you like to apply this bind to?\n" \
				"Please specify the **group ID.**",
			"type": "number",
			"min": 1,
			"max": 13,
			"name": "group"
		},
		{
			"prompt": "Please specify either the **name or ID** of a **role** in your server " \
				"that you would like to use for this bind. A new role will be created if it doesn't " \
				"already exist.",
			"type": "role",
			"name": "role"
		},
		{
			"prompt": "What rank would you like to receive role **{role.name}**? Please specify a **sequence " \
				"of ranks** as such: ``1,2,3,4,5-7``, with each number corresponding to a rank ID or a " \
				"sequence of ranks. Use - to denote a range, example: ``5-7`` means ranks 5, 6, and 7.\n" \
				"You can specify ``all`` to include ``everyone`` in the group, and you can negate the number " \
				"to catch everyone with that rank number _and above._ Example: -10 means everyone with rank " \
				"10 _and above._",
			"type": "string",
			"name": "ranks",
			"min": 1,
			"max": 40
		},
		{
			"prompt": "Would you like these members to receive a custom nickname?\nPlease say ``skip`` to skip this setting; " \
				f"otherwise, specify a nickname using this template: ```{TEMPLATES}```",
			"type": "string",
			"name": "nickname",
			"min": 1,
			"max": 32,
			"ignoreFormatting": True
		}
	], aliases=["newbind", "binds"], examples=[
		"bind",
		"bind 1337 | cool people | 1, 2, 3, 5-8 | skip"
	])
	async def setup_command(message, response, args, prefix):
		"""create a new group bind"""

		guild = message.guild

		group_id = str(args.parsed_args["group"])
		role = args.parsed_args["role"]
		ranks = (args.parsed_args["ranks"].replace(" ", "")).split(",")

		guild_id = str(guild.id)

		new_ranks = []

		if (len(ranks) == 1 and not "-" in ranks[0]) or ranks[0][0] == "-":
			if ranks[0] == "guest" or ranks[0] == "0":
				new_ranks.append("0")
			else:
				new_ranks.append(ranks[0])
		else:
			for x in ranks:
				if x.isdigit():
					new_ranks.append(str(x))
				elif x == "all":
					new_ranks.append("all")
				elif x == "guest" or x == "0":
					new_ranks.append("0")
				elif x[:1] == "-":
					try:
						int(x)
						new_ranks.append(x)
					except ValueError:
						pass
				else:

					x = x.split("-")

					if not len(x) == 2:
						return await response.error("Sequences must contain 2 numbers.")

					x1, x2 = x[0].isdigit() and int(x[0]), x[1].isdigit() and int(x[1])

					if not x1:
						return await response.error("{} is not a number.".format(x[0]))
					elif not x2:
						return await response.error("{} is not a number.".format(x[1]))

					if x2-x1 > 256:
						return await response.error("Too many numbers in range.")

					for y in range(x1, x2+1):
						new_ranks.append(str(y))

		role_binds = (await r.table("guilds").get(guild_id).run() or {}).get("roleBinds") or {}
		profile = await is_premium(guild=guild)

		if isinstance(role_binds, list):
			role_binds = role_binds[0]

		role_binds[group_id] = role_binds.get(group_id) or {}

		for x in new_ranks:
			rank = role_binds[group_id].get(x, {})

			if not isinstance(rank, dict):
				rank = {"nickname": args.parsed_args["nickname"].lower() != "skip" and args.parsed_args["nickname"] or None, "roles": [str(rank)]}
				if str(role.id) not in rank["roles"]:
					rank["roles"].append(str(role.id))
			else:
				if not str(role.id) in rank.get("roles", []):
					rank["roles"] = rank.get("roles") or []
					rank["roles"].append(str(role.id))

					if args.parsed_args["nickname"].lower() != "skip":
						rank["nickname"] = args.parsed_args["nickname"]
					else:
						if not rank.get("nickname"):
							rank["nickname"] = None

			role_binds[group_id][x] = rank

		if len(role_binds) > 15:

			if not profile.is_premium:
				await response.error("No more than 15 bounded groups are allowed. **Bloxlink " \
					"Premium** users can link up to 50 groups.")

				return await response.send(embed=DONATOR_EMBED)

			else:
				if len(role_binds) > 50:
					return await response.error("Sorry! You've reached the **50** group limit. You " \
						"need to delete some to add more.")

		if len(role_binds[group_id]) > 50:

			if not profile.is_premium:
				await response.error("No more than 50 binds are allowed per group. **Bloxlink " \
					"Premium** users can bind up to 255 ranks per group.")
				return await response.send(embed=DONATOR_EMBED)

			else:

				if len(role_binds) > 255:
					return await response.error("Sorry! You've reached the **255** bind limit. You " \
						"need to delete some to add more.")

		await r.table("guilds").insert({
			"id": guild_id,
			"roleBinds": role_binds
		}, conflict="update").run()

		await response.success("Successfully **bounded** rank ID(s): ``{}`` with discord role **{}!**".format(
			", ".join(new_ranks),
			role.name
		))
