import traceback
import logging
from resources.modules.utils import log_error
from resources.storage import get


client = get("client")
loop = client.loop

log = logging.getLogger()



@client.event
async def on_error(event, *args, **kwargs):
	error = traceback.format_exc()
	log.exception(error)

	await log_error(error, f'Uncaught Exception: {event}')
