import subprocess
import os
import sys
from datetime import datetime
import logging

def setup_logging():
    """Set up logging configuration"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"data_collection_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return log_file

def run_script(script_name: str) -> bool:
    """Run a Python script and return True if successful"""
    try:
        # Get the full path of the script
        script_path = os.path.join(os.path.dirname(__file__), script_name)
        
        # Check if script exists
        if not os.path.exists(script_path):
            logging.error(f"Script not found: {script_path}")
            return False
        
        # Run the script
        logging.info(f"Running script: {script_name}")
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        
        # Log output
        if result.stdout:
            logging.info(f"Script output:\n{result.stdout}")
        if result.stderr:
            logging.error(f"Script errors:\n{result.stderr}")
        
        # Check if script was successful
        if result.returncode == 0:
            logging.info(f"Script completed successfully: {script_name}")
            return True
        else:
            logging.error(f"Script failed with return code {result.returncode}: {script_name}")
            return False
            
    except Exception as e:
        logging.error(f"Error running script {script_name}: {str(e)}")
        return False

def run_data_collection():
    # Set up logging
    log_filename = setup_logging()
    logging.info("Starting data collection process...")
    
    # List of scripts to run in sequence
    scripts = [
        "apify_data.py"
    ]
    
    # Run each script
    for script in scripts:
        if not run_script(script):
            logging.error(f"Data collection failed at {script}")
            return False
    
    logging.info("Data collection completed successfully!")
    logging.info(f"Log file created: {log_filename}")
    return True

if __name__ == "__main__":
    try:
        # Set console encoding to UTF-8
        if sys.platform == 'win32':
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        
        success = run_data_collection()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Data collection interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        sys.exit(1) 