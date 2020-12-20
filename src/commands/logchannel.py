from resources.structures.Bloxlink import Bloxlink  # pylint: disable=import-error
from resources.exceptions import Message  # pylint: disable=import-error
from resources.constants import ARROW, BROWN_COLOR # pylint: disable=import-error
from discord import Embed, Object


post_event = Bloxlink.get_module("utils", attrs=["post_event"])
get_features = Bloxlink.get_module("premium", attrs=["get_features"])


@Bloxlink.command
class LogChannelCommand(Bloxlink.Module):
    """subscribe to certain Bloxlink events. these will be posted in your channel(s)."""

    def __init__(self):
        self.arguments = [
            {
                "prompt": "Would you like to **change** your log channels (add/delete), or **view** your "
                          "current log channels?",
                "name": "choice",
                "type": "choice",
                "choices": ["change", "add", "delete", "view"]
            }
        ]

        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.aliases = ["logchannels"]


    async def __main__(self, CommandArgs):
        choice = CommandArgs.parsed_args["choice"]

        if choice in ("change", "add", "delete"):
            return await self.change(CommandArgs)
        else:
            return await self.view(CommandArgs)


    @Bloxlink.subcommand()
    async def change(self, CommandArgs):
        """add/delete a log channel"""

        prefix = CommandArgs.prefix
        response = CommandArgs.response
        guild_data = CommandArgs.guild_data

        author = CommandArgs.message.author

        guild = CommandArgs.message.guild

        log_channels = guild_data.get("logChannels") or {}

        parsed_args = await CommandArgs.prompt([
            {
                "prompt": "Please select an **event** to add/delete:\n"
                          "``all`` "              + ARROW + " all events will be sent to your channel\n"
                          "``verifications`` "    + ARROW + " user verifications will be logged "
                                                            "to your channel\n"
                          "``configurations`` "   + ARROW + " any Bloxlink setting alteration will be "
                                                            "logged to your channel\n"
                         "``inactivity notices`` _(premium)_ " + ARROW + " user-set inactivity notices "
                                                                         "from ``" + prefix + "profie`` will "
                                                                         "be logged to your channel\n"
                        "``binds`` "              + ARROW +   " bind insertions/deletions will be logged to your channel\n"
                        "``moderation`` "         + ARROW +   " automatic moderation actions by certain features will be "
                                                              "logged to your channel",

                "name": "log_type",
                "type": "choice",
                "choices": ["all", "verifications", "configurations", "inactivity notices", "binds", "moderation"]
            },
            {
                "prompt": "Please either **mention a channel**, or say a **channel name.**\n"
                          "Successful ``{log_type}`` events will be posted to this channel.\n\n"
                          "**Please make sure Bloxlink has permission to send/read messages "
                          "from the channel!**",
                "name": "log_channel",
                "footer": "Say **clear** to **delete** an already existing log channel of this type.",
                "type": "channel",
                "exceptions": ["clear", "delete"]
            }
        ])

        log_type = parsed_args["log_type"]

        if log_type.endswith("s"):
            log_type = log_type[:-1] # remove ending "s" - looks better on embed titles

        log_channel = parsed_args["log_channel"]
        action = None

        if log_type == "inactivity notices":
            donator_profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)

            if not donator_profile.features.get("premium"):
                raise Message("Only premium subscribers can subscribe to ``inactivity notices``!\n"
                              f"Please use ``{prefix}donate`` for instructions on subscribing to premium.", type="silly")


        if log_channel in ("clear", "delete"):
            log_channels.pop(log_type, None)
            action = "deleted"
        else:
            log_channels[log_type] = str(log_channel.id)
            action = "saved"

        if not log_channels:
            guild_data.pop("logChannels", None)
        else:
            guild_data["logChannels"] = log_channels

        await self.r.table("guilds").insert(guild_data, conflict="replace").run()

        await post_event(guild, guild_data, "configuration", f"{author.mention} ({author.id}) has **changed** the ``log channels``.", BROWN_COLOR)

        await response.success(f"Successfully **{action}** your log channel!")


    @Bloxlink.subcommand()
    async def view(self, CommandArgs):
        """view your log channels"""

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        log_channels = guild_data.get("logChannels") or {}

        response = CommandArgs.response

        if not log_channels:
            raise Message("You have no log channels!", type="silly")

        embed = Embed(title="Bloxlink Log Channels")
        embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)
        embed.set_author(name=guild.name, icon_url=guild.icon_url)

        description = []

        for log_type, log_channel_id in log_channels.items():
            log_channel = guild.get_channel(int(log_channel_id))
            description.append(f"``{log_type}`` {ARROW} {log_channel and log_channel.mention or '(Deleted)'}")

        embed.description = "\n".join(description)

        await response.send(embed=embed)
