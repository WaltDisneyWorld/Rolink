from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import ARROW, LIMITS, RED_COLOR # pylint: disable=import-error
from discord import Embed


DESC = "\n".join([
    "**Looking for a list of a commands?",
    "Use ``{PREFIX}commands`` instead.**",
    "\n"
])


@Bloxlink.command
class AboutCommand(Bloxlink.Module):
    """learn about Bloxlink!"""

    def __init__(self):
        self.aliases = ["bloxlink"]

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        response = CommandArgs.response

        embed = Embed(title="Meet Bloxlink")

        description = DESC.format(PREFIX=CommandArgs.prefix)

        embed.add_field(name="What is Bloxlink?", value=f"{description}Bloxlink is a Roblox integration for Discord. "
                                                        "We add the ability to bring over Roblox to your Discord server by "
                                                        "syncing Group roles to Server roles, linking Roblox accounts to Discord "
                                                        "accounts, and more. [READ MORE](https://blox.link)\n\nWe're on a mission "
                                                        "to simplify integrating Roblox into Discord so players and groups can spend "
                                                        "more time connecting with their friends and communities.", inline=False)


        embed.add_field(name="**Join our community!**", value="[Join us in bringing The Roblox players together through Discord.](https://blox.link/support)",
                       inline=False)

        embed.set_thumbnail(url=Bloxlink.user.avatar_url)


        await response.send(embed=embed)
