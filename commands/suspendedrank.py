from discord.errors import Forbidden

from resources.module import get_module
post_event = get_module("utils", attrs=["post_event"])
get_nickname = get_module("roblox", attrs=["get_nickname"])

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="suspendedrank", aliases=["suspendedrole"], arguments=[
		{
			"prompt": "What **Roblox Group Rank** should be restricted from " \
				"getting roles? Please specify the **rank name**, e.g. Suspended\n\n" \
				"Your group must be linked via ``!setup`` for this to work (main group).\n\n"
				"Say **clear** to turn OFF this feature.",
			"type": "string",
			"name": "suspended_rank",
		}
	], category="Administration", permissions={
		"raw": "manage_guild"
	})
	async def suspended_rank(message, response, args, prefix):
		"""restricts getting roles for Suspended users"""

		guild = message.guild

		suspended = args.parsed_args["suspended_rank"]
		suspended = suspended != "clear" and suspended or None

		await r.table("guilds").insert({
			"id": str(guild.id),
			"suspendedRank": suspended
		}, conflict="update").run()

		await response.success(f'Successfully **{suspended and "enabled" or "disabled"}** ' \
			"suspended rank!")
