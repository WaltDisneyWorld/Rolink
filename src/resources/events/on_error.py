from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
import traceback

"""
@Bloxlink.event
async def on_error(event, *args, **kwargs):
    Bloxlink.error(event=event)
"""

@Bloxlink.event
async def on_error(event, *args, **kwargs):
    error = traceback.format_exc()
    Bloxlink.error(error, title=f"Error source: {event}.py")