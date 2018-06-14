from discord.errors import Forbidden
from discord import Embed
from resources.modules.roblox import get_roles, get_user


async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="getrole", alias=["getroles", "roleme"], category="Account")
	async def getrole(message, response, args):
		"""gets roles from the server"""

		author = message.author

		primary_account = await get_user(author=message.author)

		if primary_account:

			add_roles, remove_roles, errors = await get_roles(message.author)

			error_num = len(errors)

			added = []
			removed = []
			failed = []

			for role in remove_roles:
				try:
					await author.remove_roles(role, reason="Removing old group roles")
					removed.append(role.name)
				except Forbidden:
					error_num += 1
					errors.append(str(error_num) + ") Failed to remove role ``" + role.name + "``. Please drag " \
					"my role above the other roles and make sure I have ``Manage Roles`` permission.")

			for role in add_roles:
				try:
					await author.add_roles(role, reason="Adding group roles")
					added.append(role.name)
				except Forbidden:
					error_num += 1
					errors.append(str(error_num) + ") Failed to add role ``" + role.name + "``. Please drag " \
					"my role above the other roles and make sure I have ``Manage Roles`` permission.")

			embed = Embed(title="Bloxlink Roles")

			if added:
				embed.add_field(name="Added", value="\n".join(added))
			if removed:
				embed.add_field(name="Removed", value="\n".join(removed))
			if failed:
				embed.add_field(name="Failed", value="\n".join(failed))
			if errors:
				embed.add_field(name="Errors", value="\n".join(errors))

			if not added and not removed:
				embed.description = "No binds apply to you. If you're a server manager, " \
					"you need to make a bind for this person's rank."

			await response.send(embed=embed)


		else:
			await response.error("You must set a primary account!\nPlease say ``!switchaccount`` " \
				"and pick one.")
