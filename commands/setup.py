import asyncio
from discord import Embed
from discord.errors import Forbidden
from discord.utils import find
from resources.modules.roblox import get_group


in_prompt = {}

def prefix_validation(prefix):
	return len(prefix) > 5, "Prefix must be 5 characters or less."

def group_validation(group):
	if not group.isdigit():
		return True, "Group ID must be a number."
	elif len(group) > 13:
		return True, "Group IDs currently do not exceed 13 characters."

	return False, None

def validate_choices(*choices):
	def wrapper(choice):
		if choice in choices:
			return False, None
		else:
			return True, "Choice must be of either: ``{}``".format(choices)
	return wrapper

def nickname_validation(nick):
	return len(nick) > 32, "Nickname must be 32 characters or less."

prompts = [
	{
		"prompt": "Thank you for choosing Bloxlink! In a few simple prompts, we'll "  \
			"configure Bloxlink for your server.\n\nPre-configuration:\n\t" \
			"Before continuing, please ensure that Bloxlink has all the proper permissions— " \
			"such as the ability to manage roles, nicknames, channels, kick members, etc. " \
			"If you do not set these permissions, you may encounter issues with using certain commands.",
		"information": True
	},
	{
		"prompt": "Would you like to change the server prefix? " \
			"If so, what would you like to change it to?",
		"validation": prefix_validation,
		"default": "!",
		"name": "Prefix"
	},
	{
		"prompt": "Would you like to link a ROBLOX group to this Discord server?\n" \
			"Please say the ID of your ROBLOX group.",
		"validation": group_validation,
		"default": "0",
		"name": "GroupID"
	},
	{
		"prompt": "Would you like to change the Verified role name to something else?\n" \
			"Please say the name of the role that you would like to use for linked users.",
		"validation": None,
		"default": "Verified",
		"name": "VerifiedRole"
	},
	{
		"prompt": "Would you like to unlock some cool features such as automatically " \
			"giving users their group role when they join the server, or locking your server " \
			"to group members only?\nYou will be given the links to donate at the end of the setup." \
			"\nDonations help keep Bloxlink alive by covering server costs!\n\nValid choices: (yes/no/skip)",
		"validation": validate_choices("yes", "no"),
		"default": "yes",
		"name": "Donate"
	},
	{
		"prompt": "Would you like to automatically transfer your ROBLOX group ranks to Discord roles?\n" \
			"Valid choices:\n\t``merge`` - This will not remove any roles and merge your ROBLOX group " \
			"ranks with your current roles.\n\t``replace`` - This will remove all of your current Discord " \
			"roles and replace them with your ROBLOX group ranks. You will need to configure " \
			"permissions, colors, and other role settings yourself.\nValid choices: (merge/replace/skip)",
		"validation": validate_choices("merge", "replace"),
		"default": "merge",
		"name": "RoleManagement"
	},
	{
		"prompt": "Would you like to set a nickname for new members that join your server?\nAvailable " \
			"templates: ```\n{roblox-name} --> changes to their ROBLOX Username\n{discord-name} " \
			"--> changes to their Discord username\n{discord-nick} --> changes to their " \
			"server display name\n{roblox-id} --> changes to their ROBLOX ID\n" \
			"{group-rank} --> changes to their current rank in the linked group```" \
			"\n\nPlease say the nickname template that you would like to use. You can " \
			"use multiple.\n",
		"validation": nickname_validation,
		"default": "{roblox-name}",
		"name": "NicknameTemplate"
	},
]

def check(author, dm=False):
	def wrapper(message):
		return message.author == author and ((dm and not message.guild) or message.guild)

	return wrapper


