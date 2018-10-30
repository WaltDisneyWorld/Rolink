from resources.module import get_module
redeem_code = get_module("utils", attrs=["redeem_code"])

async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="redeem", cooldown=2, category="Premium", free_to_use=True, arguments=[
		{
			"prompt": "Please specify the code to redeem.",
			"type": "string",
			"name": "code"
		}
	])
	async def redeem(message, response, args, prefix):
		"""redeems a Bloxlink Premium code"""

		code = args.parsed_args["code"]

		days, already_redeemed = await redeem_code(author=message.author, code=code)

		if days == -1:
			await response.send("<:BloxlinkCrying:506622931791642625> Cannot redeem code: you **already** have a **lifetime** subscription!")
		elif days == -2:
			await response.error("Cannot redeem key: tier levels don't match. You must first transfer " \
				f"your subscription with ``{prefix}transfer``.")
		elif days == 0:
			await response.success("You now have **lifetime** premium!")
		elif already_redeemed:
			await response.error("You've **already** redeemed this code!")
		elif days:
			await response.success("Successfully **verified** your premium key! You've been given "
				+ f'**{days}** days of Bloxlink Premium.')
		else:
			await response.error("**Invalid key!** Please ensure it is correct and not been already claimed.")
