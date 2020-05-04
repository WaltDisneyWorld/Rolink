class DonatorProfile:
    def __init__(self, author):
        self.author = author
        self.features = {}
        self.attributes = {
            "patreon": False,
            "selly": False,
            "PREMIUM_ANYWHERE": False
        }

        # patreon stuff
        self.amount_cents = 0

        # selly stuff
        self.days = None
        self.redeemed_codes = []

    def load_patreon(self, payment_data):
        self.attributes["patreon"] = True
        self.amount_cents = payment_data["attributes"]["amount_cents"]

    def load_selly(self, payment_data):
        self.attributes["selly"] = True
        self.codes_redeemed = payment_data["codes_redeemed"]
        self.days = payment_data["days"]

    def add_features(self, *args):
        for arg in args:
            self.features[arg] = True
