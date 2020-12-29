import math
from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import VERSION, SHARD_RANGE, CLUSTER_ID, STARTED, IS_DOCKER, RELEASE # pylint: disable=import-error
from discord import Embed
from time import time
from psutil import Process
from os import getpid

broadcast = Bloxlink.get_module("ipc", attrs="broadcast")





@Bloxlink.command
class StatsCommand(Bloxlink.Module):
    """view the current stats of Bloxlink"""

    def __init__(self):
        self.aliases = ["statistics", "nerdinfo"]
        self.dm_allowed = True

        if len(SHARD_RANGE) > 1:
            self.shard_range = f"[{SHARD_RANGE[0]}-{SHARD_RANGE[len(SHARD_RANGE)-1]}]"
        else:
            self.shard_range = SHARD_RANGE

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        clusters = 0

        if IS_DOCKER:
            total_guilds = guilds = 0
            mem = 0
            errored = 0

            stats = await broadcast(None, type="STATS")
            clusters = len(stats)

            for cluster_id, cluster_data in stats.items():
                if cluster_data in ("cluster offline", "cluster timeout"):
                    errored += 1
                else:
                    total_guilds += cluster_data[0]
                    mem += cluster_data[1]

            if errored:
                guilds = f"{total_guilds} ({len(self.client.guilds)}) ({errored} errored)"
            else:
                guilds = f"{total_guilds} ({len(self.client.guilds)})"

        else:
            total_guilds = guilds = str(len(self.client.guilds))
            clusters = 1

            process = Process(getpid())
            mem = math.floor(process.memory_info()[0] / float(2 ** 20))


        seconds = math.floor(time() - STARTED)

        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        days, hours, minutes, seconds = None, None, None, None

        if d:
            days = f"{d}d"
        if h:
            hours = f"{h}h"
        if m:
            minutes = f"{m}m"
        if s:
            seconds = f"{s}s"

        uptime = f"{days or ''} {hours or ''} {minutes or ''} {seconds or ''}".strip()

        embed = Embed(description=f"Showing collective stats from **{clusters}** clusters")
        embed.set_author(name=Bloxlink.user.name, icon_url=Bloxlink.user.avatar_url)

        embed.add_field(name="Version", value=VERSION)
        embed.add_field(name="Cluster", value=CLUSTER_ID)
        embed.add_field(name="Shards", value=self.shard_range)
        embed.add_field(name="Servers", value=guilds)
        embed.add_field(name="Uptime", value=uptime)
        embed.add_field(name="Memory Usage", value=f"{mem} MB")

        embed.add_field(name="Invite **Bloxlink**", value=f"https://blox.link/invite")
        embed.add_field(name="Website", value=f"https://blox.link")

        await response.send(embed=embed)

        if IS_DOCKER and RELEASE == "MAIN":
            await self.r.table("miscellaneous").insert({
                "id": "stats",
                "stats": {
                    "guilds": total_guilds,
                    "version": VERSION,
                    "memory": mem,
                    "uptime": uptime,
                    "clusters": clusters
                }

            }, conflict="update").run()
