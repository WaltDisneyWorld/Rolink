class Group:
    def __init__(self, id=None, **kwargs):
        self.id = id and str(id)

        self.name = None
        self.description = None
        self.roles = None
        self.owner = None
        
        self.user_rank = None
        self.user_role = None

        self.load_json(**kwargs)

    def load_json(self, **json):
        self.id = self.id or str(json["Id"])
        self.name = self.name or (json.get("Name") and u'{}'.format(json.get("Name")).encode("utf-8").strip())
        self.description = self.description or json.get("Description", "N/A")
        self.roles = self.roles or json.get("Roles")
        self.owner = self.owner or json.get("Owner")

        self.user_rank = self.user_rank or json.get("Rank")
        self.user_role = self.user_role or json.get("Role")
    def __str__(self):
        return "{} ({})".format(self.name, self.id)
