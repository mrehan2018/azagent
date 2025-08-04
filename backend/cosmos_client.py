import os
from azure.cosmos import CosmosClient, PartitionKey
import logging
from datetime import datetime
import uuid

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

# Chat storage functions
def save_chat_message(user_id, user_role, user_message, ai_response, context=None):
    """Save a chat interaction to Cosmos DB"""
    try:
        chat_container = get_container("chat_history")
        
        chat_record = {
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "userRole": user_role,
            "timestamp": datetime.utcnow().isoformat(),
            "userMessage": user_message,
            "aiResponse": ai_response,
            "context": context,
            "sessionId": f"{user_id}_{datetime.utcnow().strftime('%Y%m%d')}"
        }
        
        result = chat_container.create_item(chat_record)
        logging.info(f"Chat message saved successfully for user {user_id}")
        return result
        
    except Exception as e:
        logging.error(f"Failed to save chat message: {str(e)}")
        raise Exception(f"Failed to save chat message: {str(e)}")

def get_chat_history(user_id, limit=10):
    """Get recent chat history for a user"""
    try:
        chat_container = get_container("chat_history")
        
        query = f"""
        SELECT TOP {limit} * FROM c 
        WHERE c.userId = '{user_id}' 
        ORDER BY c.timestamp DESC
        """
        
        items = list(chat_container.query_items(
            query, 
            enable_cross_partition_query=True
        ))
        
        logging.info(f"Retrieved {len(items)} chat messages for user {user_id}")
        return items
        
    except Exception as e:
        logging.error(f"Failed to get chat history: {str(e)}")
        return []

def update_user_chat_history(user_id, user_role, new_message):
    """Update user's chat history in their main record"""
    try:
        logging.info(f"=== UPDATE USER CHAT HISTORY START ===")
        logging.info(f"user_id: {user_id}, user_role: {user_role}")
        
        container_name = f"{user_role}s"  # students, teachers, parents
        logging.info(f"Container name: {container_name}")
        
        container = get_container(container_name)
        logging.info("Container retrieved successfully")
        
        # Get user record
        query = f"SELECT * FROM c WHERE c.userId = '{user_id}' OR c.id = '{user_id}'"
        logging.info(f"Query: {query}")
        
        items = list(container.query_items(query, enable_cross_partition_query=True))
        logging.info(f"Query returned {len(items)} items")
        
        if items:
            user_record = items[0]
            logging.info(f"Found user record for {user_id}")
            logging.info(f"Current chatHistory length: {len(user_record.get('chatHistory', []))}")
            
            # Initialize chatHistory if it doesn't exist
            if "chatHistory" not in user_record:
                user_record["chatHistory"] = []
                logging.info("Initialized empty chatHistory")
            
            # Add new message (keep last 20 messages)
            new_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "message": new_message["userMessage"],
                "response": new_message["aiResponse"]
            }
            user_record["chatHistory"].append(new_entry)
            logging.info(f"Added new message. New chatHistory length: {len(user_record['chatHistory'])}")
            
            # Keep only last 20 messages
            user_record["chatHistory"] = user_record["chatHistory"][-20:]
            logging.info(f"Trimmed to last 20. Final length: {len(user_record['chatHistory'])}")
            
            # Update the record
            update_result = container.replace_item(user_record["id"], user_record)
            logging.info(f"Record updated successfully: {update_result['id']}")
            logging.info("=== UPDATE USER CHAT HISTORY SUCCESS ===")
            
        else:
            logging.warning(f"User {user_id} not found for chat history update")
            
    except Exception as e:
        logging.error(f"Failed to update user chat history: {str(e)}")
        logging.error(f"Error type: {type(e).__name__}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        raise e  # Re-raise to see the error in main.py

def create_chat_container_if_not_exists():
    """Create chat_history container if it doesn't exist"""
    try:
        if not database:
            logging.error("Database not initialized")
            return False
            
        try:
            # Try to get the container
            database.get_container_client("chat_history")
            logging.info("chat_history container already exists")
            return True
            
        except Exception:
            # Container doesn't exist, create it
            container = database.create_container(
                id="chat_history",
                partition_key=PartitionKey(path="/userId"),
                offer_throughput=400
            )
            logging.info("chat_history container created successfully")
            return True
            
    except Exception as e:
        logging.error(f"Failed to create chat_history container: {str(e)}")
        return False

def save_chat_to_cosmos(user_id: str, user_role: str, question: str, answer: str):
    """Simple function to save chat directly to user's document"""
    try:
        logging.info(f"=== SAVING CHAT TO COSMOS ===")
        logging.info(f"user_id: {user_id}, user_role: {user_role}")
        
        # Determine container name based on role
        container_name = f"{user_role}s"  # student -> students, teacher -> teachers, etc.
        container = get_container(container_name)
        
        # Read the user's document
        user_doc = container.read_item(item=user_id, partition_key=user_id)
        logging.info(f"Found user document: {user_doc.get('name', user_id)}")
        
        # Create chat entry with timestamp
        from datetime import datetime
        chat_entry = {
            "question": question,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Initialize chatHistory if it doesn't exist, then append
        user_doc.setdefault("chatHistory", []).append(chat_entry)
        
        # Keep only last 20 chats
        user_doc["chatHistory"] = user_doc["chatHistory"][-20:]
        
        # Update document in Cosmos
        container.replace_item(item=user_id, body=user_doc)
        
        logging.info(f"Chat saved successfully. Total chats: {len(user_doc['chatHistory'])}")
        return True
        
    except Exception as e:
        logging.error(f"Error saving chat: {str(e)}")
        logging.error(f"Error type: {type(e).__name__}")
        return False

def get_chat_history_from_user(user_id: str, user_role: str):
    """Get chat history directly from user's document"""
    try:
        container_name = f"{user_role}s"
        container = get_container(container_name)
        
        user_doc = container.read_item(item=user_id, partition_key=user_id)
        chat_history = user_doc.get("chatHistory", [])
        
        # Return in reverse order (newest first)
        return list(reversed(chat_history))
        
    except Exception as e:
        logging.error(f"Error getting chat history: {str(e)}")
        return []