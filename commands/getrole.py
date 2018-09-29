from discord.errors import Forbidden
from discord import Embed

from resources.module import get_module
get_user, give_roblox_stuff = get_module("roblox", attrs=["get_user", "give_roblox_stuff"])
parse_message = get_module("commands", attrs=["parse_message"])


async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="getrole", alias=["getroles", "roleme"], category="Account")
	async def getrole(message, response, args, prefix):
		"""get roles from the server"""

		author = message.author

		primary_account, accounts = await get_user(author=message.author)

		if primary_account:

			added, removed, errored = await give_roblox_stuff(author, roblox_user=primary_account, complete=True)

			embed = Embed(title="Bloxlink Roles")

			if added:
				embed.add_field(name="Added", value="\n".join(added))
			if removed:
				embed.add_field(name="Removed", value="\n".join(removed))
			if errored:
				embed.add_field(name="Errored", value=errored[0])

			if not added and not removed and not errored:
				await response.success("All caught up! There are no roles to add/remove.")
				return

			embed.set_author(name=author, icon_url=author.avatar_url)

			await response.send(embed=embed)

		elif not accounts:
			message.content = f"{prefix}verify"
			return await parse_message(message)

		else:
			await response.error("You must set a primary account!\nPlease say ``{prefix}switchaccount`` " \
				"and pick one.")
