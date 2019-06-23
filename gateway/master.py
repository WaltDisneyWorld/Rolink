import sys
import os
import asyncio
import logging
import json
import websockets
import aiohttp
import docker
import uuid
import aiodocker
import datetime
from async_timeout import timeout
from concurrent.futures._base import CancelledError
from structures.Cluster import Cluster # pylint: disable=E0611,import-error
from exceptions import ClusterException # pylint: disable=E0611,wrong-import-order

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.abspath(os.path.join(dir_path, os.pardir)))

from src.config import TOKEN, WEBHOOKS # pylint: disable=wrong-import-position


async_docker = aiodocker.Docker()
sync_docker  = docker.from_env()

loop = asyncio.get_event_loop()


logging.basicConfig(level=logging.INFO)

# websocket stuff
WEBSOCKET_PORT = int(os.environ.get("WEBSOCKET_PORT", 8765))
HOSTNAME = os.environ.get("HOSTNAME", "localhost")

# bloxlink specifications
RELEASE = os.environ.get("RELEASE", "LOCAL")
IMAGE = os.environ.get("CLUSTER_IMAGE", "rewrite:latest")
LABEL = os.environ.get("LABEL", "bloxlink")

# shard stuff
SHARDS_PER_CLUSTER = int(os.environ.get("SHARDS_PER_CLUSTER", 1))

WEBSOCKET_SECRET = str(uuid.uuid4())

clusters = []
pending = {}



async def get_shard_count():
	SHARD_COUNT = os.environ.get("SHARD_COUNT", 0)

	if SHARD_COUNT:
		return int(SHARD_COUNT)
	else:
		headers = {
			"Authorization": f"Bot {TOKEN}"
		}

		async with aiohttp.ClientSession().get("https://discordapp.com/api/v7/gateway/bot", headers=headers) as response:
			return (await response.json())["shards"]


async def start_cluster(network, session, cluster_id, shard_range, total_shard_count):
	print(f"Spawning a new cluster with shards: {shard_range}", flush=True)

	cluster = Cluster(cluster_id, shard_range, network=network, total_shard_count=total_shard_count, websocket_secret=WEBSOCKET_SECRET)
	clusters.append(cluster)

	try:
		await cluster.spawn()
	except ClusterException as e:
		webhook_data = {
			"username": "Cluster Manager",
			"embeds": [{
				"title": f"Cluster {cluster_id} died. Restarting.",
				"timestamp": datetime.datetime.now().isoformat(),
				"color": 13319470
			}]
		}
		if e.args:
			print(f"Cluster {cluster_id} died: {e}", flush=True)
			webhook_data["embeds"][0]["fields"] = [{"name": "Traceback", "value": str(e) }]
		else:
			print(f"Cluster {cluster_id} died.", flush=True)

		await session.post(WEBHOOKS["LOGS"], json=webhook_data)

		clusters.remove(cluster)

		await asyncio.sleep(20)
		await start_cluster(network, session, cluster_id, shard_range, total_shard_count)


async def start_clusters():
	last, i, cluster_id = 0, 0, -1
	tasks = []

	network = None

	session = aiohttp.ClientSession()

	try:
		network = await async_docker.networks.get("bloxlink-network")
	except aiodocker.exceptions.DockerError:
		network = await async_docker.networks.create({"Name": "bloxlink-network"})

	shard_count = await get_shard_count()

	while i <= shard_count:
		shard_range = list(range(last, i))
		last = i

		if (i + SHARDS_PER_CLUSTER > shard_count) and (shard_count % SHARDS_PER_CLUSTER) != 0:
			i = i + (shard_count % SHARDS_PER_CLUSTER)
		else:
			i += SHARDS_PER_CLUSTER

		if shard_range:
			# append cluster spawning task
			tasks.append(start_cluster(network, session, cluster_id, tuple(shard_range), shard_count))

		cluster_id += 1

	try:
		await session.post(WEBHOOKS["LOGS"], json={
			"username": "Cluster Manager",
			"embeds": [{
				"timestamp": datetime.datetime.now().isoformat(),
				"title": f"Starting {len(tasks)} cluster{'s' if len(tasks) > 1 else ''}",
				"color": 7506393,
			}]
		})
	except:
		print("MASTER | Failed to post starting clusters webhook", flush=True)

	await asyncio.wait(tasks) # spawn all clusters


