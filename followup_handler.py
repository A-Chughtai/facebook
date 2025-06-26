import pandas as pd
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import json
import subprocess
import re
from followup_sheets_handler import FollowupSheetsHandler

# Load environment variables
load_dotenv()

def format_phone_number(phone: str) -> str:
    # Convert to string and handle float values
    phone = str(int(float(phone))) if isinstance(phone, float) else str(phone)
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

class FollowupHandler:
    def __init__(self, credentials_file="credentials.json"):
        self.sheets_handler = FollowupSheetsHandler(credentials_file=credentials_file)
    
    def get_message_history(self, user_id: str) -> List[Dict]:
        """Get message history for a user"""
        history_file = f"db/history/{user_id}.json"
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def compose_followup_message(self, username: str, post_url: str, user_id: str) -> str:
        """Compose a follow-up message using Groq"""
        try:
            # Initialize Groq model
            llm = ChatGroq(
                model_name=os.getenv("GROQ_MODEL", "mixtral-8x7b-32768"),
                temperature=float(os.getenv("TEMPERATURE", "0.7")),
                api_key=os.getenv("GROQ_API_KEY")
            )
            
            # Get message history
            message_history = self.get_message_history(user_id)
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Your task is to compose an engaging follow-up message that maintains the conversation and shows continued interest.

                History text:
                {message_history}

                Guidelines:
                - Write a complete, ready-to-send message without any placeholders or [brackets]
                - Be professional but friendly
                - Keep the message concise and clear
                - Don't use placeholders - write the complete message as if you're sending it right now
                - Don't include [Your Name] or [Recruiter's Name] - just write the message as is
                - Be direct and write a really short message please
                - Personalize accordin to message history
                - Strictly follow the structure, tone, and content of the example template below. The message must closely resemble the template, only changing details to personalize for the user, company, and post.

                Example Template:
                Hi hope you having a good morning , do you have any staff or any type of event requirements which Ta'al can 100% take care of ,completely on your budget? Please let me know. Thanks                
                
                """),
            ])
            
            # Format message history for the prompt
            formatted_history = "\n".join([
                f"[{msg['timestamp']}] {msg['message']}"
                for msg in message_history[-3:]  # Only use last 3 messages for context
            ]) if message_history else "No previous messages"
            
            # Generate message
            response = llm.invoke(prompt.format(
                message_history=formatted_history,
                post_text=f"Follow-up for post: {post_url}"
            ))
            
            return response.content
        except Exception as e:
            print(f"Error composing message with Groq: {str(e)}")
            return "Hi! I wanted to follow up on our previous conversation. I'm still very interested in the opportunity and would love to hear from you. Would you have any updates to share?"
    
    def add_followup(self, user_id: str, username: str, phone_number: str, 
                    post_url: str, followup_date: datetime, message: Optional[str] = None, 
                    last_message_date: Optional[datetime] = None) -> bool:
        """Add a new follow-up entry to the Google Sheet"""
        try:
            # Compose message if not provided
            if not message:
                message = self.compose_followup_message(username, post_url, user_id)
            
            # Add follow-up using sheets handler
            return self.sheets_handler.add_followup(
                user_id=user_id,
                username=username,
                phone_number=phone_number,
                post_url=post_url,
                followup_date=followup_date,
                message=message,
                last_message_date=last_message_date
            )
        except Exception as e:
            print(f"Error adding follow-up to Google Sheet: {str(e)}")
            return False
    
    def get_pending_followups(self) -> List[Dict]:
        """Get all pending follow-ups that were scheduled one day ago or more and user hasn't replied"""
        try:
            return self.sheets_handler.get_pending_followups()
        except Exception as e:
            print(f"Error processing follow-ups: {str(e)}")
            return []
    
    def mark_followup_completed(self, followup_id: int) -> bool:
        """Mark a follow-up as completed"""
        try:
            return self.sheets_handler.mark_followup_completed(followup_id)
        except Exception as e:
            print(f"Error updating follow-up status: {str(e)}")
            return False
    
    def delete_followup(self, followup_id: int) -> bool:
        """Delete a follow-up entry"""
        try:
            return self.sheets_handler.delete_followup(followup_id)
        except Exception as e:
            print(f"Error deleting follow-up: {str(e)}")
            return False
    
    def get_all_followups(self) -> List[Dict]:
        """Get all follow-ups with their creation timestamps"""
        try:
            return self.sheets_handler.get_all_followups()
        except Exception as e:
            print(f"Error reading follow-ups: {str(e)}")
            return []
    
    def process_followups(self) -> Dict[str, int]:
        """Process all pending follow-ups and send messages"""
        try:
            # Get pending follow-ups
            pending_followups = self.get_pending_followups()
            print(f"Found {len(pending_followups)} pending follow-ups to process")
            
            # Track results
            results = {
                "total": len(pending_followups),
                "successful": 0,
                "failed": 0
            }
            
            for followup in pending_followups:
                try:
                    followup_id = followup['id']
                    user_id = followup['user_id']
                    username = followup['username']
                    phone_number = followup['phone_number']
                    message = followup['message']
                    created_at = followup['created_at']
                    last_message_date = followup['last_message_date']
                    
                    print(f"\nProcessing follow-up {followup_id} for user {username}")
                    print(f"Created at {created_at}, last message date: {last_message_date}")
                    
                    message_sent = False
                    
                    # Try WhatsApp first if phone number is available
                    if phone_number:
                        # Format phone number before sending
                        formatted_phone = format_phone_number(phone_number)
                        print(f"Attempting to send WhatsApp message to {formatted_phone}")
                        message_sent = self.send_whatsapp_message(formatted_phone, message)
                    
                    # If no phone number available, skip this follow-up
                    if not phone_number:
                        print(f"No phone number available for user {username}, skipping follow-up")
                    
                    # Update follow-up status based on message success
                    if message_sent:
                        print(f"Message sent successfully for follow-up {followup_id}")
                        self.mark_followup_completed(followup_id)
                        results["successful"] += 1
                    else:
                        print(f"Failed to send message for follow-up {followup_id}")
                        results["failed"] += 1
                    
                except Exception as e:
                    print(f"Error processing follow-up {followup['id']}: {str(e)}")
                    results["failed"] += 1
                    continue
            
            print(f"\nFinished processing follow-ups:")
            print(f"Total: {results['total']}")
            print(f"Successful: {results['successful']}")
            print(f"Failed: {results['failed']}")
            
            return results
            
        except Exception as e:
            print(f"Error processing follow-ups: {str(e)}")
            return {"total": 0, "successful": 0, "failed": 0}
    
    def send_whatsapp_message(self, phone_number: str, message: str) -> bool:
        """Send WhatsApp message using whatsapp module"""
        try:
            from whatsapp import send_message as send_whatsapp
            return send_whatsapp(phone_number, message)
        except Exception as e:
            print(f"Error sending WhatsApp message: {str(e)}")
            return False 