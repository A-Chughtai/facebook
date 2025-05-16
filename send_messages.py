import json
import sqlite3
import os
from datetime import datetime
import re
from typing import List, Dict, Optional
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import subprocess
import importlib.util

# Load environment variables
load_dotenv()

def format_phone_number(phone: str) -> str:
    # Remove spaces and keep existing + if present
    if phone.startswith('+'):
        return '+' + re.sub(r'\s+', '', phone[1:])
    return re.sub(r'\s+', '', phone)

def extract_phone_numbers(text: str) -> List[str]:
    patterns = [
        r'\b\d{10}\b',
        r'\b\d{11}\b',
        r'\+\d{10,12}\b',
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'\b\d{4}[-.]?\d{3}[-.]?\d{3}\b'
    ]
    
    phone_numbers = []
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            phone_numbers.append(format_phone_number(match.group()))
    
    return phone_numbers

def get_message_history(user_id: str) -> List[Dict]:
    history_file = f"db/history/{user_id}.json"
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_message_history(user_id: str, message: str, platform: str):
    # Create history directory if it doesn't exist
    os.makedirs("db/history", exist_ok=True)
    
    history_file = f"db/history/{user_id}.json"
    history = get_message_history(user_id)
    
    # Add new message to history
    history.append({
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "platform": platform
    })
    
    # Save updated history
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)

def generate_message(post_text: str, message_history: List[Dict]) -> str:
    # Initialize Groq model
    llm = ChatGroq(
        model_name=os.getenv("GROQ_MODEL", "mixtral-8x7b-32768"),
        temperature=float(os.getenv("TEMPERATURE", "0.7")),
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You have candidates and you are reaching out to potential recuriters.
        Your task is to compose a personalized message based on the job post and previous message history.
        
        Guidelines:
        - Be professional but friendly
        - Reference specific details from their post
        - If there's message history, acknowledge previous interactions
        - Keep the message concise and clear
        - Include a call to action
        - Don't use emojis or informal language
        - Generate a complete message instead of a template because your message will be sent to a recruiter directly
        
        Previous message history:
        {message_history}
        
        Job post text:
        {post_text}
        
        Compose a professional message to send to the recruiter."""),
    ])
    
    # Format message history for the prompt
    formatted_history = "\n".join([
        f"[{msg['timestamp']}] {msg['message']}"
        for msg in message_history[-3:]  # Only use last 3 messages for context
    ]) if message_history else "No previous messages"
    
    # Generate message
    response = llm.invoke(prompt.format(
        message_history=formatted_history,
        post_text=post_text
    ))
    
    return response.content

def send_whatsapp_message(phone_number: str, message: str) -> bool:
    # Try to use whatsapp.py if available
    whatsapp_spec = importlib.util.find_spec("whatsapp")
    if whatsapp_spec is not None:
        try:
            import whatsapp
            return whatsapp.send_message(phone_number, message)
        except Exception as e:
            print(f"Error using whatsapp.py: {str(e)}")
            print("Falling back to message.py...")
    
    # Fallback to message.py
    result = subprocess.run([
        "python", "message.py",
        "--platform", "whatsapp",
        "--phone", phone_number,
        "--message", message
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error sending WhatsApp message: {result.stderr}")
        return False
    return True

def send_messenger_message(user_id: str, message: str) -> bool:
    # Call message.py with Messenger parameters
    result = subprocess.run([
        "python", "message.py",
        "--platform", "messenger",
        "--user_id", user_id,
        "--message", message
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error sending Messenger message: {result.stderr}")
        return False
    return True

def process_unanswered_posts():
    # Connect to database
    db_path = os.getenv("DB_PATH", "db/social_media.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get unanswered posts
    cursor.execute('''
        SELECT id, user_id, username, post_id, post_text
        FROM POSTS
        WHERE message_sent = 0
    ''')
    
    unanswered_posts = cursor.fetchall()
    print(f"Found {len(unanswered_posts)} unanswered posts")
    
    # Track users we've already messaged in this execution
    messaged_users = set()
    
    for post in unanswered_posts:
        post_id, user_id, username, fb_post_id, post_text = post
        
        # Skip if we've already messaged this user in this execution
        if user_id in messaged_users:
            print(f"\nSkipping post {post_id} from user {username} - already messaged in this execution")
            continue
            
        try:
            print(f"\nProcessing post {post_id} from user {username}")
            
            # Get message history
            message_history = get_message_history(user_id)
            
            # Generate message
            message = generate_message(post_text, message_history)
            print(f"Generated message: {message}")
            
            # Extract phone number from post text
            phone_numbers = extract_phone_numbers(post_text)
            
            message_sent = False
            if phone_numbers:
                # Try WhatsApp first
                print(f"Attempting to send WhatsApp message to {phone_numbers[0]}")
                message_sent = send_whatsapp_message(phone_numbers[0], message)
                
                # If WhatsApp fails, try Messenger as fallback
                if not message_sent:
                    print(f"WhatsApp message failed, trying Messenger as fallback for user {username}")
                    message_sent = send_messenger_message(user_id, message)
                    if message_sent:
                        save_message_history(user_id, message, "messenger")
                else:
                    save_message_history(user_id, message, "whatsapp")
            else:
                # Send Messenger message if no phone number available
                print(f"No phone number found, sending Messenger message to {user_id}")
                message_sent = send_messenger_message(user_id, message)
                if message_sent:
                    save_message_history(user_id, message, "messenger")
            
            # Only update database if message was sent successfully
            if message_sent:
                cursor.execute('''
                    UPDATE POSTS
                    SET message_sent = 1
                    WHERE id = ?
                ''', (post_id,))
                conn.commit()
                print(f"Successfully processed post {post_id}")
                # Add user to messaged_users set after successful message
                messaged_users.add(user_id)
            else:
                print(f"Failed to send message for post {post_id} (both WhatsApp and Messenger attempts failed)")
            
        except Exception as e:
            print(f"Error processing post {post_id}: {str(e)}")
            conn.rollback()
            continue
    
    conn.close()
    print("\nFinished processing all unanswered posts")
    print(f"Messaged {len(messaged_users)} unique users in this execution")

if __name__ == "__main__":
    process_unanswered_posts() 