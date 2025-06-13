from playwright.sync_api import sync_playwright
import time
import random
import argparse
from dotenv import load_dotenv
import os
import sys
from alert import send_alert
import re

# Load environment variables
load_dotenv()

# Facebook credentials from environment variables
email = os.getenv('FB_EMAIL')
password = os.getenv('FB_PASSWORD')

# List of user agents to rotate
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
]

def get_random_user_agent():
    return random.choice(user_agents)

def human_delay():
    """Add a random delay to simulate human behavior"""
    time.sleep(random.uniform(0.5, 2.0))

def type_like_human(page, selector, text):
    """Type text like a human with random delays between keystrokes"""
    time.sleep(random.uniform(4, 8))
    
    # Clear existing text
    page.fill(selector, '')
    human_delay()

    # Replace newlines with spaces to prevent line breaks
    text = text.replace('\n', ' ')
    
    # Type character by character with random delays
    for char in text:
        page.type(selector, char, delay=random.uniform(40, 90))
    
    # Add a small delay after typing
    human_delay()

def send_messenger_message(user_id: str, message: str):
    with sync_playwright() as p:
        # Check if running on Railway (environment variable)
        is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
        
        # Launch browser with stealth mode
        browser = p.chromium.launch(
            headless=is_railway,  # Use headless mode on Railway
            args=['--start-maximized']
        )
        
        # Create a new context with custom user agent
        context = browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Create a new page
        page = context.new_page()
        
        try:
            # Navigate to Facebook
            page.goto("https://www.facebook.com")
            human_delay()
            
            # Login
            page.fill("#email", email)
            human_delay()
            page.fill("#pass", password)
            human_delay()
            
            # Click login button
            page.click("button[name='login']")
            
            # Wait for login to complete and check for auth platform redirect
            time.sleep(random.uniform(9, 12))
            
            url = page.url
            print(url)
            
            # Check for auth platform redirect
            if not re.match(r'^https?://(?:www\.)?facebook\.com/(?:\?sk=welcome*)?/?$', url):
                send_alert(
                    subject="Messenger Auth required",
                    message=f"Please authenticate the Messenger Platform ASAP. The program has paused. Press ENTER on console after auth",
                    recipient=os.getenv("ALERT_RECIPIENT")
                )
                print("Facebook has redirected to the authentication platform.")
                print("Please complete the authentication manually.")
                input("Press Enter after you have completed the authentication...")
            
            # Navigate to messenger
            page.goto(f"https://www.facebook.com/messages/t/{user_id}")
            time.sleep(random.uniform(4, 6))
            
            # Handle Continue button if it exists
            try:
                continue_button = page.locator("//div[@aria-label='Continue' and @role='button']").first
                if continue_button.is_visible():
                    human_delay()
                    continue_button.click()
                    time.sleep(random.uniform(2, 3))
            except Exception as e:
                print(f"Error handling Continue button: {str(e)}")
                print("Proceeding with message...")
            
            # Find message input and send message
            message_input = page.locator("[role='textbox']").first
            type_like_human(page, "[role='textbox']", message)
            
            # Send message
            human_delay()
            page.keyboard.press("Enter")
            
            # Wait for message to be sent
            time.sleep(random.uniform(2, 4))
            return True
            
        except Exception as e:
            print(f"Error sending Messenger message: {str(e)}")
            return False
        finally:
            browser.close()

def main():
    parser = argparse.ArgumentParser(description='Send messages via Messenger')
    parser.add_argument('--user_id', required=True, help='User ID for Messenger')
    parser.add_argument('--message', required=True, help='Message to send')
    
    args = parser.parse_args()
    
    try:
        success = send_messenger_message(args.user_id, args.message)
        # Exit with appropriate status code
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
