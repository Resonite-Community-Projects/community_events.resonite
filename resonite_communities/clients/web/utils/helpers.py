
class AttrDict:

    def __init__(self, data):

        if not isinstance(data, dict):
            raise TypeError(f"AttrDict requires a dict, got {type(data)}")

        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively convert nested dicts
                setattr(self, key, AttrDict(value))
            elif isinstance(value, list):
                # Convert list items that are dicts
                setattr(self, key, [
                    AttrDict(item) if isinstance(item, dict) else item
                    for item in value
                ])
            else:
                # Store primitive values as-is
                setattr(self, key, value)

    def __getattr__(self, key):
        return None

    def __repr__(self):
        attrs = {k: v for k, v in self.__dict__.items()}
        return f"AttrDict({attrs})"
