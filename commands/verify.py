from discord.errors import Forbidden
from discord import File
from os import getcwd

from resources.module import get_module
generate_code, check_username, validate_code, verify_member, \
get_user, mass_filter, give_roblox_stuff, get_nickname = get_module("roblox", attrs=[
	"generate_code",
	"check_username",
	"validate_code",
	"verify_member",
	"get_user",
	"mass_filter",
	"give_roblox_stuff",
	"get_nickname"]
)
post_event = get_module("utils", attrs=["post_event"])

async def validate_username(message, username, previous_args):
	username_check = await check_username(username)
	return username_check, not username_check and "Username not found"

async def verified(author, roblox_user, guild=None):
	guild = guild or (hasattr(author, "guild") and author.guild)

	if roblox_user.is_verified:
		await post_event("verify", f"{author.mention} is now verified as **{roblox_user.username}.**", guild=guild, color=0x2ECC71)
		await give_roblox_stuff(author, roblox_user=roblox_user, complete=True)

async def roblox_prompts(author, channel, response, args, guild=None, verify_as=None):
	guild = guild or (hasattr(author, "guild") and author.guild)

	code = await generate_code()

	prompts = [
		{
			"name": "default",
			"type": "choice",
			"choices": ["yes", "no"],
			"prompt": ":question: Would you like to set this as your default Roblox account?",
		}	
	]

	if not verify_as:
		prompts.insert(0, {
			"name": "name",
			"prompt": ":question: What's your Roblox Username?",
			"check": validate_username
		})

	parsed_args, is_cancelled = await args.call_prompt(prompts)

	if not is_cancelled:

		user = verify_as and await get_user(username=verify_as) or args.checked_args["name"]

		if isinstance(user, tuple):
			user = user[0]

		if user:
			await user.fill_missing_details()

			if not user.is_verified:
				return await response.error("This Roblox account does not exist. Please try again.")
		else:
			return await response.error("This Roblox account does not exist. Please try again.")

		if not is_cancelled:

			try:
				await channel.send(
					file=File(f"{getcwd()}/assets/verify_help.png", filename="verify_help.png")
				)
			except Forbidden:
				try:
					await channel.send("https://cdn.discordapp.com/attachments/480614508633522176/480614556360507402/unknown.png")
				except Forbidden:
					pass

			_, is_cancelled = await args.call_prompt([
				{
					"name": "done",
					"type": "choice",
					"choices": ["done"],
					"prompt": f'Hello, **{user.username}!** To confirm that you own this Roblox account, please ' \
						f'go here: <https://www.roblox.com/my/account> and put this code on your **profile or status**:\n```{code}```\n\n' \
						"Refer to the attachment for instructions." \
						"\n\nThen say **done** to continue.",
				}
			])


			success = await validate_code(user.username, code)

			if not is_cancelled:
				if success:
					await response.success(f"You're now linked to Bloxlink as **{user.username}**!")
					await verify_member(author, user.id, primary_account=parsed_args["default"] == "yes")

					await verified(author, user, guild)

				else:
					await response.error("Could not find the code on your profile. Please run this command " \
						"again and try again.")

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="verify", flags=["force"], category="Account", flags_enabled=True)
	async def verify(message, response, args, prefix):
		"""link your Roblox account to your Discord account"""

		author = message.author
		guild = message.guild
		channel = message.channel

		if args.flags.get("add") or args.flags.get("force") or args.flags.get("new") or \
			args.flags.get("f") or args.flags.get("a") or args.flags.get("n"):

			await roblox_prompts(author, channel, response, args, guild)

		elif args.args and "-" not in args.args[0]:
			account = args.args[0]

			_, accounts = await get_user(author=author)

			if accounts:
				parsed_accounts, parsed_users = await mass_filter(accounts)

				for parsed_account in parsed_accounts:
					if account.lower() == parsed_account.lower():
						roles = list(author.roles)
						roles.remove(guild.default_role)

						real_account = parsed_users[parsed_accounts.index(parsed_account)]

						await verify_member(author, real_account, guild=guild, primary_account=False)

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

						await verified(author, real_account, guild)

						return await response.success(f"You're now verified as **{real_account.username}!**")

			await roblox_prompts(author, channel, response, args, guild, verify_as=account)

		else:
			user, _ = await get_user(author=author)

			if user:
				await user.fill_missing_details()

				guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

				verify_message = guild_data.get("welcomeMessage",
					"Welcome to {server-name}, **{roblox-name}!**")
				resolved_message = await get_nickname(author=author, roblox_user=user,
					guild_data=guild_data, template=verify_message, ignore_trim=True)
	
				resolved_message = resolved_message + f"\n\nSay ``{prefix}verify -add`` to change your Roblox account. Then, use " \
					f"``{prefix}switchuser`` to switch into that user on different servers."

				await response.send(resolved_message)
				await verified(author, user, guild)

			else:
				await roblox_prompts(author, channel, response, args, guild)
