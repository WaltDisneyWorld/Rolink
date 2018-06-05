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
		self.checked_args = {}
		self.command = command

	async def call_prompt(self, args=None, flag_str=None, skip_args=None):
		from resources.framework import client

		using_args = args or self.command.arguments
		parsed_args = {}

		ctr = 0

		while ctr < len(using_args):
			skipped_arg = None
			arg = using_args[ctr]

			if skip_args:
				try:
					skipped_arg = skip_args[ctr]
				except IndexError:
					pass

			if skipped_arg:
				resolved, _ = await validate_prompt(self.message, arg, flag_str=flag_str, skipped_arg=skipped_arg, argument_class=self)
				if resolved:
					ctr += 1
					parsed_args[arg["name"]] = resolved
				else:
					success = False
					while not success:
						await self.channel.send(arg["prompt"].format(
							**parsed_args
						) + "\nSay **cancel** to cancel.")
						try:
							msg = await client.wait_for("message", check=check_prompt(self), timeout=200.0)
							resolved, is_cancelled = await validate_prompt(msg, arg, argument_class=self)

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
				await self.channel.send(arg["prompt"].format(
					**parsed_args
				) + "\nSay **cancel** to cancel.")
				try:
					msg = await client.wait_for("message", check=check_prompt(self), timeout=200.0)
					resolved, is_cancelled = await validate_prompt(msg, arg, argument_class=self)

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

async def validate_prompt(message, arg, skipped_arg=None, flag_str=None, argument_class=None):
	err_msg = None

	if skipped_arg:
		if skipped_arg.endswith(flag_str):
			skipped_arg = skipped_arg.rstrip(flag_str).strip()
		resolved, err_msg = resolver_map.get(arg.get("type", "string")) \
			(message, arg=arg, content=skipped_arg)
	else:
		content = message.content.rstrip(flag_str).strip()

		if content.lower() == "cancel":
			return False, True

		resolved, err_msg = resolver_map.get(arg.get("type", "string"))(message, arg=arg, content=content)

	if resolved:
		if arg.get("check"):
			success, err_msg = await arg["check"](message, resolved)
			if argument_class:
				argument_class.checked_args[arg["name"]] = success
		else:
			success = True
	else:
		success = False

	if not success:
		if err_msg:
			await message.channel.send(f'Invalid **{arg.get("type", "string")}** argument: ``{err_msg}.`` ' \
				"Try again or say **cancel** to cancel.")
		else:
			await message.channel.send(f'Invalid **{arg.get("type", "string")}** argument. ' \
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