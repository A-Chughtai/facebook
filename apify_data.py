from apify_client import ApifyClient
import time
import json
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

# Get API token from environment variables
TOKEN = os.getenv('APIFY_API_TOKEN')
if not TOKEN:
    raise ValueError("APIFY_API_TOKEN not found in environment variables")

ACTOR_ID = 'apify/facebook-groups-scraper'

def read_group_urls(file_path='facebook_groups.txt'):
    """Read Facebook group URLs from a text file"""
    try:
        with open(file_path, 'r') as file:
            # Read lines and filter out empty lines and comments
            urls = [line.strip() for line in file if line.strip() and not line.strip().startswith('#')]
        
        if not urls:
            raise ValueError(f"No valid URLs found in {file_path}")
        
        # Convert URLs to the format expected by Apify
        return [{"url": url} for url in urls]
    except FileNotFoundError:
        raise FileNotFoundError(f"Group URLs file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading group URLs: {str(e)}")

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
        
        # Read group URLs from file
        start_urls = read_group_urls()
        logging.info(f"Loaded {len(start_urls)} group URLs from file")
        
        # Run the actor with the URLs from file
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
