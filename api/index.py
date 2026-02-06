import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    # Attempt to import the Flask app
    from server.app import app
    logging.info("Successfully imported Flask app")
except Exception as e:
    logging.error(f"Error importing Flask app: {str(e)}")
    logging.error(f"Stack trace: {sys.exc_info()[2]}")
    # Re-raise the exception to ensure Vercel reports the error
    raise

