def string_resolver(message, content=None, arg=None):
    if not content:
        content = message.content

    return str(content)

resolver_map = {
    "string": string_resolver
}

