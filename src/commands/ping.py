from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
import time


@Bloxlink.command
class PingCommand(Bloxlink.Module):
    """measure the latency between the bot and Discord"""

    def __init__(self):
        pass

    async def __main__(self, CommandArgs):
        message = CommandArgs.message
        response = CommandArgs.response

        t_1 = time.perf_counter()

        await message.channel.trigger_typing()

        t_2 = time.perf_counter()
        time_delta = round((t_2-t_1)*1000)

        await response.send(f"Pong! ``{time_delta}ms``")
