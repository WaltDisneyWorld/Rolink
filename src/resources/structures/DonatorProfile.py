class DonatorProfile:
    def __init__(self, author):
        self.author = author
        self.features = {}
        self.notes = []
        self.attributes = {
            "patreon": False,
            "selly": False,
            "PREMIUM_ANYWHERE": False
        }

        # patreon stuff
        self.amount_cents = 0

        # selly stuff
        self.days = None

    def load_patreon(self, data):
        self.attributes["patreon"] = True
        self.amount_cents = data["pledged"]

    def load_selly(self, days):
        self.attributes["selly"] = True
        self.days = days

    def add_features(self, *args):
        for arg in args:
            self.features[arg] = True

    def add_note(self, text):
        self.notes.append(text)
