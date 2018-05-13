import logging


logging.basicConfig(level=logging.INFO)

def log(message):
	message = "Bloxlink | {}".format(message)
	with open("logs.txt", "a") as f:
		f.write(message + "\n")
	print(message, flush=True)
