from discord.utils import find
from discord.errors import Forbidden, NotFound

from resources.module import get_module
post_event = get_module("utils", attrs=["post_event"])


class Resolver:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")

	async def string_resolver(self, message, arg, content=None):
		if not content:
			content = message.content

		min = arg.get("min", -100)
		max = arg.get("max", 100)

		if arg.get("min") or arg.get("max"):
			if min <= len(content) <= max:
				return str(content), None
			else:
				return False, f'String character count not in range: {min}-{max}'

		return str(content), None

	async def number_resolver(self, message, arg, content=None):
		if not content:
			content = message.content

		if content.isdigit():
			min = arg.get("min", -100)
			max = arg.get("max", 100)

			if arg.get("min") or arg.get("max"):
				if min <= len(content) <= max:
					return int(content), None
				else:
					return False, f'Number character count not in range: {min}-{max}'
			else:
				return int(content), None

			return int(content), None

		return False, "You must pass a number"

	async def choice_resolver(self, message, arg, content=None):
		if not content:
			content = message.content

		for choice in arg["choices"]:
			if choice.lower() == content.lower():
				return choice, None

		return False, f'Choice must be of either: {str(arg["choices"])}'

	async def user_resolver(self, message, arg, content=None):
		if not content:
			content = message.content

		guild = message.guild

		if message.mentions:
			if message.mentions[0].id != self.client.user.id:
				return message.mentions[0], None

		is_int, is_id = None, None

		try:
			is_int = int(content)
			is_id = is_int > 15
		except ValueError:
			pass

		if is_id:
			user = guild.get_member(is_int)
			if user:
				return user, None
			else:
				try:
					user = await self.client.get_user_info(int(is_int))
					return user, None
				except NotFound:
					return False, "A user with this discord ID does not exist"
		else:
			return guild.get_member_named(content), None

		return False, "Invalid user"

	async def channel_resolver(self, message, arg, content=None):
		if not content:
			content = message.content

		guild = message.guild

		if message.channel_mentions:
			return message.channel_mentions[0], None
		else:
			is_int, is_id = None, None

			try:
				is_int = int(content)
				is_id = is_int > 15
			except ValueError:
				pass

			if is_id:
				return guild.get_channel(is_int), None
			else:
				return find(lambda c: c.name == content, guild.text_channels), None

		return False, "Invalid channel"

	async def role_resolver(self, message, arg, content=None):
		if not content:
			content = message.content

		guild = message.guild

		if message.role_mentions:
			return message.role_mentions[0], None
		else:
			is_int, is_id = None, None
			role = None

			try:
				is_int = int(content)
				is_id = is_int > 15
			except ValueError:
				pass

			if is_id:
				role = find(lambda r: r.id == is_int, guild.roles)
			else:
				role = find(lambda r: r.name == content, guild.roles)

			if role:
				return role, None
			else:
				try:
					role = await guild.create_role(name=content, reason="Creating missing role")
				except Forbidden:
					await post_event(
						"error",
						f"Failed to create role {content}, please ensure I have the ``Manage Roles`` permission.",
						guild=guild,
						color=0xE74C3C
					)
					return None, "**Invalid permissions:** please ensure I have the ``Manage Roles`` permission."
				else:
					return role, None

		return False, "Invalid role"

	def get_resolver(self, name):
		for method_name in dir(self):
			if method_name.endswith("resolver") and name in method_name:
				if callable(getattr(self, method_name)):
					return getattr(self, method_name)

def new_module():
	return Resolver
