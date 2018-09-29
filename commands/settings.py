from discord import Embed

from resources.module import get_module
is_premium, post_event = get_module("utils", attrs=["is_premium", "post_event"])

settings = {
	"prefix": "change the prefix",
	"nicknameTemplate": "change the nickname template",
	"groupID": "change the linked group",
	"autoVerification": "toggle whether members are verified on join",
	"verifiedRoleName": "change the verified role name",
	"allowOldRoles": "the bot will not remove old roles",
	"autoRoles": "toggle whether members get all roles on join",
	"welcomeMessage": "message that users are greeted with",
	"joinDM": "people will be DM'd the greeting on server join",
	"persistRoles": "(premium) toggle whether members get updated roles/nick on typing",
	"groupLocked": "(premium) toggle whether members must be in the group to join",
	"dynamicRoles": "(premium) toggle whether missing roles are automatically created"
}

settings_choices = list(settings.keys())

settings_text = "```fix\n" + "\n".join([x + " ➜ " + y for x,y in settings.items()]) + "```"


async def resolve_change_with(message, change_with, previous_args):
	if previous_args["to_change"] in ("autoVerification", "autoRoles", "persistRoles", "allowOldRoles"
										"groupLocked", "dynamicRoles", "joinDM"):
		change_with = change_with in ("yes", "true", "on", "false", "off", "enabled")
		return change_with and str(change_with), "Value must be of: true or false"
	else:
		return change_with, None



async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="settings", arguments=[
		{
			"prompt": "Would you like to ``change`` or ``view`` your " \
				"settings?",
			"name": "action",
			"type": "choice",
			"choices": ["change", "view", "help"],
			"arg_len": 1
		}
	], category="Administration", examples=[
		"settings change prefix ?",
		"settings view",
		"settings help prefix",
		"settings change"
	])
	async def settings_cmd(message, response, args, prefix):
		"""view and configure Bloxlink settings"""

		guild = message.guild
		author = message.author
		channel = message.channel

		action = args.parsed_args["action"]

		if action == "change":

			perms = channel.permissions_for(author)
			if not perms.administrator and not perms.manage_guild:
				return await response.error("You need ``manage_server`` or ``administrator`` to " \
					"change settings.")

			is_cancelled = False
			to_change = None
			change_with = None
			parsed_args = None

			del args.args[0]

			try:
				to_change = args.args[0]
				del args.args[0]
				change_with = " ".join(args.args)
			except IndexError:
				parsed_args, is_cancelled = await args.call_prompt([
					{
						"prompt": "What value would you like to change?\n" \
							+ settings_text,
						"type": "choice",
						"choices": settings_choices,
						"name": "to_change"
					},
					{
						"prompt": "What would you like to set the value as?",
						"type": "string",
						"name": "change_with",
						"check": resolve_change_with,
						"min": 1,
						"max": 50
					}
				])
			finally:
				if not is_cancelled:

					to_change = to_change or parsed_args["to_change"]
					to_change = [x for x in settings_choices if x.lower() == to_change.lower()]

					if not to_change:
						return await response.error("Invalid settings choice.")
					else:
						to_change = to_change[0]

					change_with = change_with or (parsed_args and parsed_args.get("change_with"))

					if not change_with:
						return await response.error("Invalid settings choice.")

					if to_change in ("autoVerification", "autoRoles", "persistRoles", "allowOldRoles", "groupLocked", "dynamicRoles"
									"joinDM"):
						change_with = change_with.lower() in ("true", "on", "enabled", "yes")

					await r.table("guilds").insert({
						"id": str(guild.id),
						to_change: change_with
					}, conflict="update").run()

					await post_event("setup", f"{author.mention} changed the Bloxlink settings.", guild=guild, color=0xD9E212)

					await response.success("Saved!")

		elif action == "view":
			guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

			text = "\n".join(["**" + x + "** ➜ ``" + str(guild_data.get(x, "N/A"))+ "``" for x in settings.keys()])

			is_p, days, _, tier, has_premium = await is_premium(guild=guild)

			text = text + f'\n**Premium** ➜ ``{is_p}``'

			if is_p:
				text = text + f'\n\t**Premium Until** ➜ ``{days==0 and "lifetime" or str(days) + " days"}``'

			embed = Embed(title="Bloxlink Server Settings")

			embed.set_footer(text="Use !settings help <option> to view information on the choice.")
			embed.description = text
			embed.set_author(name=guild.name, icon_url=guild.icon_url)

			await response.send(embed=embed)

		elif action == "help":
			del args.args[0]

			option = None
			is_cancelled = None
			parsed_args = None

			try:
				option = args.args[0]
				del args.args[0]
			except IndexError:
				parsed_args, is_cancelled = await args.call_prompt([
					{
						"prompt": "What settings choice would you like more information on?\n" \
							+ f"```fix\n{list(settings.keys())}```",
						"type": "choice",
						"choices": settings_choices,
						"name": "option"
					}
				])
			finally:
				if not is_cancelled:
					option = option or parsed_args["option"]
					desc = settings.get(option)
					if option in settings.keys():
						await response.text(f"**{option}** ➜ ``{desc}``")
					else:
						await response.error("Invalid settings choice.")

