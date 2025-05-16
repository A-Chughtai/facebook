from apify_client import ApifyClient
import time
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API token from environment variables
TOKEN = os.getenv('APIFY_API_TOKEN')
if not TOKEN:
    raise ValueError("APIFY_API_TOKEN not found in environment variables")

ACTOR_ID = 'apify/facebook-groups-scraper'  # replace with your actual actor ID


def main() -> None:
    # Initialize client
    client = ApifyClient(token=TOKEN)

    # Run the actor with optional input (customize if your actor needs it)
    run = client.actor(ACTOR_ID).call(run_input={
        # Provide your input here, if required
        "startUrls": [
            {"url": "https://www.facebook.com/groups/1018882276887018"},
            {"url": "https://www.facebook.com/groups/leagueoflegendsfangroup"},
        ]
    })

    print(f"Run started. ID: {run['id']}, status: {run['status']}")

    # Wait for run to finish (optional if you just want to fetch output once it's done)
    while run['status'] not in ['SUCCEEDED', 'FAILED', 'ABORTED']:
        time.sleep(5)
        run = client.run(run['id']).get()
        print(f"Waiting... current status: {run['status']}")

    # Once finished, get dataset items (output)
    dataset_items = client.dataset(run['defaultDatasetId']).list_items().items

    # Save to a local JSON file
    output_file = 'facebook_scraped_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset_items, f, ensure_ascii=False, indent=4)

    print(f"Data saved to {output_file}")



if __name__ == '__main__':
    main()
