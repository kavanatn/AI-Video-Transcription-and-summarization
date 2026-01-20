from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

class Database:
    def __init__(self, uri):
        self.uri = uri
        self.client = None
        self.db = None

    def connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Trigger a connection check
            self.client.admin.command('ping')
            self.db = self.client.get_default_database()
            print(f"Connected to MongoDB at {self.uri}")
            return True
        except ConnectionFailure:
            print("Failed to connect to MongoDB")
            return False

# Global instance
db_instance = Database("") # Initialized in app.py
