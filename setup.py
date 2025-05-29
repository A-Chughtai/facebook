import os
import subprocess
import sys
import logging
from datetime import datetime

def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Set up logging
    log_filename = f"logs/setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_filename

def create_directories():
    """Create necessary directories for the project"""
    directories = [
        "db",           # Main database directory
        "logs"          # Logs directory
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f"Created directory: {directory}")
        else:
            logging.info(f"Directory already exists: {directory}")

def run_excel_setup():
    """Run the Excel creation script"""
    logging.info("Running Excel setup script...")
    try:
        # Set environment variables for proper encoding
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"
        
        # Run the Excel creation script
        result = subprocess.run(
            [sys.executable, "create_excel.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=my_env,
            check=True
        )
        
        # Log the output
        if result.stdout:
            logging.info(f"Excel setup output:\n{result.stdout}")
        
        return True
    except subprocess.CalledProcessError as e:
        logging.error("Error running Excel setup:")
        if e.stdout:
            logging.error(f"Output: {e.stdout}")
        if e.stderr:
            logging.error(f"Error: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error during Excel setup: {str(e)}")
        return False

def main():
    # Set up logging
    log_filename = setup_logging()
    logging.info("Starting project setup...")
    
    try:
        # Create necessary directories
        create_directories()
        
        # Run Excel setup
        if not run_excel_setup():
            logging.error("Excel setup failed!")
            return False
        
        logging.info("Project setup completed successfully!")
        logging.info(f"Log file created: {log_filename}")
        return True
        
    except Exception as e:
        logging.error(f"Setup failed: {str(e)}")
        return False

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
        logging.info("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        sys.exit(1) 