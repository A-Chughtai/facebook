from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import argparse
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
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

def type_like_human(element, text):
    time.sleep(random.uniform(4, 8))
    # Clear existing text using CTRL+A and Backspace
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.BACKSPACE)
    human_delay()

    """Type text like a human with random delays between keystrokes"""
    # Replace newlines with spaces to prevent line breaks
    text = text.replace('\n', ' ')
    
    for char in text:
        element.send_keys(char)
        # Random delay between keystrokes (50-150ms)
        time.sleep(random.uniform(0.04, 0.09))
    
    # Add a small delay after typing
    human_delay()

def setup_driver():
    options = Options()
    options.add_argument(f"user-agent={get_random_user_agent()}")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
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

def send_messenger_message(driver, user_id: str, message: str):
    try:
        # Navigate to Facebook
        driver.get("https://www.facebook.com")
        human_delay()  # Wait for page load
        
        # Login
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        human_delay()  # Wait before typing
        type_like_human(email_field, email)
        
        password_field = driver.find_element(By.ID, "pass")
        human_delay()  # Wait before typing password
        type_like_human(password_field, password)
        
        # Click login button instead of pressing Enter
        login_button = driver.find_element(By.NAME, "login")
        human_delay()  # Wait before clicking
        login_button.click()
        
        # Wait for login to complete and check for auth platform redirect
        time.sleep(random.uniform(9, 12))
        
        url = driver.current_url
        print(url)
        # Check for auth platform redirect
        if not re.match(r'^https?://(?:www\.)?facebook\.com/(?:\?sk=welcome)?/?$', url):
            send_alert(
                subject="Messenger Auth required",
                message=f"Please authenticate the Messenger Platform ASAP. The program has paused. Press ENTER on console after auth",
                recipient=os.getenv("ALERT_RECIPIENT")
            )
            print("Facebook has redirected to the authentication platform.")
            print("Please complete the authentication manually.")
            input("Press Enter after you have completed the authentication...")
        
        # Navigate to messenger
        driver.get(f"https://www.facebook.com/messages/t/{user_id}")
        time.sleep(random.uniform(4, 6))  # Wait for messenger to load
        
        # Check for and click the Continue button if it exists
        try:
            # Try multiple selectors for the Continue button
            continue_button = None
            selectors = [
                "//div[@aria-label='Continue' and @role='button']",
                "//div[contains(@class, 'x1i10hfl') and .//span[contains(text(), 'Continue')]]",
                "//div[@role='button' and .//span[contains(@class, 'x1lliihq') and contains(text(), 'Continue')]]"
            ]
            
            for selector in selectors:
                try:
                    continue_button = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if continue_button:
                        break
                except:
                    continue
            
            if continue_button:
                # Try regular click first
                try:
                    human_delay()  # Wait before clicking continue
                    continue_button.click()
                except:
                    # If regular click fails, try JavaScript click
                    try:
                        driver.execute_script("arguments[0].click();", continue_button)
                    except:
                        # If JavaScript click fails, try moving to element and clicking
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_to_element(continue_button).click().perform()
                
                time.sleep(random.uniform(2, 3))  # Wait for the button click to take effect
            else:
                print("Continue button not found with any selector")
        except Exception as e:
            print(f"Error handling Continue button: {str(e)}")
            print("Proceeding with message...")
        
        # Find message input and send message
        message_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='textbox']"))
        )
        human_delay()  # Wait before typing message
        type_like_human(message_input, message)
        
        # Wait before sending
        human_delay()
        message_input.send_keys(Keys.RETURN)
        
        # Wait for message to be sent
        time.sleep(random.uniform(2, 4))
        return True
    except Exception as e:
        print(f"Error sending Messenger message: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Send messages via Messenger')
    parser.add_argument('--user_id', required=True, help='User ID for Messenger')
    parser.add_argument('--message', required=True, help='Message to send')
    
    args = parser.parse_args()
    
    driver = setup_driver()
    
    try:
        success = send_messenger_message(driver, args.user_id, args.message)
        # Exit with appropriate status code
        sys.exit(0 if success else 1)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
