from discord import Embed

from resources.module import get_module
is_premium = get_module("utils", attrs=["is_premium"])

async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="status", category="Premium", free_to_use=True, arguments=[
		{
			"prompt": "Please specify the user to inspect.",
			"type": "user",
			"name": "user",
			"optional": True
		}
	], examples=[
		"status",
		"status @justin"
	])
	async def status(message, response, args, prefix):
		"""shows your Bloxlink Premium status"""

		user = args.parsed_args.get("user") or message.author

		profile = await is_premium(author=user, guild=message.guild)

		embed = Embed()
		embed.set_author(name=user, icon_url=user.avatar_url)

		if profile.is_premium:
			embed.colour = 0xFDC333
			embed.add_field(name="Premium Status", value="Active")

			if profile.selly:
				embed.add_field(name="Expiry", value=profile.days == 0 and "Never (unlimited)" or f'**{profile.days}** days left')

			elif profile.patreon:
				amount_cents = profile.payment["attributes"]["amount_cents"]
				dollars = int(amount_cents / 100)
				cents_left = amount_cents % 100

				if cents_left < 10:
					cents_left = "0" + str(cents_left)

				embed.add_field(name="Amount Pledged", value=f"${dollars}.{cents_left}")

			"""
			if tier == "bronze":
				embed.colour = 0xc95b0a
			elif tier == "pro":
				embed.colour = 0xFDC333
			"""

		else:
			embed.description = "This user does not have premium. They may donate [here](https://selly.gg/u/bloxlink)."

		await response.send(embed=embed)
