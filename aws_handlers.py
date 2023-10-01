import datetime
import os
from typing import Optional

from pymongo import MongoClient


monitoring_db = MongoClient(os.environ['MONITOR_MONGO_URI'])['monitor']


class BaseMonitor:
    out_collection_name: str
    metric: str

    def __init__(self, uri_env: str, db_name_env: str, in_collection_name: str, environment: Optional[str] = None):
        self.in_collection = MongoClient(os.environ[uri_env])[os.environ[db_name_env]][in_collection_name]
        self.environment = environment

    def read(self) -> dict:
        raise NotImplemented

    def write(self, data: dict):
        data['time'] = datetime.datetime.utcnow()
        if self.environment is not None:
            data['environment'] = self.environment

        monitoring_db[self.out_collection_name].insert_one(data)

    def collect(self):
        self.write(self.read())


class OlxMonitor(BaseMonitor):
    out_collection_name = 'olx_active_users'

    def read(self):
        return {'active_count': self.in_collection.count_documents({'active': True})}


def all_monitor():
    for monitor in [OlxMonitor('OLX_URI', 'OLX_DB_NAME', 'subscription')]:
        monitor.collect()
