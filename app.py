import os
import sys
from datetime import datetime
import logging
import time
import locale
import json
import pandas as pd
from pathlib import Path
from followup_handler import FollowupHandler
from run_data_collection import run_data_collection
from send_messages import process_unanswered_posts
from process_posts import process_posts
from whatsapp_routine import run_whatsapp_routine
import pytz

def setup_logging():
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    log_filename = f"logs/automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_filename

def cleanup():
    logging.info("Cleaning up...")
    json_file = "facebook_scraped_data.json"
    if os.path.exists(json_file):
        try:
            os.remove(json_file)
            logging.info(f"Deleted {json_file}")
        except Exception as e:
            logging.error(f"Error deleting {json_file}: {str(e)}")

def run_automation():
    """Run the automation process"""
    logging.info("Starting automation process...")
    try:
        process_unanswered_posts()
        cleanup()
        logging.info("Automation completed successfully!")
        return True
    except Exception as e:
        logging.error(f"Error during automation: {str(e)}")
        return False

def run_followups():
    """Run the follow-up processing"""
    logging.info("Starting follow-up processing...")
    try:
        followup_handler = FollowupHandler()
        results = followup_handler.process_followups()
        
        if results["successful"] > 0 or results["failed"] > 0:
            logging.info(f"Follow-up processing completed. Successful: {results['successful']}, Failed: {results['failed']}")
        else:
            logging.info("No follow-ups to process.")
        return True
    except Exception as e:
        logging.error(f"Error processing follow-ups: {str(e)}")
        return False

def run_data_collection_process():
    """Run the data collection process"""
    logging.info("Starting data collection process...")
    try:
        success = run_data_collection()
        if success:
            logging.info("Data collection completed successfully!")
        else:
            logging.error("Data collection failed")
        return success
    except Exception as e:
        logging.error(f"Error during data collection: {str(e)}")
        return False

def run_process_posts():
    """Run the process_posts.py script"""
    logging.info("Starting post processing...")
    try:
        success = process_posts()
        if success:
            cleanup()
            logging.info("Post processing completed successfully!")
        else:
            logging.error("Post processing failed")
        return success
    except Exception as e:
        logging.error(f"Error during post processing: {str(e)}")
        return False

def get_dubai_time():
    """Get the current time in Dubai timezone (UTC+4)"""
    dubai_tz = pytz.timezone('Asia/Dubai')
    return datetime.now(dubai_tz)

def main():
    # Set up logging
    setup_logging()
    logging.info("Starting continuous automation process...")
    
    iteration = 1
    # Track last run date for Followups and WhatsApp Routine
    last_run = {
        "Followups": None,
        "WhatsApp Routine": None
    }
    
    while True:
        logging.info(f"\n{'='*50}")
        logging.info(f"Starting iteration {iteration}")
        logging.info(f"{'='*50}\n")
        
        # Get current Dubai time
        dubai_now = get_dubai_time()
        dubai_hour = dubai_now.hour
        dubai_minute = dubai_now.minute
        today_str = dubai_now.strftime('%Y-%m-%d')

        # Run all processes in sequence
        processes = [
            ("Data Collection", run_data_collection_process),
            ("Process Posts", run_process_posts),
            ("Automation", run_automation),
        ]

        # Add Followups and WhatsApp Routine only if in time window and not run today
        if 9 <= dubai_hour < 12 or (dubai_hour == 11 and dubai_minute <= 55):
            # Followups
            if last_run["Followups"] != today_str:
                processes.append(("Followups", run_followups))
                last_run["Followups"] = today_str
            # WhatsApp Routine
            if last_run["WhatsApp Routine"] != today_str:
                processes.append(("WhatsApp Routine", run_whatsapp_routine))
                last_run["WhatsApp Routine"] = today_str

        for process_name, process_func in processes:
            logging.info(f"\nStarting {process_name}...")
            success = process_func()
            if not success:
                logging.error(f"{process_name} failed, but continuing with next process...")
        
        logging.info(f"\n{'='*50}")
        logging.info(f"Iteration {iteration} completed")
        logging.info("Waiting 30 minutes before next iteration...")
        logging.info(f"{'='*50}\n")
        
        # Wait for 15 minutes
        time.sleep(15 * 60)  # 30 minutes in seconds
        iteration += 1

if __name__ == "__main__":
    main() 
