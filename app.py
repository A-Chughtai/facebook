import streamlit as st
import subprocess
import os
import sys
from datetime import datetime
import logging
import time
import locale
import json
import pandas as pd
from pathlib import Path
from process_followups import process_followups
from followup_handler import FollowupHandler
from run_data_collection import run_data_collection

# Page config
st.set_page_config(
    page_title="Facebook Automation",
    page_icon="🤖",
    layout="centered"
)

# Initialize session state
if 'running' not in st.session_state:
    st.session_state.running = False
if 'followup_running' not in st.session_state:
    st.session_state.followup_running = False
if 'data_collection_running' not in st.session_state:
    st.session_state.data_collection_running = False
if 'process_posts_running' not in st.session_state:
    st.session_state.process_posts_running = False
if 'process_sequence' not in st.session_state:
    st.session_state.process_sequence = [
        "send_messages.py"
    ]

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

def run_script(script_name):
    logging.info(f"Running {script_name}...")
    try:
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"
        
        # Set console encoding to UTF-8 for Windows
        if sys.platform == 'win32':
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=my_env,
            check=True
        )
        
        if result.stdout:
            logging.info(f"Output from {script_name}:\n{result.stdout}")
        
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Error running {script_name}:"
        if e.stdout:
            error_msg += f"\nOutput: {e.stdout}"
        if e.stderr:
            error_msg += f"\nError: {e.stderr}"
        logging.error(error_msg)
        return False
    except Exception as e:
        error_msg = f"Unexpected error running {script_name}: {str(e)}"
        logging.error(error_msg)
        return False

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
    st.session_state.running = True
    
    # Set up logging
    log_filename = setup_logging()
    logging.info("Starting automation process...")
    
    # Run each script
    for script in st.session_state.process_sequence:
        if not run_script(script):
            error_msg = f"Automation failed at {script}"
            logging.error(error_msg)
            st.session_state.running = False
            return False
    
    # Cleanup
    cleanup()
    
    success_msg = "Automation completed successfully!"
    logging.info(success_msg)
    st.session_state.running = False
    return True

def run_followups():
    """Run the follow-up processing"""
    st.session_state.followup_running = True
    
    # Set up logging
    log_filename = setup_logging()
    logging.info("Starting follow-up processing...")
    
    try:
        # Initialize follow-up handler
        followup_handler = FollowupHandler()
        
        # Process follow-ups
        results = followup_handler.process_followups()
        
        if results["successful"] > 0 or results["failed"] > 0:
            success_msg = f"Follow-up processing completed. Successful: {results['successful']}, Failed: {results['failed']}"
        else:
            success_msg = "No follow-ups to process."
            
        logging.info(success_msg)
        st.session_state.followup_running = False
        return True
    except Exception as e:
        error_msg = f"Error processing follow-ups: {str(e)}"
        logging.error(error_msg)
        st.session_state.followup_running = False
        return False

def run_data_collection_process():
    """Run the data collection process"""
    st.session_state.data_collection_running = True
    
    # Set up logging
    log_filename = setup_logging()
    logging.info("Starting data collection process...")
    
    try:
        # Run data collection
        success = run_data_collection()
        
        if success:
            success_msg = "Data collection completed successfully!"
            logging.info(success_msg)
        else:
            error_msg = "Data collection failed"
            logging.error(error_msg)
        
        st.session_state.data_collection_running = False
        return success
    except Exception as e:
        error_msg = f"Error during data collection: {str(e)}"
        logging.error(error_msg)
        st.session_state.data_collection_running = False
        return False

def run_process_posts():
    """Run the process_posts.py script"""
    st.session_state.process_posts_running = True
    
    # Set up logging
    log_filename = setup_logging()
    logging.info("Starting post processing...")
    
    try:
        # Run process_posts.py
        success = run_script("process_posts.py")
        
        if success:
            # Perform cleanup
            cleanup()
            success_msg = "Post processing completed successfully!"
            logging.info(success_msg)
        else:
            error_msg = "Post processing failed"
            logging.error(error_msg)
        
        st.session_state.process_posts_running = False
        return success
    except Exception as e:
        error_msg = f"Error during post processing: {str(e)}"
        logging.error(error_msg)
        st.session_state.process_posts_running = False
        return False

# Main UI
st.title("🤖 Facebook Automation")

# Create four columns for the buttons
col1, col2, col3, col4 = st.columns(4)

# Check if any process is running
any_process_running = (
    st.session_state.data_collection_running or
    st.session_state.process_posts_running or
    st.session_state.running or
    st.session_state.followup_running
)

with col1:
    if not st.session_state.data_collection_running:
        if st.button(
            "Run Data Collection",
            type="primary",
            use_container_width=True,
            disabled=any_process_running and not st.session_state.data_collection_running
        ):
            run_data_collection_process()
    else:
        st.warning("Data collection is running...")

with col2:
    if not st.session_state.process_posts_running:
        if st.button(
            "Process Posts",
            type="primary",
            use_container_width=True,
            disabled=any_process_running and not st.session_state.process_posts_running
        ):
            run_process_posts()
    else:
        st.warning("Post processing is running...")

with col3:
    if not st.session_state.running:
        if st.button(
            "Start Automation",
            type="primary",
            use_container_width=True,
            disabled=any_process_running and not st.session_state.running
        ):
            run_automation()
    else:
        st.warning("Automation is running...")

with col4:
    if not st.session_state.followup_running:
        if st.button(
            "Process Follow-ups",
            type="secondary",
            use_container_width=True,
            disabled=any_process_running and not st.session_state.followup_running
        ):
            run_followups()
    else:
        st.warning("Follow-up processing is running...") 