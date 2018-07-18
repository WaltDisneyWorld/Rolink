from discord import Embed



async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="donate", alias=["premium"])
	async def donate(message, response, args, prefix):
		"""donate to Bloxlink! :)"""

		me = message.guild.me

		embed = Embed(description = "We appreciate all donations! Donations go towards **server " \
			"costs, domain costs, and other expenses.** If you'd like to be a generous soul and donate" \
			", we'll give you some **sweet perks** such as a **sweet role in our Discord and " \
			"donator-only commands.** :)")
		embed.add_field(name="Patreon", value="[click](https://patreon.com/bloxlink)")
		embed.add_field(name="PayPal/BTC/Stripe", value="[click](https://selly.gg/u/bloxlink)")
		embed.add_field(name="Other", value="DM justin#1337")

		embed.set_author(name=me.name, icon_url=me.avatar_url)

		await response.send(embed=embed)
