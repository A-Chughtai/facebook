import os
from datetime import datetime
from followup_handler import FollowupHandler
from message import send_messenger_message
from whatsapp import send_message as send_whatsapp_message
import logging
import re
from typing import List

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

def setup_logging():
    """Set up logging configuration"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"followup_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return log_file

def process_followups():
    """Process all pending follow-ups and send messages"""
    # Set up logging
    log_file = setup_logging()
    logging.info("Starting follow-up processing...")
    
    # Initialize follow-up handler
    followup_handler = FollowupHandler()
    
    # Get pending follow-ups
    pending_followups = followup_handler.get_pending_followups()
    logging.info(f"Found {len(pending_followups)} pending follow-ups")
    
    for followup in pending_followups:
        followup_id = followup['id']
        user_id = followup['user_id']
        username = followup['username']
        phone_number = followup['phone_number']
        message = followup['message']
        created_at = followup['created_at']
        last_message_date = followup['last_message_date']
        
        logging.info(
            f"Processing follow-up {followup_id} for user {username} "
            f"(created at {created_at}, last message date: {last_message_date})"
        )
        
        try:
            message_sent = False
            
            # Try WhatsApp first if phone number is available
            if phone_number:
                # Format phone number before sending
                formatted_phone = format_phone_number(phone_number)
                if not formatted_phone.startswith('+'):
                    formatted_phone = '+' + formatted_phone
                
                logging.info(f"Attempting to send WhatsApp message to {formatted_phone}")
                message_sent = send_whatsapp_message(formatted_phone, message)
            
            # If WhatsApp fails or no phone number, try Messenger
            if not message_sent:
                logging.info(f"WhatsApp message failed or no phone number, trying Messenger for user {username}")
                message_sent = send_messenger_message(user_id, message)
            
            # Update follow-up status based on message success
            if message_sent:
                logging.info(f"Message sent successfully for follow-up {followup_id}")
                # Mark as completed instead of deleting
                followup_handler.mark_followup_completed(followup_id)
            else:
                logging.warning(f"Failed to send message for follow-up {followup_id}")
                # Entry remains in Excel as it's still pending
            
        except Exception as e:
            logging.error(f"Error processing follow-up {followup_id}: {str(e)}")
            continue
    
    logging.info("Finished processing all follow-ups")
    logging.info(f"Log file created: {log_file}")

if __name__ == "__main__":
    process_followups() 