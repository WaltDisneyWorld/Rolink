from discord.utils import find
from resources.framework import config


def check_permissions(command, channel, author):
	if author.id == config.OWNER:
		return True, None

	if not author.guild:
		return False, "Error: Member not loaded."

	permissions = command.permissions

	if permissions.get("owner_only"):
		if author.id != config.OWNER:
			return False, "This command is reserved for the bot developer."

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
