import sys
import os
import asyncio
import logging
import websockets
import aiohttp
import docker
import json
import uuid
import aiodocker
from structures.Cluster import Cluster # pylint: disable=E0611,import-error
from exceptions import ClusterException # pylint: disable=E0611,wrong-import-order
from async_timeout import timeout
from concurrent.futures._base import CancelledError

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.abspath(os.path.join(dir_path, os.pardir)))

from src.config import TOKEN # pylint: disable=wrong-import-position


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

WEBSOCKET_AUTH = str(uuid.uuid4())

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


async def start_cluster(network, cluster_id, shard_range, total_shard_count):
	print(f"Spawning a new cluster with shards: {shard_range}", flush=True)

	cluster = Cluster(cluster_id, shard_range, network=network, total_shard_count=total_shard_count, websocket_auth=WEBSOCKET_AUTH)
	clusters.append(cluster)

	try:
		await cluster.spawn()
	except ClusterException as e:
		if e.args:
			print(f"Cluster {cluster_id} died: {e}", flush=True)
		else:
			print(f"Cluster {cluster_id} died.", flush=True)

		clusters.remove(cluster)

		await asyncio.sleep(20)
		await start_cluster(network, cluster_id, shard_range, total_shard_count)


async def start_clusters():
	last, i, cluster_id = 0, 0, -1
	tasks = []

	network = None

	try:
		network = await async_docker.networks.get("bloxlink-network")
	except aiodocker.exceptions.DockerError as e:
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
			tasks.append(start_cluster(network, cluster_id, tuple(shard_range), shard_count))

		cluster_id += 1

	await asyncio.wait(tasks) # spawn all clusters


async def cluster_timeout(future, websocket, message):
	nonce = message["nonce"]
	auth = message["auth"]

	async with timeout(15):
		try:
			await future

		except (asyncio.TimeoutError, CancelledError):
			pass

		finally:
			await websocket.send(json.dumps({
				"nonce": nonce,
				"auth": auth,
				"type": "RESULT",
				"data": pending[nonce]["results"]
			}))

			del pending[nonce]

async def websocket_connect(websocket, path):
	print("MASTER | New client connected", flush=True)

	async for message in websocket:
		try:
			message = json.loads(message)
		except json.JSONDecodeError:
			await websocket.send("Invalid JSON.")
			break

		nonce = message.get("nonce")
		auth = message.get("auth")

		if auth != WEBSOCKET_AUTH:
			await websocket.send("Invalid authorization.")
			break
		elif not nonce:
			await websocket.send("Missing nonce.")
			break

		cluster_id = int(message.get("cluster_id", 0))

		if message.get("type"):
			if message["type"] == "IDENTIFY":
				clusters[cluster_id].websocket = websocket
			elif message["type"] == "EVAL":
				if message.get("data"):
					future = loop.create_future()
					to_eval = message.get("data")
					pending[nonce] = {"results": {x:"cluster timeout" if y.websocket else "cluster offline" for x,y in enumerate(clusters)}, "future": future}

					await asyncio.wait([cluster.websocket.send(json.dumps({
						"nonce": nonce,
						"auth": auth,
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





if __name__ == '__main__':
	try:
		loop.run_until_complete(websockets.serve(websocket_connect, '0.0.0.0', 8765))
		loop.run_until_complete(start_clusters())
	finally:
		loop.run_until_complete(async_docker.session.close())
		loop.close()
