def get_user_data(users, user_id):
    """Get user data from the in-memory storage."""
    if user_id not in users:
        # Initialize with default values if user not found
        users[user_id] = {
            "name": "Unknown",
            "username": None,
            "language": "en",
            "context": [],
            "join_date": None
        }
    return users[user_id]

def save_user_data(users, user_id, data):
    """Save user data to the in-memory storage."""
    users[user_id] = data
    return True

def clear_user_context(users, user_id):
    """Clear the conversation context for a user."""
    user_data = get_user_data(users, user_id)
    user_data["context"] = []
    save_user_data(users, user_id, user_data)
    return True

def add_message_to_context(users, user_id, role, content):
    """Add a message to the user's conversation context."""
    user_data = get_user_data(users, user_id)
    
    # Add the message to the context
    user_data["context"].append({
        "role": role,
        "content": content
    })
    
    # Limit context to the last 10 messages to avoid token limits
    if len(user_data["context"]) > 10:
        user_data["context"] = user_data["context"][-10:]
    
    save_user_data(users, user_id, user_data)
    return True

def get_user_count(users):
    """Get the total number of unique users."""
    return len(users)

def format_user_list(users):
    """Format the user list for display."""
    formatted_list = ""
    for user_id, user_data in users.items():
        name = user_data["name"] or "Unknown"
        username = user_data["username"] or "N/A"
        join_date = user_data["join_date"] or "Unknown"
        formatted_list += f"- *{name}* (@{username})\n  ID: `{user_id}`\n  Joined: {join_date}\n\n"
    return formatted_list
