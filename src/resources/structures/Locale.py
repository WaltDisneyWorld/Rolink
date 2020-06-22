import json
from jsonpath_ng import parse
from ..structures.Bloxlink import Bloxlink


get_files = Bloxlink.get_module("utils", attrs="get_files")

locales = {}

for file_name in get_files("src/locales"):
	with open(f"src/locales/{file_name}") as f:
		file_contents = f.read()
		file_json = json.loads(file_contents)
		locales[file_name.replace(".json", "")] = file_json



class Locale:
	def __init__(self, lang="en"):
		self.lang = lang

	def __call__(self, locale_path, *args, **kwargs):
		jsonpath_expr = parse(locale_path)

		try:
			match = jsonpath_expr.find(locales.get(self.lang, "en"))[0].value
		except IndexError:
			try:
				match = jsonpath_expr.find(locales.get("en"))[0].value
			except IndexError:
				return locale_path

		return match.format(*args, **kwargs)
