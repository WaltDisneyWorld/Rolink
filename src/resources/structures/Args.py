class Args:
    """Dummy class used to contain arguments"""

    def __init__(self, **kwargs):
        self._items = {}

        self.add(**kwargs)

    def add(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)
            self._items[name] = str(value)

    def remove(self, item, no_error=True):
        self._items.pop(item, no_error)

    def clear(self):
        self._items.clear()

    def __str__(self):
        return f"< Argument Holder: [{', '.join([x + ' -> ' + y for x, y in self._items.items()])}] >"