async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")
	r = kwargs.get("r")

	@command(name="setup", category="Administration", permissions={
		"raw": "manage_guild"
	})
	async def setup_command(message, response, args):
		"""configures your server with Bloxlink"""

		author = message.author
		guild = message.guild

		if in_prompt.get(author.id):
			await response.error("You already have a running setup!")
			return
		else:
			in_prompt[author.id] = True

		x = 0
		already_posted = False

		setup_args = {}

		while x < len(prompts):
			prompt = prompts[x]

			buffer = ["**{}**\n\n\n".format(prompt["prompt"])]

			if prompt.get("information"):
				buffer.append("**Say ``next`` to continue.**")
			else:
				buffer.append("**Say ``skip`` to skip this setting and leave it as the default.**")

			buffer.append("\n**To end this prompt, say ``cancel``.**")

			embed = Embed(title="Setup Prompt", description="".join(buffer))

			success = await response.send(embed=embed, dm=True, strict_post=True)

			if success and not already_posted:
				await response.text(author.mention + ", **check your DMs!**")
				already_posted = True
			elif not success and already_posted:
				in_prompt[author.id] = None
				return

			try:
				msg = await client.wait_for("message", check=lambda m: m.author == author and not m.guild, timeout=200.0)
				content = msg.content.lower()

				if msg.content == "cancel":
					await response.send("**Cancelled setup.**", dm=True)
					in_prompt[author.id] = None
					break
				elif content == "skip" or content == "next" or content == "no":
					x += 1
					if not prompt.get("information") and prompt.get("default"):
						setup_args[prompt["name"]] = [prompt["default"], "skipped"]
				else:
					if prompt.get("validation"):
						failed, err = prompt["validation"](msg.content)
						if not failed:
							x += 1
							setup_args[prompt["name"]] = [msg.content, msg.content]
						else:
							await response.error("Your content failed validation.\n**Error**: " + err, dm=True)
					else:
						if prompt.get("information"):
							await response.send("**Cancelled setup.**", dm=True)
							in_prompt[author.id] = None
							break
						else:
							x += 1
							setup_args[prompt["name"]] = [msg.content, msg.content]

			except asyncio.TimeoutError:
				await response.send("**Cancelled setup: timeout reached (200s)**", dm=True)
				in_prompt[author.id] = None
				break

		else:

			buffer = [x + " ➜ " + y[1] for x, y in setup_args.items()]

			embed = Embed(title="Setup Prompt", description="**You have reached the end of the " \
				"configuration. Here are your current settings: ```fix" +
				f'\n{chr(10).join(buffer)}' + " ```\n\n\nTo complete this setup, please say ``done``." +
				"\n\nSay ``cancel`` to cancel setup.**")


			await response.send(embed=embed, dm=True)

			try:
				msg = await client.wait_for("message", check=lambda m: m.author == author and not m.guild, timeout=200.0)
				content = msg.content.lower()
			except asyncio.TimeoutError:
				await response.send("**Cancelled setup: timeout reached (200s)**", dm=True)
			else:
				if content == "done":

					embed = Embed(title="Setup Complete")

					guild_settings = await r.table("guilds").get(str(guild.id)).run() or {}

					group_id = setup_args.get("GroupID", ("0", "skipped"))
					role_management = setup_args.get("RoleManagement", ("merge", "skipped"))
					prefix = setup_args.get("Prefix", ("prefix", "skipped"))
					nickname_template = setup_args.get("NicknameTemplate", ("{roblox-name}", "skipped"))
					verified_role = setup_args.get("VerifiedRole", ("Verified", "skipped"))
					donate = setup_args.get("Donate", ("yes", "skipped"))

					if donate[0] == "yes":
						embed = Embed(title="Premium Features", description="**Donating allows you to unlock " \
							"more features on the bot, such as automatically verifying " \
							"users when they enter the server, or to lock your server to " \
							"a specific group.\n\nYou may donate here: <https://selly.gg/u/bloxlink/>** ")
						await response.send(embed=embed, dm=True)

					if group_id[0] != "0" and group_id[1] != "skipped":
						group = await get_group(group_id[0])
						if group:
							if not group.roles:
								await response.error("Unable to complete setup: Group has no rolesets.")
								return
							else:
								sorted_roles = sorted(group.roles, key=lambda role: role["Rank"], reverse=True)

								if role_management[0] == "replace" and role_management[1] != "skipped":
									for role in guild.roles:
										if not role.is_default():
											try:
												await role.delete(reason="Replace option during setup")
											except Forbidden:
												continue

								for rank in sorted_roles:
									role = find(lambda r: r.name == rank["Name"], guild.roles)
									if not role:
										try:
											await guild.create_role(name=rank["Name"], reason="Group {} Role - {}".format(
												group.id,
												author
											))
										except Forbidden:
											await response.error("Failed to create role. Please ensure I have the ``Manage Roles`` permission" \
												"and drag the Bloxlink role above the other roles.")
											return

						else:
							await response.error("Group ID not valid")
							return

					await r.table("guilds").insert({
						"id": str(guild.id),
						"prefix": (prefix[1] != "skipped" and prefix[0]) or guild_settings.get("prefix") or prefix[0],
						"nicknameTemplate": (nickname_template[1] != "skipped" and nickname_template[0]) or \
							guild_settings.get("nicknameTemplate") or nickname_template[0],
						"verifiedRoleName": (verified_role[1] != "skipped" and verified_role[0]) or \
							guild_settings.get("verifiedRoleName") or verified_role[0],
						"groupID": (group_id[1] != "skipped" and group_id[0]) or \
							guild_settings.get("groupID") or None						

					}, conflict="update").run()
					await response.send(":thumbsup: Your server is now configured with Bloxlink!", dm=True)
	

				else:
					await response.send("**Cancelled setup.**", dm=True)

			finally:
				in_prompt[author.id] = None
		