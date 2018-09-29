from discord.errors import Forbidden
from discord import File
from os import getcwd

from resources.module import get_module
post_event = get_module("utils", attrs=["post_event"])
get_nickname = get_module("roblox", attrs=["get_nickname"])



templates = "\n".join({
	"{group-shout} --> changes to the group shout",
	"{group-name} --> changes to the group name",
	"{group-id} --> changes to the group ID",
	"{roblox-name} --> changes to the shouter's roblox name",
	"{roblox-id} --> changes the shouter's roblox ID",
	"{group-rank} --> changes to the shouter's group rank",
}) + "\nNote: the {} must be included in the template."

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="shoutproxy", aliases=["shout"], arguments=[
		{
			"prompt": "This command will relay shouts made by your group to a channel that you specify.\n"
			"The group's shouts must be PUBLIC (viewable by everyone) for this to work.\n\n"
			"Which channel would you like to use for new shouts? Please either **mention the channel, or "
			"say the channel name.**\n\nSay **clear** to clear your channel.",
			"type": "channel",
			"name": "group_channel",
			"allowed": ["clear"]
		}
	], category="Premium", permissions={
		"raw": "manage_guild"
	})
	async def shoutproxy(message, response, args, prefix):
		"""relays group shouts to a channel"""

		guild = message.guild

		channel = args.parsed_args["group_channel"]
		channel = channel != "clear" and channel or None

		group_shout = None

		if channel:
			guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

			if not guild_data.get("groupID"):
				return await response.error("A group ID must be set first! " \
					f"Say ``{prefix}settings change groupID group_id_here`` to add one.")

			parsed_args, is_cancelled = await args.call_prompt([
				{
					"name": "type",
					"prompt": "Would you like to **customize** how the shout post looks " \
						"like, or use an **embed** with general metadata already attached?",
					"type": "choice",
					"choices": ["customize", "embed"]
				}
			])
			if not is_cancelled:
				if parsed_args["type"] == "customize":
					parsed_args, is_cancelled = await args.call_prompt([
						{
							"name": "format",
							"prompt": "How would you like to format your group post? Please format your message "
							f"using these templates: ```{templates}```",
							"ignoreFormatting": True
						},
						{
							"name": "clean_content",
							"prompt": "Would you like Bloxlink to automatically strip mentions (pings) " \
								"from the shout so they don't ping anyone?",
							"type": "choice",
							"choices": ["yes", "no"]
						}
					])
					if not is_cancelled:
						group_shout = {
							"format": parsed_args["format"],
							"cleanContent": parsed_args["format"],
							"channel": str(channel.id),
							"default": False,
						}
				else:
					parsed_args, is_cancelled = await args.call_prompt([
						{
							"name": "prepend",
							"prompt": "Would you like to prepend some text before the shout embed?\n" \
								"Possible use cases: ``@everyone`` before the shout embed to tag everyone.\n\n" \
								"Say the text to prepend, or say ``skip`` to not prepend any text."
						}
					])
					if not is_cancelled:
						prepend = parsed_args["prepend"] not in ("clear", "skip", "done", "next") and parsed_args["prepend"]
						group_shout = {
							"default": True,
							"channel": str(channel.id),
							"prependContent": prepend
						}

			if group_shout:
				await r.table("guilds").insert({
					"id": str(guild.id),
					"groupShout": group_shout
				}, conflict="update").run()

			await response.success("Successfully **saved** your new group shouts channel!\nNote: the shouts "
			"must be PUBLIC for this to work. If they're not, no group shouts will be sent to your channel.")

			try:
				await channel.send(
					file=File(f"{getcwd()}/assets/shoutproxy_help.png", filename="shoutproxy_help.png")
				)
			except Forbidden:
				try:
					await channel.send("https://cdn.discordapp.com/attachments/480614508633522176/480911126582788105/unknown.png")
				except Forbidden:
					pass
		else:
			guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
			guild_data.pop("groupShout", None)

			await r.table("guilds").insert({
				**guild_data
			}, conflict="replace").run()

			await response.success("Succesfully **deleted** your group shouts channel. "
			"No new messages will be sent there.")
