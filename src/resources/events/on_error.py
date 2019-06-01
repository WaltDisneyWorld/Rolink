from ..structures.Bloxlink import Bloxlink
import traceback


@Bloxlink.event
async def on_error(event, *args, **kwargs):
    error = traceback.format_exc()
    Bloxlink.error(error)

