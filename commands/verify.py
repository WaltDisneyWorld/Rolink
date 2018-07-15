from resources.modules.roblox import generate_code, check_username, \
	validate_code, verify_member, get_user, mass_filter, give_roblox_stuff
from resources.modules.utils import post_event


async def validate_username(message, username, previous_args):
	username_check = await check_username(username)
	return username_check, not username_check and "Username not found"


async def roblox_prompts(message, response, args, guild=None):
	author = message.author
	guild = guild or author.guild
	code = await generate_code()
	parsed_args, is_cancelled = await args.call_prompt([
		{
			"name": "name",
			"prompt": ":question: What's your Roblox Username?",
			"check": validate_username
		},
		{
			"name": "default",
			"type": "choice",
			"choices": ["yes", "no"],
			"prompt": ":question: Would you like to set this as your default Roblox account?",
		},
		{
			"name": "done",
			"prompt": "Hello, **{name}!** To confirm that you own this Roblox account, please " \
				f'put this code on your profile: ``{code}``\n\nThen say **done** to continue.',
			"type": "choice",
			"choices": ["done"],
		}
	])

	user, _ = await get_user(author=author)
	await user.fill_missing_details()

	if not is_cancelled:
		success = await validate_code(parsed_args["name"], code)
		if success:
			await response.success("You're now linked to the bot!")
			await verify_member(author, str(args.checked_args["name"].id), primary_account=parsed_args["default"] == "yes")
			await verified(author, user, guild)
		else:
			await response.error("Could not find the code on your profile. Please run this command " \
				"again and try again.")

async def verified(author, roblox_user, guild=None):
	guild = guild or author.guild

	if roblox_user.is_verified:
		await post_event("verify", f"{author.mention} is now verified as **{roblox_user.username}.**", guild=guild, color=0x2ECC71)
		await give_roblox_stuff(author, roblox_user=roblox_user, complete=True)


async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="verify", flags=["force"], category="Account", flags_enabled=True)
	async def verify(message, response, args):
		"""link your Roblox account to your Discord account"""

		author = message.author
		guild = message.guild

		force_flag = args.flags.get("force") or args.flags.get("f") or args.flags.get("new") \
			or args.flags.get("add")

		if force_flag:
			await roblox_prompts(message, response, args, guild)
		else:
			user, accounts = await get_user(author=author)
			if user:
				await user.fill_missing_details()
				msg = await response.success("Welcome to " + guild.name + ", **" + user.username + "!**")
				await verified(author, user, guild)				
			elif accounts:
				parsed_accounts, parsed_users = await mass_filter(accounts)
				if parsed_accounts:
					parsed_accounts_text = ", ".join(parsed_accounts) + "\n"
					args, is_cancelled = await args.call_prompt([
						{
							"name": "chosen_account",
							"type": "choice",
							"choices": parsed_accounts,
							"prompt": ":exclamation: No default Roblox account set\n\nWhich account would you like to verify as?\n\n**Please pick one: **" \
								+ parsed_accounts_text
						},
						{
							"name": "default",
							"type": "choice",
							"choices": ["yes", "no"],
							"prompt": ":question: Would you like to set this as your **default** Roblox account from now on?"
						}
					])
					if not is_cancelled:
						chosen = args["chosen_account"]

						await verify_member(author, parsed_users[parsed_accounts.index(chosen)], primary_account=args["default"] == "yes")
						await response.success("Welcome to " + guild.name + ", **" + chosen + "!**")

						user, _ = await get_user(author=author)

						if user:
							await verified(author, user, guild)
				else:
					await roblox_prompts(message, response, args, guild)
			else:
				await roblox_prompts(message, response, args, guild)
