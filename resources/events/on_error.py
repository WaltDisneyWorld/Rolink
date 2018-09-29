import traceback
import logging

from resources.module import get_module
log_error = get_module("utils", attrs=["log_error"])


log = logging.getLogger()

class OnError:
	def __init__(self, **kwargs):
		client = kwargs.get("client")

		@client.event
		async def on_error(event, *args, **kwargs):
			error = traceback.format_exc()
			log.exception(error)

			await log_error(error, f'Uncaught Exception: {event}')
