import json
import os
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import subprocess
import importlib.util
from excel_handler import ExcelHandler
from followup_handler import FollowupHandler
import whatsapp

# Load environment variables
load_dotenv()

def format_phone_number(phone: str) -> str:
    # Remove spaces and keep existing + if present
    if phone.startswith('+'):
        return '+' + re.sub(r'\s+', '', phone[1:])
    return '+' + re.sub(r'\s+', '', phone)

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
        ("system", """You are a professional job seeker reaching out to recruiters. Your task is to compose a personalized message based on the job post and previous message history.
        
        Guidelines:
        - Write a complete, ready-to-send message without any placeholders or [brackets]
        - Be professional but friendly
        - Reference specific details from their post
        - If there's message history, acknowledge previous interactions
        - Keep the message concise and clear
        - Include a call to action
        - Don't use emojis or informal language
        - Don't use templates or placeholders - write the complete message as if you're sending it right now
        - Don't include [Your Name] or [Recruiter's Name] - just write the message as is
        - Be direct and write a really short message please
        
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
            return whatsapp.send_message(phone_number, message)
        except Exception as e:
            print(f"Error using whatsapp.py: {str(e)}")
            print("Falling back to message.py...")
            return False

def send_messenger_message(user_id: str, message: str) -> bool:
    # Call message.py with Messenger parameters
    result = subprocess.run([
        "python", "message.py",
        "--user_id", user_id,
        "--message", message
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error sending Messenger message: {result.stderr}")
        return False
    return True

def process_unanswered_posts():
    # Initialize handlers
    excel_handler = ExcelHandler()
    followup_handler = FollowupHandler()
    
    # Get unanswered posts
    unanswered_posts = excel_handler.get_unanswered_posts()
    print(f"Found {len(unanswered_posts)} unanswered posts")
    
    # Track users we've already messaged in this execution
    messaged_users = set()
    
    for post in unanswered_posts:
        post_id = post['id']
        user_id = post['user_id']
        username = post['username']
        post_text = post['post_text']
        post_url = post.get('post_url', '')
        
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
            platform_used = None
            
            # Try WhatsApp if phone number is available
            if phone_numbers:
                formatted_phone = phone_numbers[0]
                if not formatted_phone.startswith('+'):
                    formatted_phone = '+' + formatted_phone
                
                # Update WhatsApp number in Excel
                excel_handler.update_whatsapp_number(post_id, formatted_phone)
                
                print(f"Attempting to send WhatsApp message to {formatted_phone}")
                if send_whatsapp_message(formatted_phone, message):
                    print(f"WhatsApp message sent successfully to {formatted_phone}")
                    message_sent = True
                    platform_used = "whatsapp"
                    print("WhatsApp message sent successfully")
                else:
                    print("WhatsApp message failed, will try Messenger")
            
            # Try Messenger if WhatsApp failed or no phone number available
            if not message_sent:
                print(f"Trying Messenger for user {username}")
                if send_messenger_message(user_id, message):
                    message_sent = True
                    platform_used = "messenger"
                    print("Messenger message sent successfully")
                else:
                    print("Messenger message failed")
            
            # Process the result
            if message_sent and platform_used:
                # Mark as sent in Excel
                excel_handler.mark_message_sent(post_id)
                print(f"Successfully processed post {post_id} via {platform_used}")
                
                # Save message history
                save_message_history(user_id, message, platform_used)
                
                # Create follow-up
                followup_date = datetime.now() + timedelta(days=1)
                followup_success = followup_handler.add_followup(
                    user_id=user_id,
                    username=username,
                    phone_number=phone_numbers[0] if phone_numbers else None,
                    post_url=post_url,
                    followup_date=followup_date,
                    last_message_date=datetime.now()
                )
                
                if followup_success:
                    print(f"Created follow-up for user {username} scheduled for {followup_date}")
                else:
                    print(f"Failed to create follow-up for user {username}")
                
                # Add to messaged users
                messaged_users.add(user_id)
            else:
                print(f"Failed to send message for post {post_id} (both platforms failed)")
            
        except Exception as e:
            print(f"Error processing post {post_id}: {str(e)}")
            continue
    
    print("\nFinished processing all unanswered posts")
    print(f"Messaged {len(messaged_users)} unique users in this execution")

if __name__ == "__main__":
    process_unanswered_posts() 