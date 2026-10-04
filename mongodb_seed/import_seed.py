import json
import ssl
import os
from pymongo import MongoClient
import sys

def main():
    uri = "mongodb+srv://nevethaniivii_db_user:MrjW1rES4dd8ITHL@cluster0.wsxkegi.mongodb.net"
    db_name = "netchaos"
    
    # Get the directory where this script and json files are located
    seed_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"Connecting to MongoDB Atlas...")
    client = MongoClient(uri)
    db = client[db_name]

    collections = [
        "networks",
        "nodes",
        "links",
        "traffic_simulations",
        "chaos_experiments",
        "failure_detections",
        "recovery_events"
    ]

    for col_name in collections:
        file_path = os.path.join(seed_dir, f"{col_name}.json")
        if not os.path.exists(file_path):
            print(f"WARNING: {file_path} not found, skipping...")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        col = db[col_name]
        
        # Drop existing collection data like --drop does
        col.drop()
        
        if data:
            if isinstance(data, list):
                col.insert_many(data)
                print(f"OK {col_name} imported ({len(data)} documents)")
            else:
                col.insert_one(data)
                print(f"OK {col_name} imported (1 document)")
        else:
            print(f"OK {col_name} imported (empty list)")

    print(f"Done! Database '{db_name}' is ready.")

if __name__ == "__main__":
    main()
