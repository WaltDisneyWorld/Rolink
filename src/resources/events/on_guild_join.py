from ..structures.Bloxlink import Bloxlink
from resources.constants import RELEASE, SERVER_INVITE
from discord.errors import NotFound, Forbidden
from discord import Object

is_premium = Bloxlink.get_module("utils", attrs=["is_premium"])

NOT_PREMIUM = "Notice - Server Not Premium\n.Pro can only be used on " \
              "servers with premium from Patreon.com. If you are indeed subscribed " \
              "on patreon, then please use the ``!transfer`` command on the normal " \
              "Bloxlink bot and transfer your premium **to the server owner**. You may " \
              "revoke the premium transfer with ``!transfer disable``. Also note that " \
              "it may take up to 10 minutes for the bot to register your premium from Patreon " \
              "**after** linking your Discord account. Find more information with the " \
              f"``!donate`` command. Any trouble? Message us here: {SERVER_INVITE}"

WELCOME_MESSAGE = "\n\n".join([
                    "Thanks for adding Bloxlink! <:BloxlinkHappy:506622933339340830>",
                    ":exclamation: Run ``!help`` to view a list of commands.",
                    ":gear: Run ``!setup`` for an all-in-one command to set-up your server with Bloxlink.",
                    ":gear: If you're looking to change specific settings, use the ``!settings`` command.",
                    ":woman_office_worker: if you're looking to link Roblox groups, use the ``!bind`` command.",
                    "<:BloxlinkSale:506622933184020490> Interested in supercharging your Bloxlink experience? Run the ``!donate`` command and help support Bloxlink development!",
                    f"<:BloxlinkSearch:506622933012054028> **Need support?** Join our community server: {SERVER_INVITE}"])

@Bloxlink.module
class GuildJoinEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_guild_join(guild):
            chosen_channel = None
            sorted_channels = sorted(guild.text_channels, key=lambda c: c.position, reverse=False)

            for channel in sorted_channels:
                permissions = channel.permissions_for(guild.me)

                if permissions.send_messages and permissions.read_messages:
                    chosen_channel = channel
                    break

            if RELEASE == "PRO":
                profile, _ = await is_premium(Object(id=guild.owner_id))

                if not profile.features.get("pro"):
                    if chosen_channel:
                        try:
                            await chosen_channel.send(NOT_PREMIUM)
                        except (NotFound, Forbidden):
                            pass

                    await guild.leave()

                    return

            if chosen_channel:
                try:
                    await chosen_channel.send(WELCOME_MESSAGE)
                except (NotFound, Forbidden):
                    pass
