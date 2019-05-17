from os import environ as env
import websockets
from ..structures.Bloxlink import Bloxlink


WEBSOCKET_PORT = env.get("WEBSOCKET_PORT")
LABEL = env.get("LABEL", "master").lower()



@Bloxlink.module
class IPC:
	def __init__(self, args):
		self.connected = False

	async def connect(self):
		success = False

		try:
			async with websockets.connect(f"ws://{LABEL}:{WEBSOCKET_PORT}") as websocket:
				Bloxlink.log("Connected to Websocket")
				self.connected = True
				success = True

				async for message in websocket:
					pass

		finally:
			# disconnected
			self.connected = False
			Bloxlink.log("Disconnected from websocket")


		return success


	async def kill(self):
		pass

	async def setup(self):
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

		else:
			Bloxlink.log("DEBUG | Not loading IPC")

