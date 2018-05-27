import asyncio
import re
from resources.modules.resolver import resolver_map


def check_prompt(self):
	def wrapper(message):
		return message.author.id == self.message.author.id \
			and message.channel.id == self.channel.id
	return wrapper


class Argument:
	def __init__(self, message, args, command):
		self.message = message
		self.channel = message.channel
		self.author = message.author

		self.args = args
		self.parsed_args = {}
		self.command = command

	async def call_prompt(self, args=None, flag_str=None, skip_args=None):
		from resources.framework import client

		using_args = args or self.command.arguments
		parsed_args = {}

		ctr = 0

		while ctr < len(using_args):
			skipped_arg = None
			arg = using_args[ctr]

			try:
				skipped_arg = skip_args[ctr]
			except IndexError:
				pass

			if skipped_arg:
				resolved, _ = await validate_prompt(self.message, arg, flag_str=flag_str, skipped_arg=skipped_arg)
				if resolved:
					ctr += 1
					parsed_args[arg["name"]] = resolved
				else:
					success = False
					while not success:
						await self.channel.send(f'{arg["prompt"]}\nSay **cancel** to cancel.')
						try:
							msg = await client.wait_for("message", check=check_prompt(self), timeout=200.0)
							resolved, is_cancelled = await validate_prompt(msg, arg)

							if resolved:
								ctr += 1
								success = True
								parsed_args[arg["name"]] = resolved

							elif is_cancelled:
								await self.channel.send("**Cancelled prompt.**")
								return None, "user cancellation"

						except asyncio.TimeoutError:
							await self.channel.send("**Cancelled prompt:** timeout reached (200s)")
							return None, "timeout reached"
			else:
				await self.channel.send(f'{arg["prompt"]}\nSay **cancel** to cancel.')
				try:
					msg = await client.wait_for("message", check=check_prompt(self), timeout=200.0)
					resolved, is_cancelled = await validate_prompt(msg, arg)

					if resolved:
						ctr += 1
						parsed_args[arg["name"]] = resolved

					elif is_cancelled:
						await self.channel.send("**Cancelled prompt.**")
						return None, "user cancellation"

				except asyncio.TimeoutError:
					await self.channel.send("**Cancelled prompt:** timeout reached (200s)")
					return None, "timeout reached"

		if not args:
			self.parsed_args = parsed_args

		return parsed_args, None

async def validate_prompt(message, arg, skipped_arg=None, flag_str=None):
	if skipped_arg:
		if skipped_arg.endswith(flag_str):
			skipped_arg = skipped_arg.rstrip(flag_str).strip()
		resolved = resolver_map.get(arg.get("type", "string"))(message, content=skipped_arg, arg=arg)
	else:
		content = message.content.rstrip(flag_str).strip()

		if content.lower() == "cancel":
			return False, True

		resolved = resolver_map.get(arg.get("type", "string"))(message, content=content, arg=arg)

	if resolved:
		if arg.get("check"):
			success = arg["check"](message, resolved)
		else:
			success = True
	else:
		success = False

	if not success:
		await message.channel.send(f'Invalid **{arg.get("type", "string")}** argument. '
		"Try again or say **cancel** to cancel.")

	return (success and resolved), False


def parse_flags(content):
	# https://stackoverflow.com/questions/50554698/easy-way-to-extract-flags-from-a-string
	flags = {m.group(1): m.group(2) or True for m in re.finditer(r"--?(\w+)(?: ([^-]*)|$)", content)}

	if flags:
		try:
			content = content[content.index("--"):]
		except ValueError:
			try:
				content = content[content.index("-"):]
			except ValueError:
				return {}, None
	
	return flags, flags and content

