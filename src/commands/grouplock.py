from resources.structures.Bloxlink import Bloxlink  # pylint: disable=import-error
from resources.exceptions import PermissionError, Error, RobloxNotFound, Message  # pylint: disable=import-error
from resources.constants import BROWN_COLOR # pylint: disable=import-error
from discord import Embed, Object
import re


post_event = Bloxlink.get_module("utils", attrs=["post_event"])
get_group = Bloxlink.get_module("roblox", attrs=["get_group"])
get_features = Bloxlink.get_module("premium", attrs=["get_features"])

roblox_group_regex = re.compile(r"roblox.com/groups/(\d+)/")


@Bloxlink.command
class GroupLockCommand(Bloxlink.Module):
    """lock your server to group members"""


    @staticmethod
    async def validate_group(message, content):
        regex_search = roblox_group_regex.search(content)

        if regex_search:
            group_id = regex_search.group(1)
        else:
            group_id = content

        try:
            group = await get_group(group_id)
        except RobloxNotFound:
            return None, "No group was found with this ID. Please try again."

        return group

    def __init__(self):
        self.arguments = [
            {
                "prompt": "This command will kick people who join your server and aren't in these groups. They must be in __ALL__ of these groups.\n"
                          "Would you like to **add** a new group, **delete** a group, or **view** your current groups?",
                "name": "choice",
                "type": "choice",
                "choices": ["add", "delete", "view"]
            }
        ]

        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"


    async def __main__(self, CommandArgs):
        choice = CommandArgs.parsed_args["choice"]
        guild_data = CommandArgs.guild_data
        groups = CommandArgs.guild_data.get("groupLock", {})
        guild = CommandArgs.message.guild
        author = CommandArgs.message.author
        prefix = CommandArgs.prefix
        response = CommandArgs.response

        if choice == "add":
            args = await CommandArgs.prompt([
                {
                    "prompt": "Please specify either the **Group ID** or **Group URL** that you would like "
                              "to set as a requirement for new joiners.",
                    "name": "group",
                    "validation": self.validate_group
                },
                {
                    "prompt": "Would you like people who are kicked to receive a custom DM? Please specify either ``yes`` or ``no``.\n\n"
                              "Note that Unverified users will receive a different DM on instructions to linking to Bloxlink.",
                    "name": "dm_enabled",
                    "type": "choice",
                    "choices": ["yes", "no"]
                }
            ])

            group = args["group"]
            dm_enabled = args["dm_enabled"] == "yes"

            if len(groups) >= 15:
                raise Message("15 groups is the max you can add to your group-lock! Please delete some before adding any more.", type="silly")

            profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)

            if len(groups) >= 3 and not profile.features.get("premium"):
                raise Message("If you would like to add more than **3** groups to your group-lock, then you need Bloxlink Premium.\n"
                              f"Please use ``{prefix}donate`` for instructions on receiving Bloxlink Premium.\n"
                              "Bloxlink Premium members may lock their server with up to **15** groups.", type="silly")

            if dm_enabled:
                dm_message = (await CommandArgs.prompt([{
                    "prompt": "Please specify the text of the DM that people who are kicked will receive. A recommendation "
                              "is to provide your Group Link and any other instructions for them.",
                    "name": "dm_message",
                    "max": 1500
                }]))["dm_message"]
            else:
                dm_message = None

            groups[group.group_id] = {"groupName": group.name, "dmMessage": dm_message}

            await self.r.table("guilds").insert({
                "id": str(guild.id),
                "groupLock": groups
            }, conflict="update").run()

            await post_event(guild, guild_data, "configuration", f"{author.mention} has **added** a group to the ``server-lock``.", BROWN_COLOR)

            await response.success(f"Successfully added group **{group.name}** to your Server-Lock!")


        elif choice == "delete":
            group = (await CommandArgs.prompt([
                {
                    "prompt": "Please specify either the **Group URL** or **Group ID** to delete.",
                    "name": "group",
                    "validation": self.validate_group
                }
            ]))["group"]

            if not groups.get(group.group_id):
                raise Message("This group isn't in your server-lock!")

            del groups[group.group_id]
            guild_data["groupLock"] = groups

            if groups:
                await self.r.table("guilds").insert(guild_data, conflict="replace").run()
            else:
                guild_data.pop("groupLock")

                await self.r.table("guilds").insert(guild_data, conflict="replace").run()

            await post_event(guild, guild_data, "configuration", f"{author.mention} has **deleted** a group from the ``server-lock``.", BROWN_COLOR)

            await response.success("Successfully **deleted** your group from the Server-Lock!")


        elif choice == "view":
            if not groups:
                raise Message("You have no groups added to your Server-Lock!", type="silly")

            embed = Embed(title="Bloxlink Server-Lock")
            embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)
            embed.set_author(name=guild.name, icon_url=guild.icon_url)

            for group_id, data in groups.items():
                embed.add_field(name=f"{data['groupName']} ({group_id})", value=data["dmMessage"], inline=False)

            await response.send(embed=embed)
