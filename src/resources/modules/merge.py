from ..structures import Bloxlink
from ..exceptions import RobloxAPIError, RobloxDown, RobloxNotFound, Message


get_group = Bloxlink.get_module("roblox", attrs="get_group")


@Bloxlink.module
class Merge(Bloxlink.Module):
    """testing code to convert 2.0 data to 3.0 compatible data

    This will be here for a few months to filter against servers that don't use Bloxlink anymore.

    """

    def __init__(self):
        self.processed_guilds = {}

    async def transform_guild_data(self, guild_data):
        if guild_data.get("merged"):
            return

        primary_group = str(guild_data.get("groupID", ""))
        changed = False

        if primary_group:
            changed = True
            try:
                group = await get_group(primary_group)
            except (RobloxNotFound, RobloxAPIError):
                group_name = None
            else:
                group_name = group.name

            if group_name:
                guild_data["groupIDs"] = {}
                guild_data["groupIDs"][primary_group] = {"nickname": None, "groupName": group_name}

            guild_data.pop("groupID")

        if guild_data.get("roleBinds"):
            guild_data["roleBinds"]["groups"] = guild_data["roleBinds"].get("groups") or {}

            for bind_id, bind_data in dict(guild_data["roleBinds"]).items():
                if bind_id.isdigit():
                    changed = True
                    guild_data["roleBinds"]["groups"][bind_id] = guild_data["roleBinds"]["groups"].get(bind_id) or {}
                    guild_data["roleBinds"]["groups"][bind_id]["binds"] = bind_data
                    guild_data["roleBinds"].pop(bind_id)
                elif bind_id == "virtualGroups":
                    changed = True
                    for vg_name, vg_binds in dict(bind_data).items():
                        if vg_name == "assetBind":
                            #guild_data["roleBinds"]["assets"] = guild_data["roleBinds"].get("assets", {})
                            if vg_binds.get("moreData"):

                                for vg_id, vg_data in dict(vg_binds["moreData"]).items():
                                    vg_type = vg_data.get("type")
                                    if vg_type == "Asset":
                                        guild_data["roleBinds"]["assets"] = guild_data["roleBinds"].get("assets", {})
                                        guild_data["roleBinds"]["assets"][vg_id] = {
                                            "roles": vg_data["roles"],
                                            "nickname": None,
                                            "displayName": None # TODO: get displayName
                                        }
                                    elif vg_type == "GamePass":
                                        guild_data["roleBinds"]["gamePasses"] = guild_data["roleBinds"].get("gamePasses", {})
                                        guild_data["roleBinds"]["gamePasses"][vg_id] = {
                                            "roles": vg_data["roles"],
                                            "nickname": None,
                                            "displayName": None # TODO: get displayName
                                        }
                                    elif vg_type == "Badge":
                                        guild_data["roleBinds"]["badges"] = guild_data["roleBinds"].get("badges", {})
                                        guild_data["roleBinds"]["badges"][vg_id] = {
                                            "roles": vg_data["roles"],
                                            "nickname": None,
                                            "displayName": None # TODO: get displayName
                                        }

                        guild_data["roleBinds"]["virtualGroups"].pop(vg_name)


                    guild_data["roleBinds"].pop(bind_id)

                elif bind_id == "groups":
                    for group_id, group_data in dict(bind_data).items():
                        for rank_id, rank_data in dict(group_data.get("binds", {})).items():
                            if isinstance(rank_data, str):
                                changed = True
                                rank_data = {
                                    "nickname": None,
                                    "roles": [rank_data]
                                }
                                guild_data["roleBinds"]["groups"][group_id]["binds"][rank_id] = rank_data
                            else:
                                for role_id in rank_data.get("roles", []):
                                    if not isinstance(role_id, str):
                                        changed = True
                                        guild_data["roleBinds"]["groups"][group_id]["binds"].pop(rank_id)
                                        break

        if guild_data.get("joinDM"):
            changed = True
            guild_data["verifiedDM"] = guild_data.get("welcomeMessage", "Welcome to **{server-name}**, {roblox-name}!")
            guild_data.pop("joinDM")

        if guild_data.get("groupLocked") is not None:
            changed = True
            if guild_data["groupLocked"]:
                if primary_group:
                    try:
                        group = await get_group(primary_group)
                    except RobloxNotFound:
                        group_name = None
                    else:
                        group_name = group.name

                    if group_name:
                        guild_data["groupLock"] = {
                            primary_group: {"groupName": group_name, "dmMessage": f"You were kicked for not being in the linked group: <https://www.roblox.com/groups/{primary_group}/->."}
                        }

            guild_data.pop("groupLocked", None)


        if guild_data.get("customBot"):
            changed = True
            if guild_data["customBot"].get("enabled") is False:
                guild_data.pop("customBot", None)
            else:
                guild_data["customBot"].pop("enabled", None)

        if guild_data.get("owner"):
            changed = True
            guild_data.pop("actualId", None)
            guild_data.pop("lastDataRefresh", None)
            guild_data.pop("owner", None)
            guild_data.pop("name", None)
            guild_data.pop("removed", None)
            guild_data.pop("memberCount", None)

        if guild_data.get("groupShout"):
            changed = True
            guild_data.pop("groupShout", None)

        if not guild_data.get("merged"):
            guild_data["merged"] = True
            changed = True

        if changed:
            await self.r.db("bloxlink").table("guilds").insert(guild_data, conflict="replace").run()


    async def merge(self, guild, guild_data):
        await self.transform_guild_data(guild_data)
