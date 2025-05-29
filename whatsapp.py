from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import re

# List of user agents
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
]

def get_random_user_agent():
    return random.choice(user_agents)

def human_delay():
    time.sleep(random.uniform(0.5, 2.0))

def type_like_human(element, text):
    text = text.replace('\n', ' ')
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.01, 0.05))
    human_delay()

def setup_driver():
    options = Options()
    options.add_argument(f"user-agent={get_random_user_agent()}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Use absolute path for session directory
    user_data_path = os.path.abspath("whatsapp_session")
    options.add_argument(f"--user-data-dir={user_data_path}")
    options.add_argument("--profile-directory=Default")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    return driver

# Global driver instance
_driver = None

def get_driver():
    global _driver
    if _driver is None:
        _driver = setup_driver()
    return _driver

def send_message(phone_number: str, message: str) -> bool:
    """
    Send a WhatsApp message using Selenium.
    Maintains the same interface as the previous implementation.
    
    Args:
        phone_number (str): Phone number with country code (e.g., +1234567890)
        message (str): Message to send
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        # Ensure phone number is properly formatted
        phone_number = str(phone_number)
        # Remove all non-digit characters
        phone_number = re.sub(r'\D', '', phone_number)
        
        driver = get_driver()
        
        # Go to the chat page
        url = f"https://web.whatsapp.com/send?phone={phone_number}"
        driver.get(url)

        print("Waiting for WhatsApp chat to load...")
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-tab='10' and @contenteditable='true']"))
        )

        # Get the message input box
        message_box = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@data-tab='10' and @contenteditable='true']"))
        )
        message_box.click()
        type_like_human(message_box, message)

        # Wait for the Send button and click it
        send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']"))
        )
        send_button.click()

        print("Message sent successfully!")
        time.sleep(2)
        
        # Close the current window but keep the session
        driver.close()
        
        
        return True

    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        # Close the window even if there's an error
        try:
            driver.close()
            driver.switch_to.new_window('tab')
        except:
            pass
        return False

def cleanup():
    """Clean up the driver when the program exits"""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except:
            pass
        _driver = None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Send WhatsApp messages using Selenium')
    parser.add_argument('--phone', required=True, help='Phone number with country code (e.g., +1234567890)')
    parser.add_argument('--message', required=True, help='Message to send')
    
    args = parser.parse_args()
    
    try:
        send_message(args.phone, args.message)
    finally:
        cleanup()
