from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from importlib import import_module

get_files = Bloxlink.get_module("utils", attrs="get_files")
get_guild_value = Bloxlink.get_module("cache", attrs=["get_guild_value"])

@Bloxlink.module
class AddonsM(Bloxlink.Module):
    def __init__(self):
        self.addons = {}

    async def __setup__(self):
        self.new_command = Bloxlink.get_module("commands", attrs=["new_command"])
        self.load_addons()

    def load_addons(self):
        addon_categories = [f.replace(".py", "") for f in get_files("src/addons/")]

        for addon_category in addon_categories:
            addon_commands = [f.replace(".py", "") for f in get_files(f"src/addons/{addon_category}") if f != "__init__.py"]

            addon_category_structure = None
            command_structure = None

            addon_category_module = import_module(f"addons.{addon_category}")

            for attr_name in dir(addon_category_module):
                if "Addon" in attr_name and not "Command" in attr_name:
                    addon_category_structure = getattr(addon_category_module, attr_name)()

                    self.addons[str(addon_category_structure)] = addon_category_structure

                    for command in addon_commands:
                        addon_command_module = import_module(f"addons.{addon_category}.{command}")

                        for attr_name in dir(addon_command_module):
                            if "Command" in attr_name and hasattr(getattr(addon_command_module, attr_name), "__main__"): # it's probably a command tbh, should have a better system to check tho
                                command_structure = getattr(addon_command_module, attr_name)

                                self.new_command(command_structure, addon=addon_category_structure)

    async def get_addons(self, guild):
        guild_addons = await get_guild_value(guild, "addons")

        return guild_addons and {x:y for x,y in guild_addons.items() if x in self.addons}

    async def get_enabled_addons(self, guild):
        guild_addons   = await get_guild_value(guild, "addons") or {}
        enabled_addons = {}

        for addon, val in guild_addons.items():
            if val:
                enabled_addons[addon] = self.addons.get(addon)

        for addon in self.addons.values():
            if getattr(addon, "default_enabled", False) and not getattr(addon, "toggleable", True):
                enabled_addons[str(addon)] = addon

        return enabled_addons
