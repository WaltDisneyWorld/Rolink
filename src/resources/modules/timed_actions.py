from ..structures.Bloxlink import Bloxlink
from ..exceptions import RobloxNotFound
import asyncio
import dateutil
from discord.errors import Forbidden, NotFound
from discord import Embed, AllowedMentions

coro_async = Bloxlink.get_module("utils", attrs=["coro_async"])
get_group, get_user = Bloxlink.get_module("roblox", attrs=["get_group", "get_user"])


@Bloxlink.module
class TimedActions(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):
        await Bloxlink.wait_until_ready()
        #self.loop.run_in_executor(None, coro_async, self.group_shouts) # ugly, but necessary ? if we need more coros which may potentially be blocking
        await self.group_shouts()

    async def group_shouts(self):
        conn = await Bloxlink.load_database()

        while True:
            group_shouts = await self.r.db("canary").table("groupShouts").run(conn)

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

                            await self.r.db("canary").table("groupShouts").get(guild_id).update(shout_data).run()

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
                                    await self.r.db("canary").table("groupShouts").get(guild_id).delete().run()

                                    guild_data = await self.r.db("canary").table("guilds").get(guild_id).run() or {"id": guild_id}
                                    guild_data.pop("groupShoutChannel", None)

                                    await self.r.db("canary").table("guilds").insert(guild_data, conflict="replace").run()

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
                                        await self.r.db("canary").table("groupShouts").get(guild_id).delete().run()

                                        guild_data = await self.r.db("canary").table("guilds").get(guild_id).run() or {"id": guild_id}
                                        guild_data.pop("groupShoutChannel", None)

                                        await self.r.db("canary").table("guilds").insert(guild_data, conflict="replace").run()


            await asyncio.sleep(5 * 60)
