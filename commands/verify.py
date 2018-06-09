from resources.modules.roblox import generate_code, check_username, \
	validate_code, verify_member, get_user, mass_filter


async def validate_username(message, username):
	username_check = await check_username(username)
	return username_check, not username_check and "Username not found"


async def roblox_prompts(message, response, args, r):
	author = message.author
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

	if not is_cancelled:
		success = await validate_code(parsed_args["name"], code)
		if success:
			await response.success("You're now linked to the bot!")
			await verify_member(author, str(args.checked_args["name"].id), primary_account=parsed_args["default"] == "yes")
		else:
			await response.error("Could not find the code on your profile. Please run this command " \
				"again and try again.")


async def setup(client, command, r, *args, **kwargs):

	@command(name="verify", flags=["force"], category="Account")
	async def verify(message, response, command_args):
		"""links your Roblox account to your Discord account"""

		author = message.author
		guild = message.guild

		force_flag = command_args.flags.get("force")

		if force_flag:
			await roblox_prompts(message, response, command_args, r)
		else:
			user, accounts = await get_user(author=author)
			if user:
				await user.fill_missing_details()
				await response.success("Welcome to " + guild.name + ", **" + user.username + "!**")
			elif accounts:
				parsed_accounts, parsed_users = await mass_filter(accounts)
				if parsed_accounts:
					parsed_accounts_text = ", ".join(parsed_accounts) + "\n"
					args, is_cancelled = await command_args.call_prompt([
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
				else:
					await roblox_prompts(message, response, command_args, r)
			else:
				await roblox_prompts(message, response, command_args, r)
