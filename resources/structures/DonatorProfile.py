class DonatorProfile:
	def __init__(self, author, is_premium):
		self.is_premium = is_premium
		self.author = author

		# patreon stuff
		self.patreon = False
		self.payment = None

		# selly stuff
		self.selly = False
		self.days = None
		self.redeemed_codes = []

	def load_patron(self, payment):
		self.patreon = True
		self.payment = payment

	def load_selly(self, payment):
		self.selly = True
		self.codes_redeemed = payment["codes_redeemed"]
		self.days = payment["days"]
