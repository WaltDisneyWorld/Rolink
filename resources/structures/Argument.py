import asyncio
from resources.modules.resolver import resolver_map


class Argument:
	def __init__(self, message, args, command):
		self.message = message
		self.channel = message.channel
		self.author = message.author

		self.args = args
		self.parsed_args = []
		self.command = command

	async def call_prompt(self, args=None):
		from resources.framework import client

		using_args = args or self.command.arguments
		parsed_args = {}

		ctr = 0
		while ctr < len(using_args):
			arg = using_args[ctr]

			def check_prompt(message):
				return message.author.id == self.message.author.id \
					and message.channel.id == self.channel.id

			await self.channel.send(f'{arg["prompt"]}\nSay **cancel** to cancel.')

			try:

				msg = await client.wait_for("message", check=check_prompt, timeout=200.0)
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

async def validate_prompt(message, arg):
	content = message.content

	if content.lower() == "cancel":
		return False, True

	resolved = resolver_map.get(arg.get("type", "string"))(message, content=content, arg=arg)

	if resolved:
		if arg.get("check"):
			success = arg["check"](message)
		else:
			success = True
	else:
		success = False

	if not success:
		await message.channel.send(f'Invalid **{arg.get("type", "string")}** argument.'
		"Try again or say **cancel** to cancel.")

	return (success and resolved), False
