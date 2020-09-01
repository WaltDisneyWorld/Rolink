from os import getpid
import json
import uuid
import asyncio
from discord import Status, Game, Streaming
from ..structures.Bloxlink import Bloxlink
from ..constants import CLUSTER_ID, SHARD_RANGE, STARTED, IS_DOCKER, PLAYING_STATUS
from config import PROMPT, PREFIX # pylint: disable=import-error, no-name-in-module
from time import time
from math import floor
from os import environ as env
from psutil import Process
import async_timeout

eval = Bloxlink.get_module("evalm", attrs="__call__")




@Bloxlink.module
class IPC(Bloxlink.Module):
    def __init__(self):
        self.pending_tasks = {}
        self.clusters = set()

    async def handle_message(self, message):
        message = json.loads(str(message["data"], "utf-8"))

        data = message["data"]
        type = message["type"]
        nonce = message["nonce"]
        original_cluster = message["original_cluster"]
        waiting_for = message["waiting_for"]
        cluster_id = message["cluster_id"]
        extras = message.get("extras", {})

        if type == "IDENTIFY":
            # we're syncing this cluster with ourselves, and send back our clusters
            if original_cluster == CLUSTER_ID:
                if isinstance(data, int):
                    self.clusters.add(data)
                else:
                    for x in data:
                        self.clusters.add(x)
            else:
                self.clusters.add(original_cluster)

                data = json.dumps({
                    "nonce": None,
                    "cluster_id": CLUSTER_ID,
                    "data": list(self.clusters),
                    "type": "IDENTIFY",
                    "original_cluster": original_cluster,
                    "waiting_for": waiting_for
                })

                await self.redis.publish(f"CLUSTER_{original_cluster}", data)

        elif type == "EVAL":
            res = (await eval(data, codeblock=False)).description

            data = json.dumps({
                "nonce": nonce,
                "cluster_id": CLUSTER_ID,
                "data": res,
                "type": "CLIENT_RESULT",
                "original_cluster": original_cluster,
                "waiting_for": waiting_for
            })

            await self.redis.publish(f"CLUSTER_{original_cluster}", data)

        elif type == "CLIENT_RESULT":
            task = self.pending_tasks.get(nonce)

            if task:
                task[1][cluster_id] = data
                task[2] += 1
                waiting_for = message["waiting_for"] or len(self.clusters)

                if task[2] == waiting_for:
                    task[0].set_result(True)

        elif type == "DM":
            if 0 in SHARD_RANGE:
                try:
                    message_ = await Bloxlink.wait_for("message", check=lambda m: m.author.id == data and not m.guild, timeout=PROMPT["PROMPT_TIMEOUT"])
                except asyncio.TimeoutError:
                    message_ = "cancel (timeout)"

                data = json.dumps({
                    "nonce": nonce,
                    "cluster_id": CLUSTER_ID,
                    "data": getattr(message_, "content", message_),
                    "type": "CLIENT_RESULT",
                    "original_cluster": original_cluster,
                    "waiting_for": waiting_for
                })

                await self.redis.publish(f"CLUSTER_{original_cluster}", data)

        elif type == "STATS":
            seconds = floor(time() - STARTED)

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

            process = Process(getpid())
            mem = floor(process.memory_info()[0] / float(2 ** 20))

            data = json.dumps({
                "nonce": nonce,
                "cluster_id": CLUSTER_ID,
                "data": (len(self.client.guilds), len(self.client.users), mem, uptime),
                "type": "CLIENT_RESULT",
                "original_cluster": original_cluster,
                "waiting_for": waiting_for
            })

            await self.redis.publish(f"CLUSTER_{original_cluster}", data)

        elif type == "PLAYING_STATUS":
            presence_type = extras.get("presence_type", "normal")
            playing_status = extras.get("status", PLAYING_STATUS).format(prefix=PREFIX)

            if presence_type == "normal":
                await Bloxlink.change_presence(status=Status.online, activity=Game(playing_status))
            elif presence_type == "streaming":
                stream_url = extras.get("stream_url", "https://twitch.tv/blox_link")

                await Bloxlink.change_presence(activity=Streaming(name=playing_status, url=stream_url))

            data = json.dumps({
                "nonce": nonce,
                "cluster_id": CLUSTER_ID,
                "data": True,
                "type": "CLIENT_RESULT",
                "original_cluster": original_cluster,
                "waiting_for": waiting_for
            })

            await self.redis.publish(f"CLUSTER_{original_cluster}", data)


    async def __setup__(self):
        if IS_DOCKER:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe("GLOBAL", f"CLUSTER_{CLUSTER_ID}")

            data = json.dumps({
                "nonce": None,
                "cluster_id": CLUSTER_ID,
                "data": CLUSTER_ID,
                "type": "IDENTIFY",
                "original_cluster": CLUSTER_ID,
                "waiting_for": None
            })

            await self.redis.publish("GLOBAL", data)

            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)

                if message:
                    self.loop.create_task(self.handle_message(message))


    async def broadcast(self, message, type, send_to="GLOBAL", waiting_for=None, timeout=10, response=True, **kwargs):
        nonce = str(uuid.uuid4())

        if waiting_for and isinstance(waiting_for, str):
            waiting_for = int(waiting_for)

        future = self.loop.create_future()
        self.pending_tasks[nonce] = [future, {x:"cluster timeout" for x in self.clusters}, 0]

        data = json.dumps({
            "nonce": response and nonce,
            "data": message,
            "type": type,
            "original_cluster": CLUSTER_ID,
            "cluster_id": CLUSTER_ID,
            "waiting_for": waiting_for,
            "extras": kwargs
        })


        await self.redis.publish(send_to, data)

        if response:
            try:
                async with async_timeout.timeout(timeout):
                    await future
            except asyncio.TimeoutError:
                pass

            result = self.pending_tasks[nonce][1]
            self.pending_tasks[nonce] = None

            return result
        else:
            self.pending_tasks[nonce] = None # this is necessary to prevent any race conditions
