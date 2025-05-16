import pywhatkit
import argparse
from datetime import datetime, timedelta

def send_message(phone_number: str, message: str):
    # Get current time
    now = datetime.now()
    
    # Calculate time 2 minutes from now to ensure WhatsApp Web is ready
    send_time = now + timedelta(minutes=2)
    
    # Extract hour and minute
    hour = send_time.hour
    minute = send_time.minute
    
    try:
        # Send message
        pywhatkit.sendwhatmsg(
            phone_number,
            message,
            
            hour,
            minute,
            wait_time=50,  # Wait 15 seconds for WhatsApp Web to load
            tab_close=True,  # Close the tab after sending
            close_time=50  # Wait 3 seconds before closing
        )
        print(f"Message scheduled to be sent at {hour}:{minute:02d}")
        return True
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Send WhatsApp messages using pywhatkit')
    parser.add_argument('--phone', required=True, help='Phone number with country code (e.g., +1234567890)')
    parser.add_argument('--message', required=True, help='Message to send')
    
    args = parser.parse_args()
    
    # Validate phone number format
    if not args.phone.startswith('+'):
        print("Error: Phone number must start with country code (e.g., +1234567890)")
        return
    
    send_message(args.phone, args.message)

if __name__ == "__main__":
    main()
