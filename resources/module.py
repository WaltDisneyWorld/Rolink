from .structures import Module

loaded_modules = []


def new_module(*args, **kwargs):
	# TODO: check if module is already registered, and return it
	module = Module(*args, **kwargs)
	# store module and do stuff with it
