"""PyMongo database access."""
from collections.abc import Iterator

from pymongo import MongoClient
from pymongo.database import Database

from app.config import get_mongodb_uri, get_mongodb_database

_client: MongoClient | None = None

def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(get_mongodb_uri())
    return _client

def get_mongo_db() -> Iterator[Database]:
    client = get_mongo_client()
    yield client[get_mongodb_database()]

def init_db() -> None:
    """Create MongoDB indexes."""
    from pymongo.errors import DuplicateKeyError
    client = get_mongo_client()
    db = client[get_mongodb_database()]
    try:
        db.networks.create_index("id", unique=True)
        db.nodes.create_index([("network_id", 1), ("id", 1)], unique=True)
        db.links.create_index([("network_id", 1), ("id", 1)], unique=True)
    except DuplicateKeyError as e:
        print(f"Warning: Could not create unique index due to duplicates: {e}")
