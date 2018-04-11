import datetime
import json

from bson.objectid import ObjectId


class MongoEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime.datetime):
            return str(o)
        return json.JSONEncoder.default(self, o)


class MongoDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.objectid_hook, *args, **kwargs)

    def objectid_hook(self, o):
        for k, v in o.items():
            if k in ['pims_id', 'clinic_id', 'payment_customer_id']:
                continue
            if k.endswith('_id'):
                o[k] = ObjectId(v)
        return o
