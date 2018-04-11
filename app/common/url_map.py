from bson.objectid import ObjectId
from werkzeug.routing import BaseConverter


class ObjectIdConverter(BaseConverter):
    def to_python(self, value):
        return ObjectId(value)
