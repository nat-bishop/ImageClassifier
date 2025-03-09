import json
import logging
import os

PREFERENCES_PATH = os.path.expanduser('~/preferences.json')
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def store_preferences(data: dict) -> None:
    with open(PREFERENCES_PATH, 'w') as f:
        logging.info(f"storeing preferences at: {PREFERENCES_PATH}")
        json.dump(data, f)

def load_preferences() -> dict:
    if os.path.exists(PREFERENCES_PATH):
        with open(PREFERENCES_PATH, 'r') as f:
            logging.info(f'succesfully loaded preferences from {PREFERENCES_PATH}')
            return json.load(f)
    logging.info('didnt find preferences, loading defaults')
    return {"num_colors": 9, "classifier": "KMeans"}
