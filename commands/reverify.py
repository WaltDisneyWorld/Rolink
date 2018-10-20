from resources.module import get_module
parse_message = get_module("commands", attrs=["parse_message"])


async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="reverify", category="Account")
	async def reverify(message, response, args, prefix):
		"""add a new account to Bloxlink"""

		message.content = f"{prefix}verify -add"

		await parse_message(message)
		