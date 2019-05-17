from ..structures.Bloxlink import Bloxlink


@Bloxlink.event
async def on_ready():
    Bloxlink.log(f"Logged in as {Bloxlink.user.name}")