async def cluster_timeout(future, websocket, message):
	nonce = message["nonce"]
	secret = message["secret"]

	async with timeout(15):
		try:
			await future

		except (asyncio.TimeoutError, CancelledError):
			pass

		finally:
			await websocket.send(json.dumps({
				"nonce": nonce,
				"secret": secret,
				"type": "RESULT",
				"data": pending[nonce]["results"]
			}))

			del pending[nonce]

async def websocket_connect(websocket, _):
	print("MASTER | New client connected", flush=True)

	session = aiohttp.ClientSession()

	async for message in websocket:
		try:
			message = json.loads(message)
		except json.JSONDecodeError:
			await websocket.send("Invalid JSON.")
			break

		nonce = message.get("nonce")
		secret = message.get("secret")

		if secret != WEBSOCKET_SECRET:
			await websocket.send("Invalid secret.")
			break
		elif not nonce:
			await websocket.send("Missing nonce.")
			break

		cluster_id = int(message.get("cluster_id", 0))
		cluster = clusters[cluster_id]

		if message.get("type"):
			if message["type"] == "IDENTIFY":
				cluster.websocket = websocket
			elif message["type"] == "READY":
				guilds = message["data"]["guilds"]
				users = message["data"]["users"]

				if len(cluster.shards) > 1:
					shard_desc = f"{min(cluster.shards)}-{max(cluster.shards)}"
				else:
					shard_desc = cluster.shards[0]

				try:
					await session.post(WEBHOOKS["LOGS"], json={
						"username": "Cluster Manager",
						"embeds": [{
							"title": f"Cluster {cluster_id} connected",
							"timestamp": datetime.datetime.now().isoformat(),
							"color": 3066737,
							"description": "All shards have successfully connected to the gateway.",
							"fields": [{"name": "Statistics", "value": f"**Shards:** {shard_desc}\n**Guilds:** {guilds}\n**Users:** {users}"}]

						}]
					})
				except:
					print("MASTER | Failed to post log webhook", flush=True)

			elif message["type"] == "EVAL":
				if message.get("data"):
					future = loop.create_future()
					to_eval = message.get("data")
					pending[nonce] = {"results": {x:"cluster timeout" if y.websocket else "cluster offline" for x,y in enumerate(clusters)}, "future": future}

					await asyncio.wait([cluster.websocket.send(json.dumps({
						"nonce": nonce,
						"secret": secret,
						"type": "EVAL",
						"data": to_eval,
						"parent": cluster_id
					})) for cluster in clusters if cluster.websocket])

					loop.create_task(cluster_timeout(future, websocket, message))

			elif message["type"] == "RESULT":
				if pending.get(nonce) is not None:
					future = pending[nonce]["future"]
					pending[nonce]["results"][cluster_id] = message.get("data")

					num_completed = 0
					num_all = 0
					for cluster_id, cluster_response in pending.get(nonce, {}).get("results", {}).items():
						if cluster_response != "cluster offline":
							num_all += 1
						if cluster_response not in ("cluster offline", "cluster timeout"):
							num_completed += 1

					if num_completed == num_all:
						future.set_result(True)

	await session.close()




if __name__ == '__main__':
	try:
		loop.run_until_complete(websockets.serve(websocket_connect, '0.0.0.0', 8765))
		loop.run_until_complete(start_clusters())
	finally:
		loop.run_until_complete(async_docker.session.close())
		loop.close()
