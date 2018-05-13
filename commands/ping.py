from resources.modules.commands import command



@command("ping", alias=["test"])
async def ping_test():
    """measures the latency of the bot"""

    print("ping command called")