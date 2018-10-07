from resources.module import get_module

is_premium = get_module("utils", attrs=["is_premium"])

class VirtualGroups:
    def __init__(self, **kwargs):
        pass

    async def premium_bind(self, author):
        DonatorProfile = await is_premium(author=author)
        return DonatorProfile.is_premium

    def get_virtual_group(self, name):
        name = name.replace("Bind", "_bind")
        
        if hasattr(self, name):
            return getattr(self, name)


def new_module():
    return VirtualGroups
