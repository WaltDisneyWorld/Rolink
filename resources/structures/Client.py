from discord import AutoShardedClient


class Bloxlink(AutoShardedClient):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.modules = {}

	def __repr__(self):
		return "<Bloxlink Instance>"

client = Bloxlink(
	fetch_offline_members=False
)
