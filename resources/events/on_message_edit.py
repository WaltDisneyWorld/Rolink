from resources.modules.commands import processed_messages

from resources.module import get_module
parse_message = get_module("commands", attrs=["parse_message"])

class OnMessageEdit:
	def __init__(self, **kwargs):
		self.client = kwargs.get("client")

	async def setup(self):

		@self.client.event
		async def on_message_edit(before, after):
			if after.author.bot:
				return

			if before.id not in processed_messages:
				await parse_message(after)

def new_module():
	return OnMessageEdit
