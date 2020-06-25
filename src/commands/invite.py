from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from discord import Embed


@Bloxlink.command
class InviteCommand(Bloxlink.Module):
    def __init__(self):
        pass

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        prefix = CommandArgs.prefix

        embed = Embed(title="Invite Bloxlink")
        embed.description = "**To add Bloxlink to your server, click this link: https://blox.link/invite\n" \
                            "Support server: https://blox.link/support**"

        embed.add_field(name="Frequently Asked Questions", value="1.) I don't see my server when I try to invite the bot!\n" \
                                                                f"> There are 2 possibilities:\n> a.) you don't have the ``Manage Server`` " \
                                                                "role permission\n> b.) you aren't logged on the correct account; " \
                                                                "go to <https://discord.com> and log out.")


        embed.set_footer(text="Thanks for choosing Bloxlink!", icon_url=Bloxlink.user.avatar_url)

        await response.send(embed=embed)
