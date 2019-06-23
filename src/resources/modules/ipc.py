from os import environ as env
import websockets
import json
import uuid
from asyncio import sleep
from ..structures.Bloxlink import Bloxlink

eval = Bloxlink.get_module("eval", attrs="__call__")


WEBSOCKET_PORT = env.get("WEBSOCKET_PORT")
WEBSOCKET_SECRET = env.get("WEBSOCKET_SECRET")
CLUSTER_ID = int(env.get("CLUSTER_ID", 0))
LABEL = env.get("LABEL", "master").lower()


pending_tasks = {}

@Bloxlink.module
class IPC:
	def __init__(self, args):
		self.connected = False
		self.websocket = None

		self.client = args.client
		self.loop = args.client.loop

	async def broadcast(self, message, response=True):
		"""broadcasts a message to all clusters"""

		nonce = str(uuid.uuid4())

		await self.websocket.send(json.dumps({
			"nonce": nonce,
			"secret": WEBSOCKET_SECRET,
			"cluster_id": CLUSTER_ID,
			"type": "EVAL",
			"data": message
		}))

		future = self.loop.create_future()

		pending_tasks[nonce] = future

		return await future

	async def connect(self):
		success = False

		try:
			async with websockets.connect(f"ws://{LABEL}:{WEBSOCKET_PORT}") as websocket:
				Bloxlink.log("Connected to Websocket")
				self.connected = True
				success = True
				self.websocket = websocket

				await websocket.send(json.dumps({
					"type": "IDENTIFY",
					"cluster_id": CLUSTER_ID,
					"secret": WEBSOCKET_SECRET,
					"nonce": str(uuid.uuid4())
				}))

				await self.client.wait_for("ready")

				# for initial stats posting
				await websocket.send(json.dumps({
					"type": "READY",
					"cluster_id": CLUSTER_ID,
					"secret": WEBSOCKET_SECRET,
					"nonce": str(uuid.uuid4()),
					"data": {
						"guilds": len(self.client.guilds),
						"users": len(self.client.users)
					}
				}))

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

					if message.get("type"):
						if message["type"] == "EVAL":
							if message.get("data"):
								to_eval = message.get("data")

								res = (await eval(to_eval, codeblock=False)).description

								await websocket.send(json.dumps({
									"type": "RESULT",
									"cluster_id": CLUSTER_ID,
									"parent": message["parent"],
									"secret": WEBSOCKET_SECRET,
									"nonce": nonce,
									"data": res or "null"
								}))

						elif message["type"] == "RESULT":
							pending_tasks[nonce].set_result(message["data"])
							del pending_tasks[nonce]

		finally:
			# disconnected
			self.connected = False
			Bloxlink.log("Disconnected from websocket")

		return success

	async def __setup__(self):
		if WEBSOCKET_PORT:
			failed = 0

			while True:
				if failed == 5:
					raise SystemExit("Websocket disconnected. Couldn't reconnect after 5 tries.")

				success = await self.connect()

				if success:
					failed = 0
				else:
					failed += 1
					Bloxlink.log("Disconnected from websocket. Retrying.")
					await sleep(5)

		else:
			Bloxlink.log("DEBUG | Not loading IPC")
