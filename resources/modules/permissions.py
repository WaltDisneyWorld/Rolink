from config import OWNER, RELEASE, DONATOR_EMBED
from discord.utils import find
from discord.errors import Forbidden, NotFound

from resources.module import get_module
is_premium = get_module("utils", attrs=["is_premium"])

class Permissions:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")

	async def check_permissions(self, command, channel, author):
		#if author.id == OWNER:
		#	return True, None

		if not hasattr(author, "guild"):
			if not channel.guild.chunked:
				await self.client.request_offline_members(channel.guild)
				return False, "Error: Member not loaded. We're now attempting to fetch all offline members." \
					"you may attempt to retry this command in a few seconds."
		permissions = command.permissions

		if permissions.get("owner_only") or command.category == "Developer":
			if author.id != OWNER:
				return False, "This command is reserved for the bot developer."

		if command.category == "Premium" or RELEASE == "PRO":
			profile = await is_premium(guild=channel.guild)

			if not command.free_to_use and not profile.is_premium:
				try:
					await channel.send(embed=DONATOR_EMBED)
				except (Forbidden, NotFound):
					pass

				return False, "This command is reserved for donators. The server owner " \
					"must have premium for this command to work. Run ``!donate`` for instructions on donating."


		roles = permissions.get("roles") or permissions.get("role")

		if roles:
			if isinstance(roles, str):
				role = find(lambda r: r.name == roles or r.id == roles, author.roles)

				if not role:
					return False, f'Missing role: {roles}'

			elif isinstance(roles, list):
				missing_roles = []

				for role in roles:
					has_role = find(lambda r: r.name == role or r.id == role, author.roles)

					if not has_role:
						missing_roles.append(role)

				if missing_roles:
					return False, f'Missing role(s): {", ".join(missing_roles)}'


		raw = permissions.get("raw")

		if raw:
			perms = channel.permissions_for(author)

			if isinstance(raw, str):
				if not getattr(perms, raw, None):
					return False, f'Missing role permission: {raw}'

			elif isinstance(raw, list):
				missing_perms = []

				for perm in raw:
					if not getattr(perms, perm, None):
						missing_perms.append(perm)

				if missing_perms:
					return False, f'Missing role permission(s): {", ".join(missing_perms)}'

		return True, None

def new_module():
	return Permissions
