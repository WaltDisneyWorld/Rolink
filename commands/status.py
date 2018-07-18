from resources.modules.utils import is_premium
from discord import Embed

async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="status", category="Premium", free_to_use=True, arguments=[
		{
			"prompt": "Please specify the user to inspect.",
			"type": "user",
			"name": "user",
			"optional": True
		}
	])
	async def status(message, response, args, prefix):
		"""shows your Bloxlink Premium status"""

		user = args.parsed_args.get("user") or message.author

		is_p, days, codes_redeemed = await is_premium(author=user)

		embed = Embed()
		embed.set_author(name=user, icon_url=user.avatar_url)

		if is_p:
			embed.add_field(name="Premium Status", value="Active")
			embed.add_field(name="Expiry", value=days == 0 and "Never (unlimited)" or f'**{days}** days left')
		else:
			embed.description = "This user does not have premium. They may donate [here](https://selly.gg/u/bloxlink)"

		await response.send(embed=embed)
