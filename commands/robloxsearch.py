from discord import Embed

from resources.module import get_module
get_user, get_note = get_module("roblox", attrs=["get_user", "get_note"])


async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="robloxsearch", flags_enabled=True, alias=["search"], args = [
		{
			"name": "user",
			"prompt": "Please specify the search query.",
			"type": "string",

		}
	], examples=[
		"robloxsearch 1337 -username",
		"robloxsearch builderman",
		"robloxsearch 1"
	])
	async def robloxsearch(message, response, args, prefix):
		"""searches Roblox for the account"""

		guild = message.guild

		async with message.channel.typing():

			user = args.parsed_args.get("user")

			if (user.isdigit() and not args.flags.get("username")) or args.flags.get("id"):
				primary_account, _ = await get_user(id=user)
			else:
				primary_account, _ = await get_user(username=user)

			if primary_account:
				await primary_account.fill_missing_details(complete=True)

				embed = Embed()

				if primary_account.is_verified:
					id = primary_account.id

					if primary_account.is_banned:
						embed.add_field(name="Username", value=f"~~{primary_account.username}~~")
						embed.description = "<:ban:476838302092230672> This user is _banned_. Not all data may be available."
					else:
						embed.add_field(name="Username", value=primary_account.username)

					note = await get_note(roblox_id=id)
					guild_data = await r.table("guilds").get(str(guild.id)).run() or {}

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

					embed.set_author(name=primary_account.username, url=primary_account.profile_link)

					if primary_account.membership != "NBC":
						embed.add_field(name="Membership", value=primary_account.membership)

					if primary_account.badges:
						embed.add_field(name="Badges", value=", ".join(primary_account.badges))

					if primary_account.description:
						embed.add_field(name="Description", value=primary_account.description[0:500])

					if note:
						embed.add_field(name="Official Note", value=note)

					await response.send(embed=embed)

				else:
					return await response.error("There is no account found with your query.")
			else:
				return await response.error("There is no account found with your query.")
