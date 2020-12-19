from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import RELEASE, SERVER_INVITE # pylint: disable=import-error
from discord.errors import NotFound, Forbidden
from discord import Object

get_prefix = Bloxlink.get_module("utils", attrs=["get_prefix"])
get_features = Bloxlink.get_module("premium", attrs=["get_features"])
get_board = Bloxlink.get_module("trello", attrs=["get_board"])
post_stats = Bloxlink.get_module("site_services", name_override="DBL", attrs="post_stats")

NOT_PREMIUM = "**Notice - Server Not Premium**\nPro can only be used on " \
              "servers with premium from Patreon.com. If you are indeed subscribed " \
              "on patreon, then please use the ``{prefix}transfer`` command on the normal " \
              "Bloxlink bot and transfer your premium **to the server owner**. You may " \
              "revoke the premium transfer with ``{prefix}transfer disable``. Also note that " \
              "it may take up to 10 minutes for the bot to register your premium from Patreon " \
              "**after** linking your Discord account. Find more information with the " \
              "``{prefix}donate`` command. Any trouble? Message us here: " + SERVER_INVITE

WELCOME_MESSAGE = "\n\n".join([
                    "Thanks for adding Bloxlink! <:BloxlinkHappy:506622933339340830>",
                    ":exclamation: Run ``{prefix}help`` to view a list of commands.",
                    ":gear: Run ``{prefix}setup`` for an all-in-one command to set-up your server with Bloxlink.",
                    ":gear: If you're looking to change specific settings, use the ``{prefix}settings`` command.",
                    ":woman_office_worker: if you're looking to link Roblox groups, use the ``{prefix}bind`` command.",
                    "<:BloxlinkSale:506622933184020490> Interested in supercharging your Bloxlink experience? Run the ``{prefix}donate`` command and help support Bloxlink development!",
                    f"<:BloxlinkSearch:506622933012054028> **Need support?** Join our community server: {SERVER_INVITE}"])

@Bloxlink.module
class GuildJoinEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_guild_join(guild):
            guild_id = str(guild.id)
            chosen_channel = None
            sorted_channels = sorted(guild.text_channels, key=lambda c: c.position, reverse=False)

            for channel in sorted_channels:
                permissions = channel.permissions_for(guild.me)

                if permissions.send_messages and permissions.read_messages:
                    chosen_channel = channel
                    break

            guild_data = await self.r.table("guilds").get(guild_id).run() or {"id": guild_id}
            trello_board = await get_board(guild_data=guild_data, guild=guild)
            prefix, _ = await get_prefix(guild=guild, trello_board=trello_board)

            guild_data["hasBot"] = True
            await self.r.table("guilds").insert(guild_data, conflict="update").run()

            if RELEASE == "PRO":
                profile, _ = await get_features(Object(id=guild.owner_id), guild=guild, cache=False)

                if not profile.features.get("pro"):
                    if chosen_channel:
                        try:
                            await chosen_channel.send(NOT_PREMIUM.format(prefix=prefix))
                        except (NotFound, Forbidden):
                            pass

                    await guild.leave()

                    return

            elif RELEASE == "MAIN":
                await post_stats()

            if chosen_channel:
                try:
                    await chosen_channel.send(WELCOME_MESSAGE.format(prefix=prefix))
                except (NotFound, Forbidden):
                    pass
