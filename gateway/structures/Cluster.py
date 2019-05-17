import aiodocker; docker = aiodocker.Docker()
from exceptions import ClusterException # pylint: disable=E0611
from os import environ as env
import asyncio

# websocket stuff
WEBSOCKET_PORT = int(env.get("WEBSOCKET_PORT", 8765))
HOSTNAME = env.get("HOSTNAME", "localhost")

# bloxlink specifications
RELEASE = env.get("RELEASE", "LOCAL")
IMAGE = env.get("CLUSTER_IMAGE", "rewrite:latest")
LABEL = env.get("LABEL", "bloxlink")




class Cluster:
	def __init__(self, cluster_id, shard_range, network, total_shard_count):
		self.id = cluster_id
		self.range = shard_range

		self.network = network
		self.container = None

		self.total_shard_count = total_shard_count

	async def kill(self):
		pass

	async def respawn(self):
		pass

	async def spawn(self):
		container = await docker.containers.create_or_replace(
			config={
				"Image": IMAGE,
				# not sure what the few options do below rofl
				"AttachStdin": False,
				"AttachStdout": True,
				"AttachStderr": True,
				"Tty": False,
				"OpenStdin": False,
				"StdinOnce": False,
				# end of the unknown options
				"Cmd": ["python3", "src/bot.py"],
				"Env": [
					f"SHARD_RANGE={str(self.range)}",
					f"SHARD_COUNT={self.total_shard_count}",
					f"CLUSTER_ID={self.id}",
					f"WEBSOCKET_PORT={WEBSOCKET_PORT}",
					f"RELEASE={RELEASE}",
					f"LABEL={LABEL}",
				]
			},
			name=f"{LABEL}-child-{self.id}",
		)

		await self.network.connect({"Container": f"{LABEL}-child-{self.id}"})

		self.container = container
		errors = [f"ERROR LOGS FOR CLUSTER {self.id}"]

		try:
			await container.start()

			logs = await container.log(stdout=True, stderr=True, follow=True)
			async for line in logs:
				print(line, flush=True)

			errors = errors + await container.log(stderr=True)
			print(errors, flush=True)
			#print(errors, flush=True) # TODO: do something with this.. maybe log to a file?

		finally:
			await self.network.disconnect({"Container": f"{LABEL}-child-{self.id}"})
			await container.delete(force=True)

			if errors:
				raise ClusterException(str(errors))