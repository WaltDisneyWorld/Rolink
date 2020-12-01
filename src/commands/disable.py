
from resources.structures.Bloxlink import Bloxlink  # pylint: disable=import-error
from resources.modules.commands import commands # pylint: disable=import-error
from resources.exceptions import Error # pylint: disable=import-error
from resources.constants import BROWN_COLOR # pylint: disable=import-error
from discord import TextChannel

post_event = Bloxlink.get_module("utils", attrs=["post_event"])


@Bloxlink.command
class DisableCommand(Bloxlink.Module):
    """enable/disable commands globally or per channel for non-admins"""

    def __init__(self):
        self.aliases = ["enable"]
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.arguments = [
            {
                "prompt": "Please specify the **command name** to be enabled/disabled.",
                "type": "choice",
                "choices": commands.keys(),
                "name": "command_name"
            },
            {
                "prompt": "Should this command be enabled/disabled **globally** or **for a channel?**\n"
                          "You may either say ``globally`` or mention a ``channel``.",
                "type": ["channel", "choice"],
                "create_missing_channel": False,
                "name": "disable_type",
                "choices": ["globally", "global"]
            }
        ]


    async def __main__(self, CommandArgs):
        response = CommandArgs.response

        author = CommandArgs.message.author
        guild = CommandArgs.message.guild

        guild_data = CommandArgs.guild_data
        disabled_commands = guild_data.get("disabledCommands", {})

        disable_type = CommandArgs.parsed_args["disable_type"]
        command_name = CommandArgs.parsed_args["command_name"]

        if command_name in ("disable", "enable") or commands[command_name].developer_only:
            raise Error("You can't disable this command!")

        enable = disable_where = ""

        if isinstance(disable_type, TextChannel):
            channel_id = str(disable_type.id)
            disabled_commands["channels"] = disabled_commands.get("channels", {})

            disable_where = f"for channel {disable_type.mention}"

            if disabled_commands["channels"].get(channel_id):
                disabled_commands["channels"].pop(channel_id)
                enable = "enabled"
            else:
                disabled_commands["channels"][channel_id] = command_name
                enable = "disabled"

        else:
            disabled_commands["global"] = disabled_commands.get("global", [])

            disable_where = "**globally**"

            if command_name in disabled_commands["global"]:
                disabled_commands["global"].remove(command_name)
                enable = "enabled"
            else:
                disabled_commands["global"].append(command_name)
                enable = "disabled"

        guild_data["disabledCommands"] = disabled_commands
        await self.r.table("guilds").insert(guild_data, conflict="replace").run()

        await response.success(f"Successfully **{enable}** command ``{command_name}`` {disable_where} for non-admins.\n"
                                "If you would like to grant a certain person access to use this command, give them a role called ``Bloxlink Bypass``.")

        await post_event(guild, guild_data, "configuration", f"{author.mention} ({author.id}) has **{enable}** the command ``{command_name}`` {disable_where}.", BROWN_COLOR)
