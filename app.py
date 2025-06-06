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
import subprocess

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

def run_setup():
    """Run the setup.py script"""
    logging.info("Starting setup process...")
    try:
        excel_files = ["db/social_media.xlsx", "db/followups.xlsx"]
        files_exist = all(os.path.exists(file) for file in excel_files)
        
        if files_exist:
            logging.info("Excel files already exist. Skipping setup.")
            return True
        
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(
            [sys.executable, "setup.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=my_env,
            check=True
        )
        
        if result.stdout:
            logging.info(f"Setup output:\n{result.stdout}")
        
        logging.info("Setup completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = "Error running setup:"
        if e.stdout:
            error_msg += f"\nOutput: {e.stdout}"
        if e.stderr:
            error_msg += f"\nError: {e.stderr}"
        logging.error(error_msg)
        return False
    except Exception as e:
        logging.error(f"Error during setup: {str(e)}")
        return False

def main():
    # Set up logging
    setup_logging()
    logging.info("Starting continuous automation process...")
    
    # Run setup once at the beginning
    if not run_setup():
        logging.error("Initial setup failed. Exiting...")
        return
    
    iteration = 1
    while True:
        logging.info(f"\n{'='*50}")
        logging.info(f"Starting iteration {iteration}")
        logging.info(f"{'='*50}\n")
        
        # Run all processes in sequence
        processes = [
            ("Data Collection", run_data_collection_process),
            ("Process Posts", run_process_posts),
            ("Automation", run_automation),
            ("Followups", run_followups)
        ]
        
        for process_name, process_func in processes:
            logging.info(f"\nStarting {process_name}...")
            success = process_func()
            if not success:
                logging.error(f"{process_name} failed, but continuing with next process...")
        
        logging.info(f"\n{'='*50}")
        logging.info(f"Iteration {iteration} completed")
        logging.info("Waiting 30 minutes before next iteration...")
        logging.info(f"{'='*50}\n")
        
        # Wait for 30 minutes
        time.sleep(30 * 60)  # 30 minutes in seconds
        iteration += 1

if __name__ == "__main__":
    main() 