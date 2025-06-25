from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import time
import random
import os
import re
from datetime import datetime
from alert import send_alert
from typing import Optional, Tuple
import json

# List of user agents
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
]

# Global instances
_playwright = None
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None

# Session management
SESSION_FILE = "whatsapp_session.json"

def get_random_user_agent() -> str:
    return random.choice(user_agents)

def human_delay() -> None:
    time.sleep(random.uniform(0.5, 2.0))

def type_like_human(page: Page, text: str) -> None:
    time.sleep(6)
    # Clear existing text using CTRL+A and Backspace
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    human_delay()
    
    text = text.replace('\n', ' ')
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.01, 0.05))
    human_delay()

def save_session_info():
    """Save session information to a JSON file"""
    session_info = {
        "timestamp": datetime.now().isoformat(),
        "user_agent": get_random_user_agent()
    }
    
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_info, f)
        print("Session information saved successfully")
    except Exception as e:
        print(f"Error saving session information: {str(e)}")

def load_session_info() -> Optional[dict]:
    """Load session information from JSON file"""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading session information: {str(e)}")
    return None

def setup_browser() -> Tuple[Browser, BrowserContext]:
    """Initialize and return a browser instance with appropriate settings."""
    global _playwright
    
    if _playwright is None:
        _playwright = sync_playwright().start()
    
    try:
        # Check if we have a saved session
        session_info = load_session_info()
        
        # Check if running on Railway (environment variable)
        is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
        
        browser = _playwright.chromium.launch_persistent_context(
            user_data_dir=os.path.abspath("browser_data"),
            headless=is_railway,  # Use headless mode on Railway
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ],
            user_agent=session_info.get('user_agent', get_random_user_agent()) if session_info else get_random_user_agent(),
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation'],
            ignore_default_args=['--enable-automation'],
            color_scheme='light',
            accept_downloads=True,
            record_video_dir=None,
            record_har_path=None
        )
        
        # Create a new page and wait for it to be ready
        page = browser.new_page()
        page.wait_for_load_state('networkidle')
        
        return browser, page
    except Exception as e:
        print(f"Error setting up browser: {str(e)}")
        cleanup()
        raise

def get_browser() -> Tuple[Browser, BrowserContext]:
    """Get or create browser instance with retry logic."""
    global _browser, _context
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if _browser is None or _context is None:
                _browser, _context = setup_browser()
            return _browser, _context
        except Exception as e:
            retry_count += 1
            print(f"Error getting browser (attempt {retry_count}/{max_retries}): {str(e)}")
            cleanup()
            if retry_count == max_retries:
                raise
            time.sleep(2)  # Wait before retrying

