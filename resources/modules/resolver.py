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

def user_resolver(message, arg, content=None):
	if not content:
		content = message.content

	guild = message.guild

	if message.mentions:
		return message.mentions[0], None
	else:
		is_int, is_id = None, None

		try:
			is_int = int(content)
			is_id = is_int > 15
		except ValueError:
			pass

		if is_id:
			return guild.get_member(is_int), None
		else:
			return guild.get_member_named(content), None

	return False, "Invalid user"

resolver_map = {
	"string": string_resolver,
	"choice": choice_resolver,
	"user": user_resolver
}
