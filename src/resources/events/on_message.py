from ..structures.Bloxlink import Bloxlink
from resources.constants import RELEASE

parse_message = Bloxlink.get_module("commands", attrs="parse_message")
in_prompt = Bloxlink.get_module("arguments", attrs="in_prompt")
validate_guild = Bloxlink.get_module("utils", attrs=["validate_guild"])

@Bloxlink.module
class MessageEvent:
	def __init__(self):
		pass

	async def __setup__(self):

		@Bloxlink.event
		async def on_message(message):
			author = message.author

			if RELEASE != "LOCAL" and getattr(message, "guild", None):
				if not await validate_guild(message.guild):
					return

			if author.bot or not message.channel or in_prompt(author):
				return

			await parse_message(message)
