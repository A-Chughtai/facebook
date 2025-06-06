import smtplib
import ssl
from email.message import EmailMessage
import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

def send_alert(
    subject: str,
    message: str,
    recipient: str,
    sender_email: Optional[str] = os.getenv("EMAIL_USER"),
    sender_password: Optional[str] = os.getenv("EMAIL_PASS"),
    attachment_path: Optional[str] = None
) -> bool:
    """
    Send an email alert using SMTP.
    
    Args:
        subject (str): The subject of the email
        message (str): The content of the email
        recipient (str): The recipient's email address
        sender_email (str, optional): The sender's email address. Defaults to the configured Gmail address
        sender_password (str, optional): The sender's app password. Defaults to the configured app password
        attachment_path (str, optional): Path to file to attach to the email
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Create email message
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient
        msg.set_content(message)
        
        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                file_data = f.read()
                file_name = os.path.basename(attachment_path)
                msg.add_attachment(
                    file_data,
                    maintype='image',
                    subtype='png',
                    filename=file_name
                )
        
        # Gmail SMTP server configuration
        smtp_server = "smtp.gmail.com"
        port = 465  # For SSL
        
        # Create a secure SSL context and send the email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"Alert email sent successfully to {recipient}")
        return True
        
    except Exception as e:
        print(f"Failed to send alert email: {str(e)}")
        return False

# Example usage
if __name__ == "__main__":
    # Example of sending a test alert
    send_alert(
        subject="Test Alert",
        message="This is a test alert message.",
        recipient="example@gmail.com"
    ) 