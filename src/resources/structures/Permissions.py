class Permissions:
    """Contains permission attributes for commands"""

    def __init__(self, roles=None, **kwargs):
        self.allowed = {"roles":[], "discord_perms": [], "functions": []}
        self.exceptions = {"roles":[], }

        self.bloxlink_role = False
        self.developer_only = False
        self.premium = False

        self.allow_bypass = False

        if roles:
            self.allowed["roles"] = roles

    def build(self, *args, function=None, roles=None):
        if roles:
            self.allowed["roles"] += roles

        if function:
            self.allowed["functions"].append(function)

        for arg in args:
            if arg in ("BLOXLINK_ADMIN", "BLOXLINK_MANAGER", "BLOXLINK_UPDATER", "BLOXLINK_MODERATOR"):
                self.bloxlink_role = arg.replace("_", " ").title()
            elif arg in ("MANAGE_ROLES", "BAN_MEMBERS", "KICK_MEMBERS", "MANAGE_SERVER"):
                self.allowed["discord_perms"].append(arg.replace("_", "").title())
            elif arg == "DEVELOPER_ONLY":
                self.developer_only = True
            elif arg == "PREMIUM":
                self.premium = True


        return self

    def exception(self, *args, roles=None):
        if roles:
            self.exceptions["roles"] += roles

        return self
