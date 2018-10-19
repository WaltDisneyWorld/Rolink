from resources.module import get_module
is_premium = get_module("utils", attrs=["is_premium"])


async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="devforumbind", category="Binds", permissions={
		"raw": "manage_guild"
	}, arguments=[
		{
			"prompt": "Please specify either the **name or ID** of a **role** in your server " \
				"that you would like to use for this bind. A new role will be created if it doesn't " \
				"already exist.",
			"type": "role",
			"name": "role"
		}
	], examples=[
		"devforumbind",
		"devforumbind developers"
	])
	async def devforumbind(message, response, args, prefix):
		"""binds a role for Developer Forum developers"""

		guild = message.guild

		role = args.parsed_args["role"]

		guild_id = str(guild.id)

		role_binds = (await r.table("guilds").get(guild_id).run() or {}).get("roleBinds") or {}
		virtual_groups = role_binds.get("virtualGroups", {})
		devforum_bind = virtual_groups.get("devForumBind", {})

		roles = devforum_bind.get("roles", [])
		roles.append(str(role.id))

		devforum_bind["roles"] = roles
		virtual_groups["devForumBind"] = devforum_bind
		role_binds["virtualGroups"] = virtual_groups

		await r.table("guilds").insert({
			"id": guild_id,
			"roleBinds": role_binds
		}, conflict="update").run()

		await response.success(f"Successfully **bounded** role **{role}** to this devforum bind.")
