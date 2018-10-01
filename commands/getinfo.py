from discord import Embed

from resources.module import get_module
get_user, mass_filter, get_note = get_module("roblox", attrs=["get_user", "mass_filter", "get_note"])


async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="getinfo", cooldown=5, alias=["whois"], args = [
		{
			"name": "user",
			"prompt": "Please specify a user.",
			"type": "user",
			"optional": True

		}
	], examples=[
		"getinfo @justin",
		"getinfo"
	])
	async def getinfo(message, response, args, prefix):
		"""retrieve the user's Roblox information"""

		async with message.channel.typing():

			user = args.parsed_args.get("user", message.author)
			primary_account, accounts = await get_user(author=user)
			guild = message.guild

			notes = []

			if accounts or primary_account:

				parsed_accounts = None

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

					guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

					if primary_account.is_verified:
						id = primary_account.id
						notes = await get_note(user, roblox_id=id, roblox_user=primary_account)

						if primary_account.is_banned:
							embed.add_field(name="Username", value=f"~~{primary_account.username}~~")
							embed.description = "Note: this user is _banned_. Not all data may be available."
						else:
							embed.add_field(name="Username", value=primary_account.username)

						embed.add_field(name="ID", value=primary_account.id)
						embed.add_field(name="Presence", value=primary_account.presence)

						if primary_account.age_string:
							embed.add_field(name="Join Date", value=primary_account.age_string)
						if primary_account.age:
							embed.add_field(name="Account Age", value=f"{primary_account.age} days old")


						if guild_data.get("groupID"):
							group_id = guild_data.get("groupID")

							if group_id:
								group_id = str(group_id)

							group = primary_account.groups.get(group_id)

							if group:
								embed.add_field(name="Group Rank", value=group.user_role)
							else:
								embed.add_field(name="Group Rank", value="Guest")

						if primary_account.avatar:
							embed.set_thumbnail(url=primary_account.avatar)

						embed.set_author(name=user, icon_url=user.avatar_url, url=primary_account.profile_link)

						if primary_account.membership != "NBC":
							embed.add_field(name="Membership", value=primary_account.membership)

						if primary_account.badges:
							embed.add_field(name="Badges", value=", ".join(primary_account.badges))

						if primary_account.description:
							embed.add_field(name="Description", value=primary_account.description[0:500])
				"""
				if parsed_accounts:
					if primary_account and primary_account.username in parsed_accounts:
						parsed_accounts.remove(primary_account.username)
					if parsed_accounts:
						embed.add_field(name="Other accounts", value= ", ".join(parsed_accounts))
				"""

				if notes:
					embed.add_field(name="User Title", value="\n".join(notes))

				await response.send(embed=embed)

			else:

				await response.error(str(user) + " is **not linked** with Bloxlink.")

