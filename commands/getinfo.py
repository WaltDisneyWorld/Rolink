from discord import Embed
from resources.modules.roblox import get_user, mass_filter


async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="getinfo", alias=["whois"], args = [
		{
			"name": "user",
			"prompt": "Please specify a user.",
			"type": "user",
			"optional": True

		}
	])
	async def getinfo(message, response, args):
		"""retrieves the user's Roblox information"""

		user = args.parsed_args.get("user", message.author)
		primary_account, accounts = await get_user(author=user)

		if accounts:

			parsed_accounts, _ = await mass_filter(accounts)

			description = None
			embed = None

			if not primary_account:
				description = not primary_account and "**No primary account.**"
				embed = Embed(description=description)
			else:

				await primary_account.fill_missing_details(complete=True)

				embed = Embed()

				if primary_account.is_verified:
					embed.add_field(name="Username", value=primary_account.username)
					embed.add_field(name="ID", value=primary_account.id)
					embed.add_field(name="Presence", value=primary_account.presence)
					#embed.add_field(name="Group Rank", value=primary_account.username)
					embed.set_thumbnail(url=primary_account.avatar)
					if primary_account.membership != "NBC":
						embed.add_field(name="Membership", value=primary_account.membership)
					embed.add_field(name="Badges", value=", ".join(primary_account.badges))

			if parsed_accounts:
				if primary_account.username in parsed_accounts:
					parsed_accounts.remove(primary_account.username)
					if parsed_accounts:
						embed.add_field(name="Other accounts", value= ", ".join(parsed_accounts))

			await response.send(embed=embed)

		else:

			await response.error("**"+user.name+"#"+user.discriminator+"** is not linked with Bloxlink.")

