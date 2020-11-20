from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..exceptions import RobloxNotFound # pylint: disable=import-error
from ..constants import CACHE_CLEAR # pylint: disable=import-error
import asyncio
import dateutil
from discord.errors import Forbidden, NotFound
from discord import Embed, AllowedMentions

coro_async = Bloxlink.get_module("utils", attrs=["coro_async"])
get_group, get_user = Bloxlink.get_module("roblox", attrs=["get_group", "get_user"])
cache_clear, cache_get = Bloxlink.get_module("cache", attrs=["clear", "get"])
load_partners = Bloxlink.get_module("partners", attrs=["load_data"])
load_blacklist = Bloxlink.get_module("blacklist", attrs=["load_blacklist"])
load_boosters = Bloxlink.get_module("nitro_boosters", attrs=["load_boosters"], name_override="NitroBoosters")
load_staff_members = Bloxlink.get_module("premium", attrs=["load_staff_members"])


@Bloxlink.module
class TimedActions(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):
        await Bloxlink.wait_until_ready()
        #self.loop.run_in_executor(None, coro_async, self.group_shouts) # ugly, but necessary ? if we need more coros which may potentially be blocking
        #await self.group_shouts()
        await self.timed_actions()


    async def timed_actions(self):
        while True:
            await cache_clear("partners")

            try:
                await load_partners()
                await load_blacklist() # redis
                await load_boosters() # redis
                await load_staff_members() # redis
            except BaseException as e:
                Bloxlink.error(e)

            await asyncio.sleep(CACHE_CLEAR * 60)

    async def group_shouts(self):
        conn = await Bloxlink.load_database()
        group_shouts = await self.r.table("groupShouts").run(conn)

        async for shout_data in group_shouts:
            guild_id = shout_data["id"]
            channel_id = int(shout_data["channel"])

            guild = Bloxlink.get_guild(int(shout_data["id"]))

            if guild:
                channel = guild.get_channel(channel_id)

                if channel:
                    try:
                        group = await get_group(shout_data["group"], with_shout=True)
                    except RobloxNotFound:
                        continue

                    shout = group.shout

                    if not shout:
                        continue

                    datetime = dateutil.parser.parse(shout["updated"])
                    shout_text = shout["body"].strip()

                    if shout_text and shout_data.get("lastShout", "") != shout_text:
                        shout_data["lastShout"] = shout_text

                        await self.r.table("groupShouts").get(guild_id).update(shout_data).run()

                        if shout_data.get("default"):
                            embed = Embed(
                                title="Group Shout",
                                description=f'Shouted by: {shout["poster"]["username"]}',
                                timestamp=datetime
                            )

                            embed.set_author(
                                name=group.name,
                                icon_url=group.emblem_url,
                                url=group.url
                            )

                            embed.add_field(name="Shout:", value=shout_text)

                            try:
                                await channel.send(content=shout_data.get("prependContent"), embed=embed, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=True))
                            except Forbidden:
                                pass
                            except NotFound:
                                await self.r.table("groupShouts").get(guild_id).delete().run()

                                guild_data = await self.r.table("guilds").get(guild_id).run() or {"id": guild_id}
                                guild_data.pop("groupShoutChannel", None)

                                await self.r.table("guilds").insert(guild_data, conflict="replace").run()

                        else:
                            shout_format = shout_data.get("format", "")

                            if "{group-rank}" in shout_format:
                                user, _ = await get_user(roblox_id=shout["poster"]["userId"])
                                user_group = user.groups.get(group.group_id)

                                if user_group:
                                    group_rank = user_group.user_rank_name
                                else:
                                    group_rank = "Guest"
                            else:
                                group_rank = "Guest"

                            if shout_text:
                                shout_text = shout_format.replace(
                                    "{group-name}", group.name
                                ).replace(
                                    "{group-shout}", shout_text
                                ).replace(
                                    "{group-id}", group.group_id
                                ).replace(
                                    "{roblox-name}", shout["poster"]["username"]
                                ).replace(
                                    "{roblox-id}", str(shout["poster"]["userId"])
                                ).replace(
                                    "{group-rank}", group_rank
                                )

                                if shout_data.get("cleanContent"):
                                    allowed_mentions = AllowedMentions(users=False, everyone=False, roles=False)
                                else:
                                    allowed_mentions = AllowedMentions(users=True, everyone=True, roles=True)

                                try:
                                    await channel.send(shout_text, allowed_mentions=allowed_mentions)
                                except Forbidden:
                                    pass
                                except NotFound:
                                    await self.r.table("groupShouts").get(guild_id).delete().run()

                                    guild_data = await self.r.table("guilds").get(guild_id).run() or {"id": guild_id}
                                    guild_data.pop("groupShoutChannel", None)

                                    await self.r.table("guilds").insert(guild_data, conflict="replace").run()
