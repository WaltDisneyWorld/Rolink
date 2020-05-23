from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from discord import Embed
from importlib import import_module

get_files = Bloxlink.get_module("utils", attrs="get_files")


@Bloxlink.command
class AddonsCommand(Bloxlink.Module):
    """enable/disable a server add-on"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.aliases = ["addon"]
        self.hidden = True

        self.addons = {}

        self.load_addons()

    async def __main__(self, CommandArgs):
        pass

    @Bloxlink.subcommand()
    async def view(self, CommandArgs):
        """view your available server add-ons"""

        response = CommandArgs.response
        prefix = CommandArgs.prefix
        guild_data = CommandArgs.guild_data

        embed = Embed(title="Bloxlink Server Add-ons")
        embed.description = f"Use ``{prefix}addon change`` to enable/disable an add-on."

        guild_addons = guild_data.get("addons", {})

        available_addons = set()
        enabled_addons = set()

        for addon, val in guild_addons.items():
            if val:
                enabled_addons.add(self.addons.get(addon))

        available_addons = [str(x) for x in set(self.addons.values()).difference(enabled_addons)]
        enabled_addons = [str(x) for x in enabled_addons]


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

        guild_data = CommandArgs.guild_data
        addons = guild_data.get("addons", {})

        parsed_args = await CommandArgs.prompt([
            {
                "prompt": f"Please choose the add-on you would like to change: ``{list(self.addons.keys())}``",
                "name": "addon_choice",
                "type": "choice",
                "choices": self.addons.keys(),
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

        addons[addon_choice] = enable
        guild_data["addons"] = addons

        await self.r.db("canary").table("guilds").insert(guild_data, conflict="update").run()

        await response.success(f"Successfully **{parsed_args['enable']}d** the add-on **{addon_choice}!**")


    def load_addons(self):
        addon_files = [f.replace(".py", "") for f in get_files("src/addons/")]

        for addon in addon_files:
            import_name = f"addons.{addon}"

            addon_mod = import_module(import_name)

            for attr in dir(addon_mod):
                if "Addon" in attr:
                    mod = getattr(addon_mod, attr)

                    if callable(mod):
                        self.addons[addon] = mod()
