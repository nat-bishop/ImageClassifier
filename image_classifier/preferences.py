import json
import logging
import os
from pathlib import Path

# Store preferences in the user's home directory under .image_classifier
PREFERENCES_DIR = os.path.expanduser('~/.image_classifier')
PREFERENCES_PATH = os.path.join(PREFERENCES_DIR, 'preferences.json')

# Default preferences
DEFAULT_PREFERENCES = {
    "num_colors": 4,
    "classifier": "GaussianMixture",
    "show_welcome_tour": True,  # Whether to show the welcome tour
    "tour_completed": False     # Whether the user has completed the tour
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def store_preferences(data: dict) -> None:
    """Store preferences to disk, creating the directory if it doesn't exist."""
    try:
        # Create the preferences directory if it doesn't exist
        os.makedirs(PREFERENCES_DIR, exist_ok=True)
        
        with open(PREFERENCES_PATH, 'w') as f:
            logging.info(f"Storing preferences at: {PREFERENCES_PATH}")
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to store preferences: {e}")


def load_preferences() -> dict:
    """Load preferences from disk, returning defaults if no file exists or on error."""
    try:
        if os.path.exists(PREFERENCES_PATH):
            with open(PREFERENCES_PATH, 'r') as f:
                preferences = json.load(f)
                # Validate and merge with defaults
                validated_preferences = DEFAULT_PREFERENCES.copy()
                validated_preferences.update(preferences)
                logging.info(f'Successfully loaded preferences from {PREFERENCES_PATH}')
                return validated_preferences
    except Exception as e:
        logging.error(f"Failed to load preferences: {e}")
    
    logging.info('Using default preferences')
    return DEFAULT_PREFERENCES.copy()
