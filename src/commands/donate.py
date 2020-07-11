from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import ARROW, LIMITS # pylint: disable=import-error
from discord import Embed

PREMIUM_PERKS = "\n".join([
    f"- More role bindings allowed (from {LIMITS['BINDS']['FREE']} to {LIMITS['BINDS']['PREMIUM']}).",
     "- Exclusive premium-only settings such as setting an age-limit, group shout channel, **changing the username "
        "and pfp of the bot** (white-labeling), and much more. "
        "See ``{prefix}settings change/help`` and look at the premium section.",
     "- Reduced cooldown on some commands.",
     "- More groups allowed to be added to your Group-Lock (``{prefix}grouplock``)."
])


@Bloxlink.command
class DonateCommand(Bloxlink.Module):
    """learn how to receive Bloxlink Premium"""

    def __init__(self):
        self.aliases = ["premium"]

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        prefix = CommandArgs.prefix

        embed = Embed(title="Bloxlink Premium")
        embed.description = "We appreciate all donations!\nBy donating a certain amount, you will receive **[Bloxlink Premium](https://www.patreon.com/join/bloxlink?)** " \
                            f"on __every server you own__ and receive these perks:\n{PREMIUM_PERKS.format(prefix=prefix)}" \

        embed.add_field(name="Frequently Asked Questions", value="1.) Can I transfer premium to someone else?\n"
                                                                f"> Yes, use the ``{prefix}transfer`` command. "
                                                                 "You'll be able to disable the transfer whenever you want "
                                                                f"with ``{prefix}transfer disable``.\n"
                                                                 "2.) How do I receive my perks after donating?\n"
                                                                 "> Link your Discord account to Patreon. After, wait 10-15 "
                                                                 "minutes and your perks should be activated. Feel free to ask "
                                                                 "in our support server if you need more help: <https://blox.link/support>.", inline=False)

        embed.add_field(name="Premium Monthly (**$5**)", value="[click here](https://www.patreon.com/join/bloxlink?)")
        embed.add_field(name="Premium Lifetime", value="no longer offered")

        embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)

        await response.send(embed=embed)
