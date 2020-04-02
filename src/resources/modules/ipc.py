from os import getpid
import websockets
from ast import literal_eval
import json
import uuid
from asyncio import sleep
from ..structures.Bloxlink import Bloxlink
from resources.constants import WEBSOCKET_PORT, WEBSOCKET_SECRET, CLUSTER_ID, LABEL, SHARD_RANGE, STARTED
from time import time
from math import floor
from psutil import Process

eval = Bloxlink.get_module("evalm", attrs="__call__")


pending_tasks = {}

@Bloxlink.module
class IPC(Bloxlink.Module):
	def __init__(self):
		self.connected = False
		self.websocket = None

	async def broadcast(self, message=None, *, response=True, type="EVAL"):
		"""broadcasts a message to all clusters"""

		nonce = str(uuid.uuid4())

		await self.websocket.send(json.dumps({
			"nonce": nonce,
			"secret": WEBSOCKET_SECRET,
			"cluster_id": CLUSTER_ID,
			"type": type,
			"data": message
		}))

		future = self.loop.create_future()

		pending_tasks[nonce] = future

		if response:
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
					message_type = message.get("type")
					message_data = message.get("data")

					if secret != WEBSOCKET_SECRET:
						await websocket.send("Invalid secret.")
						break

					if not nonce:
						await websocket.send("Missing nonce.")
						break

					if message_type:
						if message_type == "EVAL":
							if message_data:
								res = (await eval(message_data, codeblock=False)).description

								await websocket.send(json.dumps({
									"type": "RESULT",
									"cluster_id": CLUSTER_ID,
									"parent": message["parent"],
									"secret": WEBSOCKET_SECRET,
									"nonce": nonce,
									"data": res or "null"
								}))

						elif message_type == "RESULT":
							pending_tasks[nonce].set_result(message_data)
							del pending_tasks[nonce]

						elif message_type == "DM":
							if 0 in SHARD_RANGE:
								message_ = await Bloxlink.wait_for("message", check=lambda m: m.author.id == message_data and not m.guild)

								await websocket.send(json.dumps({
									"type": "RESULT",
									"cluster_id": CLUSTER_ID,
									"parent": message["parent"],
									"secret": WEBSOCKET_SECRET,
									"nonce": nonce,
									"data": message_.content
								}))
						elif message_type == "STATS":
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

							await websocket.send(json.dumps({
								"type": "RESULT",
								"cluster_id": CLUSTER_ID,
								"parent": message["parent"],
								"secret": WEBSOCKET_SECRET,
								"nonce": nonce,
								"data": (len(self.client.guilds), len(self.client.users), mem, uptime)
							}))


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
