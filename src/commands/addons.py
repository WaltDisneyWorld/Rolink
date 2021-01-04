from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error # pylint: disable=import-error
from discord import Embed, Object


set_guild_value = Bloxlink.get_module("cache", attrs="set_guild_value")
get_features = Bloxlink.get_module("premium", attrs="get_features")
addons, get_enabled_addons = Bloxlink.get_module("addonsm", attrs=["addons", "get_enabled_addons"])


@Bloxlink.command
class AddonsCommand(Bloxlink.Module):
    """enable/disable a server add-on"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.aliases = ["addon"]
        self.hidden = True

        self.arguments = [
            {
                "prompt": "Would you like to **view** the available add-ons, or **change** (enable/disable) an add-on?",
                "name": "subcommand",
                "type": "choice",
                "choices": ["view", "change", "enable", "disable"]
            }
        ]

    async def __main__(self, CommandArgs):
        subcommand_choice = CommandArgs.parsed_args["subcommand"]

        if subcommand_choice in ("change", "enable", "disable"):
            await self.change(CommandArgs)
        else:
            await self.view(CommandArgs)

    @Bloxlink.subcommand()
    async def view(self, CommandArgs):
        """view your available server add-ons"""

        response   = CommandArgs.response
        prefix     = CommandArgs.prefix
        guild      = CommandArgs.message.guild

        embed = Embed(title="Bloxlink Server Add-ons")
        embed.description = f"Use ``{prefix}addon change`` to enable/disable an add-on."

        available_addons = set()
        enabled_addons   = set()

        enabled_addons = (await get_enabled_addons(guild)).values()

        available_addons = [repr(x) for x in set(addons.values()).difference(enabled_addons)]
        enabled_addons   = [repr(x) for x in enabled_addons]

        if available_addons:
            embed.add_field(name="Available Add-ons", value="\n".join(available_addons), inline=False)
        else:
            embed.add_field(name="Available Add-ons", value="None", inline=False)

        if enabled_addons:
            embed.add_field(name="Enabled Add-ons", value="\n".join(enabled_addons), inline=False)
        else:
            embed.add_field(name="Enabled Add-ons", value="None", inline=False)

        await response.send(embed=embed)

    @Bloxlink.subcommand()
    async def change(self, CommandArgs):
        """change a server add-on"""

        response = CommandArgs.response
        prefix   = CommandArgs.prefix

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data
        guild_addons = guild_data.get("addons", {})

        toggleable_addons = [str(x) for x in filter(lambda x: getattr(x, 'toggleable', True), addons.values())]

        parsed_args = await CommandArgs.prompt([
            {
                "prompt": f"Please choose the add-on you would like to change: ``{toggleable_addons}``",
                "name": "addon_choice",
                "type": "choice",
                "choices": toggleable_addons,
                "formatting": False
            },
            {
                "prompt": "Would you like to **enable** or **disable** this add-on?",
                "name": "enable",
                "type": "choice",
                "choices": ["enable", "disable"]
            },
        ])

        addon_choice = parsed_args["addon_choice"]
        enable = parsed_args["enable"] == "enable"

        if enable and getattr(addons[addon_choice], "premium", False):
            donator_profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)

            if not donator_profile.features.get("premium"):
                raise Error(f"You must have premium in order to enable this add-on. Please use ``{prefix}donate`` "
                            "for instructions on donating.")


        guild_addons[addon_choice] = enable
        guild_data["addons"] = guild_addons

        await self.r.table("guilds").insert(guild_data, conflict="update").run()

        await set_guild_value(guild, "addons", guild_addons)

        await response.success(f"Successfully **{parsed_args['enable']}d** the add-on **{addon_choice}!**")
