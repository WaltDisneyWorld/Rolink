import aiodocker; docker = aiodocker.Docker()


class Utils:
	pass

class Cleanup(Utils):

	@staticmethod
	async def network():
		networks = await docker.networks.list()

		for network in networks:
			if network["Name"] in ("bloxlink-network", "rewrite_default"):
				found_network = await docker.networks.get(network["Id"])
				try:
					await found_network.delete()
				except aiodocker.exceptions.DockerError:
					pass

	@staticmethod
	async def clusters():
		containers = await docker.containers.list()

		for container in containers:
			if "bloxlink-child" in (await container.show())["Name"]:
				await container.delete(force=True)

	@staticmethod
	async def all():
		await Cleanup.clusters()
		await Cleanup.network()
