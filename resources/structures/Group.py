class Group:
	def __init__(self, id=None, **kwargs):
		self.id = id and str(id)

		self.name = None
		self.description = None
		self.roles = None
		self.owner = None
		self.member_count = None
		self.embed_url = None
		self.url = self.id and f"https://www.roblox.com/My/Groups.aspx?gid={self.id}"

		self.user_rank = None
		self.user_role = None

		self.load_json(**kwargs)

	def load_json(self, **json):
		self.id = self.id or str(json["Id"])
		self.name = self.name or json.get("Name")
		self.description = self.description or json.get("Description") or json.get("description", "N/A")
		self.roles = self.roles or json.get("Roles")
		self.owner = self.owner or json.get("Owner") or json.get("owner")
		self.member_count = self.member_count or json.get("memberCount")
		self.embed_url = self.embed_url or json.get("EmblemUrl")
		self.url = self.url or (self.id and f"https://www.roblox.com/My/Groups.aspx?gid={self.id}")

		self.user_rank = self.user_rank or (json.get("Rank") and str(json.get("Rank")).strip())
		self.user_role = self.user_role or (json.get("Role") and str(json.get("Role")).strip())

	def __str__(self):
		name = u'{}'.format(self.name).encode("utf-8").strip()

		return "{} ({})".format(name, self.id)

	def __repr__(self):
		return str(self)
