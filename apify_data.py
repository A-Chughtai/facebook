from apify_client import ApifyClient
import time
import json
from dotenv import load_dotenv
import os
import logging
import gspread
from google.oauth2.service_account import Credentials
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Get API token and sheet ID from environment variables
TOKEN = os.getenv('APIFY_API_TOKEN')
SHEET_ID = os.getenv('FACEBOOK_GROUPS_SHEET_ID')

if not TOKEN:
    raise ValueError("APIFY_API_TOKEN not found in environment variables")
if not SHEET_ID:
    raise ValueError("GOOGLE_SHEET_ID not found in environment variables")

ACTOR_ID = 'apify/facebook-groups-scraper'

def is_valid_facebook_url(url):
    """Validate if the URL is a valid Facebook group URL"""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ['http', 'https'] and
            'facebook.com' in parsed.netloc and
            '/groups/' in parsed.path
        )
    except:
        return False

def read_group_urls():
    """Read Facebook group URLs from Google Sheets"""
    try:
        # Set up Google Sheets credentials
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(
            'credentials.json',
            scopes=scopes
        )
        
        gc = gspread.authorize(credentials)
        
        # Open the spreadsheet and get the first worksheet
        sheet = gc.open_by_key(SHEET_ID).sheet1
        
        # Find the "URLs" column
        headers = sheet.row_values(1)
        try:
            url_col_index = headers.index('URLs') + 1  # +1 because gspread is 1-indexed
        except ValueError:
            raise ValueError("Column 'URLs' not found in the sheet")
        
        # Get all values from the URLs column
        urls = sheet.col_values(url_col_index)
        
        # Remove the header row and filter out empty values and comments
        urls = [url.strip() for url in urls[1:] if url.strip() and not url.strip().startswith('#')]
        
        # Validate and format URLs
        valid_urls = []
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            if is_valid_facebook_url(url):
                valid_urls.append({"url": url})
            else:
                logging.warning(f"Invalid Facebook group URL found: {url}")
        
        if not valid_urls:
            raise ValueError("No valid Facebook group URLs found in the Google Sheet")
        
        logging.info(f"Found {len(valid_urls)} valid Facebook group URLs")
        return valid_urls
    except Exception as e:
        raise Exception(f"Error reading group URLs from Google Sheets: {str(e)}")

def main() -> None:
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        # Initialize client
        client = ApifyClient(token=TOKEN)
        
        # Read group URLs from Google Sheets
        start_urls = read_group_urls()
        logging.info(f"Loaded {len(start_urls)} group URLs from Google Sheets")
        
        # Run the actor with the URLs from Google Sheets
        run = client.actor(ACTOR_ID).call(run_input={
            "startUrls": start_urls
        })
        
        logging.info(f"Run started. ID: {run['id']}, status: {run['status']}")
        
        # Wait for run to finish
        while run['status'] not in ['SUCCEEDED', 'FAILED', 'ABORTED']:
            time.sleep(5)
            run = client.run(run['id']).get()
            logging.info(f"Waiting... current status: {run['status']}")
        
        # Get dataset items (output)
        dataset_items = client.dataset(run['defaultDatasetId']).list_items().items
        
        # Save to a local JSON file
        output_file = 'facebook_scraped_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset_items, f, ensure_ascii=False, indent=4)
        
        logging.info(f"Data saved to {output_file}")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise

if __name__ == '__main__':
    main()
