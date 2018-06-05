def string_resolver(message, arg, content=None):
	if not content:
		content = message.content

	return str(content), None

def choice_resolver(message, arg, content=None):
	if not content:
		content = message.content

	for choice in arg["choices"]:
		if choice.lower() == content.lower():
			return choice, None

	return False, f'Choice must be of either: {str(arg["choices"])}'

resolver_map = {
	"string": string_resolver,
	"choice": choice_resolver
}
