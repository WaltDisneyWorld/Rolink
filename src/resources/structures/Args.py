class Args:
    """Dummy class used to contain arguments"""

    def __init__(self, **kwargs):
        self._items = {}

        for name, value in kwargs.items():
            setattr(self, name, value)
            self._items[name] = str(value)

    def __str__(self):
        return f"< Argument Holder: [{', '.join([x + ' -> ' + y for x, y in self._items.items()])}]"
