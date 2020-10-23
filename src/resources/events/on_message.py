from ..structures import Bloxlink, Arguments # pylint: disable=import-error
from resources.constants import RELEASE # pylint: disable=import-error

parse_message = Bloxlink.get_module("commands", attrs="parse_message")
validate_guild = Bloxlink.get_module("utils", attrs=["validate_guild"])


@Bloxlink.module
class MessageEvent:
	def __init__(self):
		pass

	async def __setup__(self):
		@Bloxlink.event
		async def on_message(message):
			author = message.author

			if (author.bot or not message.channel or Arguments.in_prompt(author)) or (message.guild and message.guild.unavailable):
				return

			await parse_message(message)
