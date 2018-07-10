from discord.errors import Forbidden
from discord import Embed
from resources.modules.roblox import get_roles, get_user, give_roblox_stuff


async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="getrole", alias=["getroles", "roleme"], category="Account")
	async def getrole(message, response, args):
		"""get roles from the server"""

		author = message.author

		primary_account, _ = await get_user(author=message.author)

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


		else:
			await response.error("You must set a primary account!\nPlease say ``!switchaccount`` " \
				"and pick one.")
