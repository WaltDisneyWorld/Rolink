import math
from resources.structures.Bloxlink import Bloxlink
from discord import Embed
from config import IS_DOCKER
from time import time
from resources.constants import VERSION, SHARD_RANGE, CLUSTER_ID, STARTED
from psutil import Process
from os import getpid

broadcast = Bloxlink.get_module("ipc", attrs="broadcast")




@Bloxlink.command
class StatsCommand(Bloxlink.Module):
    """view the current stats of Bloxlink"""

    def __init__(self):
        pass


    async def __main__(self, CommandArgs):
        response = CommandArgs.response

        embed = Embed(description="Showing stats for all clusters")
        embed.set_author(name=Bloxlink.user.name, icon_url=Bloxlink.user.avatar_url)

        if IS_DOCKER:
            guilds = 0
            users = 0
            mem = 0
            errored = 0

            stats = await broadcast(type="STATS")

            for cluster_id, cluster_data in stats.items():
                if cluster_data in ("cluster offline", "cluster timeout"):
                    errored += 1
                else:
                    guilds += cluster_data[0]
                    users += cluster_data[1]
                    mem += cluster_data[2]

            if errored:
                guilds = f"{guilds} ({len(self.client.guilds)}) ({errored} errored)"
                users = f"{users} ({len(self.client.users)}) ({errored} errored)"
            else:
                guilds = f"{guilds} ({len(self.client.guilds)})"
                users = f"{users} ({len(self.client.users)})"

        else:
            guilds = str(len(self.client.guilds))
            users = str(len(self.client.users))

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


        embed.add_field(name="Version", value=VERSION)
        embed.add_field(name="Cluster", value=CLUSTER_ID)
        embed.add_field(name="Shards", value=SHARD_RANGE)
        embed.add_field(name="Servers", value=guilds)
        embed.add_field(name="Cached Users", value=users)
        embed.add_field(name="Uptime", value=uptime)
        embed.add_field(name="Memory Usage", value=f"{mem} MB")

        embed.add_field(name="Invite Bloxlink", value=f"https://blox.link/invite")
        embed.add_field(name="Website", value=f"https://blox.link")


        await response.send(embed=embed)
