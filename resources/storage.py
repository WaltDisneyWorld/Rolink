client = None

def load(**kwargs):
	if kwargs.get("client"):
		global client
		if not client:
			bot = kwargs.get("client")
			client = bot

def get(arg):
	return globals().get(arg)
