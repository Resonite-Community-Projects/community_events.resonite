from sqlalchemy.types import TypeDecorator, JSON
import easydict
import json

class EasyDictType(TypeDecorator):
    """Custom type decorator to store EasyDict as JSON in the database.

    Will be loaded back as an EasyDict when queried.
    """
    impl = JSON

    def process_bind_param(self, value, dialect):
        if isinstance(value, easydict.EasyDict):
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value:
            return easydict.EasyDict(json.loads(value))
        return easydict.EasyDict()