def wait_for_qr_scan(page: Page, timeout: int = 400) -> bool:
    """
    Wait for the QR code to be scanned and WhatsApp Web to be ready.
    
    Args:
        page: Playwright Page instance
        timeout: Maximum time to wait in seconds
        
    Returns:
        bool: True if QR code was scanned successfully, False if timeout occurred
    """
    time.sleep(10)
    try:
        # First check if already logged in
        try:
            # Use a more reliable text-based selector that doesn't depend on class names
            page.wait_for_selector('//*[text()="Chats" or text()="Loading your chats" or text()="End-to-end encrypted" or @title="New chat" or @data-icon="new-chat-outline" or @data-icon="new-chat-online"]', timeout=3000)
            print("Already logged in")
            # Save session info since we're already logged in
            save_session_info()
            return True
        except:
            print("Not logged in - proceeding with QR code check")
        
        # Check for QR code presence
        qr_code_texts = [
            "Log in to WhatsApp Web",
            "WhatsApp Web",
            "Scan QR code",
            "To use WhatsApp on your computer",
            "Log in"
        ]
        
        # Find which text is present on the page
        found_text = None
        for text in qr_code_texts:
            try:
                # Wait for element containing the text
                element = page.wait_for_selector(f'//*[contains(text(), "{text}")]', timeout=2000)
                if element:
                    found_text = text
                    print(f"QR code page detected: Found text '{text}'")
                    
                    # Take screenshot
                    screenshot_dir = "screenshots"
                    os.makedirs(screenshot_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = os.path.join(screenshot_dir, f"qr_code_{timestamp}.png")
                    page.screenshot(path=screenshot_path)
                    print(f"Screenshot saved to {screenshot_path}")
                    
                    send_alert(
                        subject="WhatsApp Web QR Code Detected",
                        message=f"Scan the QR code ASAP",
                        recipient=os.getenv("ALERT_RECIPIENT"),
                        attachment_path=screenshot_path
                    )
                    break
            except:
                continue
        
        if found_text is None:
            print("No QR code text patterns found on the page")
            return False
            
        # Start time for timeout
        start_time = time.time()
        
        # While loop to check if the text remains present
        while time.time() - start_time < timeout:
            try:
                # Check if the text is still present
                element = page.wait_for_selector(f'//*[contains(text(), "{found_text}")]', timeout=1000)
                if element:
                    # If text is still present, wait a bit and check again
                    time.sleep(1)
                    continue
            except:
                # If text is no longer present, QR code was likely scanned
                print("QR code text no longer present - likely scanned")
                # Wait longer for the page to fully load
                print("Waiting for page to load completely...")
                time.sleep(20)  # Increased wait time
                try:
                    # Verify Chats text or aria-label is present
                    page.wait_for_selector('//*[text()="Chats" or @aria-label="WhatsApp"]', timeout=60000)
                    print("Chats text or WhatsApp aria-label detected - QR code scanned successfully!")
                    # Save session info after successful QR scan
                    save_session_info()
                    return True
                except:
                    print("Chats text or WhatsApp aria-label not found after QR code text disappeared")
                    return False
        
        print("Timeout waiting for QR code to be scanned")
        return False
        
    except Exception as e:
        print("Error during QR code scanning:", str(e))
        return False

def send_message(phone_number: str, message: str) -> bool:
    """
    Send a WhatsApp message using Playwright.
    Maintains the same interface as the previous implementation.
    
    Args:
        phone_number (str): Phone number with country code (e.g., +1234567890)
        message (str): Message to send
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    browser = None
    page = None
    try:
        # Ensure phone number is properly formatted
        phone_number = str(phone_number)
        # Remove all non-digit characters
        phone_number = re.sub(r'\D', '', phone_number)
        
        browser, page = get_browser()
        
        # First, go to the main WhatsApp Web page
        page.goto("https://web.whatsapp.com", wait_until="networkidle")
        page.wait_for_load_state('networkidle')
        
        # Wait for QR code to be scanned
        if not wait_for_qr_scan(page):
            print("Failed to scan QR code within timeout period")
            time.sleep(5)
            cleanup()
            return False
        
        # Wait 5 seconds and press ESC to bypass any UI compoments
        time.sleep(5)
        try:
            page.locator('button:has-text("Continue")').click()
            print("Clicked the Continue button.")
        except Exception as e:
            print("Could not find or click the Continue button:", e)
            
        # Now go to the specific chat
        url = f"https://web.whatsapp.com/send?phone={phone_number}"
        page.goto(url, wait_until="networkidle")
        page.wait_for_load_state('networkidle')

        # Wait 5 seconds and press ESC to bypass any UI compoments
        time.sleep(5)
        try:
            page.locator('button:has-text("Continue")').click()
            print("Clicked the Continue button.")
        except Exception as e:
            print("Could not find or click the Continue button:", e)

        page.wait_for_selector('div[data-tab="10"][contenteditable="true"]', timeout=150000)
        
        
        url = f"https://web.whatsapp.com/send?phone={phone_number}"
        page.goto(url, wait_until="networkidle")
        page.wait_for_load_state('networkidle')

        # Get the message input box and type message
        message_box = page.locator('div[data-tab="10"][contenteditable="true"]')
        message_box.click()
        type_like_human(page, message)

        # Wait for the Send button and click it
        send_button = page.locator('button[aria-label="Send"]')
        send_button.click()

        print("Message sent successfully!")
        time.sleep(2)
        
        # Wait 5 seconds before closing the browser
        time.sleep(5)
        cleanup()
        return True

    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        # Wait 5 seconds before closing the browser on failure
        time.sleep(5)
        cleanup()
        return False

def cleanup() -> None:
    """Clean up the browser when the program exits"""
    global _playwright, _browser, _context
    
    if _context is not None:
        try:
            _context.close()
        except:
            pass
        _context = None
        
    if _browser is not None:
        try:
            _browser.close()
        except:
            pass
        _browser = None
        
    if _playwright is not None:
        try:
            _playwright.stop()
        except:
            pass
        _playwright = None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Send WhatsApp messages using Playwright')
    parser.add_argument('--phone', required=True, help='Phone number with country code (e.g., +1234567890)')
    parser.add_argument('--message', required=True, help='Message to send')
    
    args = parser.parse_args()
    
    try:
        send_message(args.phone, args.message)
    finally:
        pass  # cleanup is now handled inside send_message