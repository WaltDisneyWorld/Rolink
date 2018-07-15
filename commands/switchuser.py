from resources.modules.roblox import verify_member, give_roblox_stuff, get_user
from resources.modules.utils import post_event
from discord.errors import Forbidden


async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="switchuser", category="Account")
	async def switchuser(message, response, args):
		"""change your account for the server"""

		author = message.author
		guild = message.guild
		roblox_user, accounts = await get_user(author=author)

		if roblox_user or accounts:
			buffer = []
			if roblox_user:
				await roblox_user.fill_missing_details()
				buffer.append(f"**Primary Account:** {roblox_user.username}")
			if accounts:
				await response.send(buffer[0])
				parsed_args, is_cancelled = await args.call_prompt([
					{
						"prompt": "Which account would you like to verify as _for this server_?\n" \
							"**Account IDs:** " + ", ".join(accounts),
						"type": "choice",
						"choices": accounts,
						"name": "acc"
					},
					{
						"prompt": "Would you like to set this account as your **primary** account?",
						"type": "choice",
						"choices": ["yes", "no"],
						"name": "primary"
					},
					{
						"prompt": "Please note: this will remove all your roles and give you roles " \
							"depending on the server configuration. Continue?",
						"type": "choice",
						"choices": ["yes", "no"],
						"name": "continue"
					}
				])
				if not is_cancelled:
					if parsed_args["continue"] == "yes":
						await verify_member(author, parsed_args["acc"], primary_account=parsed_args["primary"] == "yes")

						if parsed_args["primary"] == "yes":
							await response.success("**Saved** your new primary account!")
						roles = list(author.roles)
						roles.remove(guild.default_role)
						try:
							await author.remove_roles(*roles, reason="Switched User— cleaning their roles")
						except Forbidden:
							await post_event(
								"error",
								f"Failed to delete roles from {author.mention}. Please ensure I have " \
									"the ``Manage Roles`` permission, and drag my role above the other roles.",
								guild=guild,
								color=0xE74C3C
							)

						new_user, _ = await get_user(id=parsed_args["acc"])
						await new_user.fill_missing_details()

						await give_roblox_stuff(author, complete=True)

						await post_event("verify", f"{author.mention} is now verified as **{roblox_user.username}.**", guild=guild, color=0x2ECC71)

						await response.success("You're now verified as **"+new_user.username+"!**")
			else:
				await response.error("You only have **one account** linked! Run ``!verify --force`` to link another.")
		else:
			await response.error("You're **not linked** with Bloxlink! Run ``!verify`` to verify.")