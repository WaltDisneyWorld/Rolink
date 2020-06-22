from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from discord import Embed
from resources.constants import IS_DOCKER # pylint: disable=import-error
from resources.exceptions import Error, CancelCommand # pylint: disable=import-error
import async_timeout
import asyncio

broadcast = Bloxlink.get_module("ipc", attrs="broadcast")
eval = Bloxlink.get_module("evalm", attrs="__call__")



@Bloxlink.command
class EvalCommand(Bloxlink.Module):
    """evaluates code"""

    def __init__(self):
        self.developer = True
        self.category = "Developer"
        self.arguments = [{
            "prompt": "Please type the code that you would like to execute.",
            "name": "code"
        }]

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        code = CommandArgs.parsed_args["code"]
        message = CommandArgs.message
        flags = CommandArgs.flags

        global_flag = flags.get("global")
        waiting_for_flag = flags.get("waiting_for")
        timeout_flag = flags.get("timeout", 10)

        if IS_DOCKER and global_flag:
            async with response.loading():
                stats = await broadcast(code, type="EVAL", timeout=timeout_flag != "0" and int(timeout_flag), waiting_for=waiting_for_flag)
                embed = Embed(title="Evaluation Result")

                for cluster_id, cluster_data in stats.items():
                    embed.add_field(name=f"Cluster {cluster_id}", value=cluster_data, inline=False)

                await response.send(embed=embed)

        else:
            async with response.loading():
                try:
                    async with async_timeout.timeout(timeout_flag != "0" and int(timeout_flag)):
                        embed = await eval(code, message, codeblock=False)
                except asyncio.TimeoutError:
                    raise Error("This evaluation timed out.")
                else:
                    if embed:
                        await response.send(embed=embed)
