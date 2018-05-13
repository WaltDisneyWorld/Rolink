from resources.modules.commands import command



@command("ping", alias=["test"])
def ping_test():
    """measures the latency of the bot"""

    print("ping command called")