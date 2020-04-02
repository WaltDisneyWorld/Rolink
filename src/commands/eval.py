from resources.structures.Bloxlink import Bloxlink
from discord import Embed
from resources.constants import IS_DOCKER

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

        if IS_DOCKER and CommandArgs.flags.get("global"):
            stats = await broadcast(code, type="EVAL")
            embed = Embed(title="Code Evaluation")

            for cluster_id, cluster_data in stats.items():
                embed.add_field(name=f"Cluster {cluster_id}", value=cluster_data, inline=False)

            await response.send(embed=embed)

        else:
            embed = await eval(code, message, codeblock=False)

            await response.send(embed=embed)
