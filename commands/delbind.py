from discord import Embed
from discord.utils import find

from resources.module import get_module
get_group = get_module("roblox", attrs=["get_group"])

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="delbind", category="Binds", permissions={
		"raw": "manage_guild"
	}, aliases=["delbinds", "deletebind", "deletebinds"], arguments=[
		{
			"prompt": "Please specify the group ID that this bind resides in. If this is not a group, " \
			"specify the bind type (e.g. \"assetBind\").",
			"type": "string",
			"name": "query"
		}
	])
	async def delbind(message, response, args, prefix):
		"""deletes a bind"""

		guild = message.guild

		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
		role_binds = guild_data.get("roleBinds") or {}

		bind_id = args.parsed_args["query"]

		if not role_binds:
			return await response.error(f"You have no binds! Say ``{prefix}bind`` to make a new bind.")

		if bind_id.isdigit(): # gave group number
			if not role_binds.get(bind_id):
				return await response.error(f"No binding for group ``{bind_id}`` exists.")

			parsed_args, is_cancelled = await args.call_prompt([
				{
					"prompt": "Please specify the ``rank ID`` (found on the group admin page), or say ``all`` " \
					f"to delete all binds for group **{bind_id}**. This is a guest role, say ``guest``.",
					"type": "string",
					"name": "rank"
				}
			])

			if not is_cancelled:
				rank = parsed_args["rank"]

				if rank.lower() in ("all", "everything"):
					role_binds.pop(bind_id, None)
				elif rank.lower() == "guest":
					if not role_binds.get(bind_id, {}).get("guest") and not role_binds.get(bind_id, {}).get("0"):
						return await response.error(f"No binding for group ``{bind_id}`` exists.")

					rank = rank == "guest" and "0"

					role_binds[bind_id].pop(rank, None)
					guild_data["roleBinds"] = role_binds

					await r.table("guilds").insert({
						**guild_data
					}, conflict="replace").run()

					return await response.success("Successfully **deleted** this bind.")
				else:
					if not role_binds[bind_id].get(rank):
						return await response.error(f"No bounded rank ID ``{rank}`` exists for group ``{bind_id}``.")

					role_binds[bind_id].pop(rank, None)

				guild_data["roleBinds"] = role_binds
				await r.table("guilds").insert({
					**guild_data
				}, conflict="replace").run()

				await response.success("Successfully **deleted** this bind.")
		else:
			# virtual group

			virtual_groups = role_binds.get("virtualGroups", {})

			if not virtual_groups:
				return await response.error(f"You have no virtual groups! Say {prefix}bind to make " \
					"a new one.")

			if not virtual_groups.get(bind_id):
				return await response.error(f"A bind with type ``{bind_id}`` does not exist.")

			if virtual_groups[bind_id].get("moreData"):
				ids = virtual_groups[bind_id]["moreData"].keys()

				parsed_args, is_cancelled = await args.call_prompt([
					{
						"prompt": "Multiple binds of this type exist! Please specify a bind with one "
						f'of these IDs: ``{", ".join(ids)}``',
						"type": "choice",
						"choices": list(ids),
						"name": "bind_choice"
					}
				])

				if not is_cancelled:
					virtual_groups[bind_id]["moreData"].pop(parsed_args["bind_choice"], None)

					role_binds["virtualGroups"] = virtual_groups
					guild_data["roleBinds"] = role_binds

					await r.table("guilds").insert({
						**guild_data
					}, conflict="replace").run()

					await response.success("Successfully **deleted** this bind.")
			else:
				virtual_groups.pop(bind_id, None)

				role_binds["virtualGroups"] = virtual_groups
				guild_data["roleBinds"] = role_binds

				await r.table("guilds").insert({
					**guild_data
				}, conflict="replace").run()

				await response.success("Successfully **deleted** this bind.")
