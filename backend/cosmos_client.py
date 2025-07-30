import os
from azure.cosmos import CosmosClient, PartitionKey
import logging

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME")

# Add validation
if not all([COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DB_NAME]):
    logging.warning("Cosmos DB environment variables not fully configured")
    client = None
    database = None
else:
    try:
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        database = client.get_database_client(COSMOS_DB_NAME)
        logging.info("Cosmos DB client initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Cosmos DB client: {e}")
        client = None
        database = None

def get_container(container_name):
    if not database:
        raise Exception("Cosmos DB not properly configured. Check environment variables.")
    return database.get_container_client(container_name)