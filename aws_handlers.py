import datetime
import os
from typing import Optional, Union, Sequence, List

from pymongo import MongoClient


monitoring_db = MongoClient(os.environ['MONITOR_MONGO_URI'])['monitor']


def get_collection(uri_env: str, db_name_env: str, in_collection_name: str) -> 'pymongo.collection':
    return MongoClient(os.environ[uri_env])[os.environ[db_name_env]][in_collection_name]


class BaseMonitor:
    out_collection_name: str

    def __init__(self, uri_env: str, db_name_env: str, in_collection_name: str, environment: Optional[str] = None):
        self.in_collection = get_collection(uri_env, db_name_env, in_collection_name)
        self.environment = environment

    def read(self) -> Union[dict, Sequence]:
        raise NotImplemented

    def write_many(self, data: Sequence):
        utc_now = datetime.datetime.utcnow()

        for item in data:
            item['time'] = utc_now
            if self.environment is not None:
                item['environment'] = self.environment

        monitoring_db[self.out_collection_name].insert_many(data)

    def write_one(self, data: dict):
        data['time'] = datetime.datetime.utcnow()
        if self.environment is not None:
            data['environment'] = self.environment

        monitoring_db[self.out_collection_name].insert_one(data)

    def collect(self):
        data = self.read()
        if isinstance(data, Sequence):
            self.write_many(data)

        else:
            self.write_one(self.read())


class OlxMonitor(BaseMonitor):
    out_collection_name = 'olx_active_users'

    def read(self):
        return {'active_count': self.in_collection.count_documents({'active': True})}


class FoodUsersMonitor(BaseMonitor):
    out_collection_name = 'food_users'

    def read(self) -> List:
        return [
            item['_id']|{'count': int(item['count'])}
            for item in self.in_collection.aggregate(
                [
                    {
                        '$group': {
                            '_id': {'is_active': '$is_active', 'workflow': '$workflow', 'location': '$info.location'},
                            'count': {'$sum': 1}
                        }
                    }
                ]
            )
        ]


def all_monitor(event, context):
    monitors = [
        OlxMonitor('OLX_URI', 'OLX_DB', 'subscription'),
        FoodUsersMonitor('FOOD_STAGING_URI', 'FOOD_STAGING_DB', 'users', environment='staging'),
        FoodUsersMonitor('FOOD_LIVE_URI', 'FOOD_LIVE_DB', 'users', environment='live'),
    ]

    for monitor in monitors:
        monitor.collect()
