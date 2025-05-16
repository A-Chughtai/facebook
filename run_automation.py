import subprocess
import os
import sys
from datetime import datetime
import logging
import time
import locale

def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Set up logging
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
        # Set environment variables for proper encoding
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"
        
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=my_env,
            check=True
        )
        
        # Log the output
        if result.stdout:
            logging.info(f"Output from {script_name}:\n{result.stdout}")
        
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running {script_name}:")
        if e.stdout:
            logging.error(f"Output: {e.stdout}")
        if e.stderr:
            logging.error(f"Error: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error running {script_name}: {str(e)}")
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
    else:
        logging.info(f"{json_file} not found")

def main():
    # Set up logging
    log_filename = setup_logging()
    logging.info("Starting automation process...")
    
    # List of scripts to run in sequence
    scripts = [
        "apify_data.py",
        "process_posts.py",
        "send_messages.py"
    ]
    
    # Run each script
    for script in scripts:
        if not run_script(script):
            logging.error(f"Automation failed at {script}")
            return False
    
    # Cleanup
    cleanup()
    
    logging.info("Automation completed successfully!")
    logging.info(f"Log file created: {log_filename}")
    return True

if __name__ == "__main__":
    try:
        # Set console encoding to UTF-8
        if sys.platform == 'win32':
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Automation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        sys.exit(1) 