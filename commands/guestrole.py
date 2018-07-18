from discord import Embed
from discord.utils import find
from discord.errors import Forbidden
from resources.modules.utils import post_event


async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="guestrole", category="Binds", hidden=True, permissions={
		"raw": "manage_guild"
	}, arguments=[
		{
			"prompt": "What group ID would you like to link this guest role?",
			"type": "number",
			"name": "group"
		},
		{
			"prompt": "What role would you like to be used? A role will be created if it doesn't already exist.",
			"type": "string",
			"name": "role"
		}
	], aliases=["logchannels"])
	async def guestrole(message, response, args, prefix):
		"""binds a role for non-group members"""

		author = message.author
		guild = message.guild

		guild_id = str(guild.id)

		group_id = str(args.parsed_args["group"])
		role_name = args.parsed_args["role"]
		role = find(lambda r: r.name == role_name, guild.roles)

		if not role:
			try:
				role = await guild.create_role(name=role_name, reason="Creating Guest Role")
			except Forbidden:
				await post_event("error", "Failed to create Guest Role. Please ensure " \
					"I have the ``Manage Roles`` permission, and drag my role above " \
					"the other roles.", guild=guild, color=0xE74C3C)
				return


		role_binds = (await r.table("guilds").get(guild_id).run() or {}).get("roleBinds") or {}

		if isinstance(role_binds, list):
			role_binds = role_binds[0]

		role_binds[group_id] = role_binds.get(group_id) or {}
		role_binds[group_id]["0"] = str(role.id)

		await r.table("guilds").insert({
			"id": guild_id,
			"roleBinds": role_binds
		}, conflict="update").run()

		await response.success("Successfully **added** this role as a Guest Role!")



		