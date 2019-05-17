import sys
import os
import asyncio
import logging
import websockets
import aiohttp
import docker
import aiodocker
from structures.Cluster import Cluster # pylint: disable=E0611,import-error
from exceptions import ClusterException # pylint: disable=E0611,wrong-import-order

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.abspath(os.path.join(dir_path, os.pardir)))

from src.config import TOKEN # pylint: disable=wrong-import-position


async_docker = aiodocker.Docker()
sync_docker  = docker.from_env()


logging.basicConfig(level=logging.INFO)

# websocket stuff
WEBSOCKET_PORT = int(os.environ.get("WEBSOCKET_PORT", 8765))
HOSTNAME = os.environ.get("HOSTNAME", "localhost")

# bloxlink specifications
RELEASE = os.environ.get("RELEASE", "LOCAL")
IMAGE = os.environ.get("CLUSTER_IMAGE", "rewrite:latest")
LABEL = os.environ.get("LABEL", "bloxlink")

# shard stuff
#SHARD_COUNT = int(os.environ.get("SHARD_COUNT", 0))
SHARDS_PER_CLUSTER = int(os.environ.get("SHARDS_PER_CLUSTER", 1))

clusters = []



async def get_shard_count():
	SHARD_COUNT = os.environ.get("SHARD_COUNT", 0)

	if SHARD_COUNT:
		return int(SHARD_COUNT)
	else:
		headers = {
			"Authorization": f"Bot {TOKEN}"
		}

		async with aiohttp.ClientSession().get("https://discordapp.com/api/v7/gateway/bot", headers=headers) as response:
			json_response = await response.json()

			return json_response["shards"]


async def start_cluster(network, cluster_id, shard_range, total_shard_count):
	print(f"Spawning a new cluster with shards: {shard_range}", flush=True)

	cluster = Cluster(cluster_id, shard_range, network=network, total_shard_count=total_shard_count)
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
		await start_cluster(network, cluster_id, shard_range, shard_count)


async def start_clusters():
	last, i, cluster_id = 0, 0, 0
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


async def websocket_connect(websocket, path):
	print("MASTER | New client connected", flush=True)

	async for message in websocket:
		pass


if __name__ == '__main__':
	loop = asyncio.get_event_loop()

	try:
		loop.run_until_complete(websockets.serve(websocket_connect, '0.0.0.0', 8765))
		loop.run_until_complete(start_clusters())
	finally:
		loop.run_until_complete(async_docker.session.close())
		loop.close()
