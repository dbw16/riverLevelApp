import requests
import datetime
from decimal import Decimal
import logging
from riverLevels.level import Level
from riverLevels.table import batch_update_level_db
import sys
from dateutil import parser


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)
LOGGER.addHandler(log_handler)


def get_water_levels(endpoint: str) -> [Level]:
    r = requests.get(endpoint)

    rows  = [line.split(",") for line in r.text.splitlines()[1:]]

    levels = []
    for row in rows:
        date = parser.parse(row[0])
        height = row[1]
        try:
            levels.append(Level(date, Decimal(height)))
        except:
            levels.append(Level(date, Decimal(0)))
    return levels


def handler(event, context):
    LOGGER.info("started handler")
    endpoints = {
        "Dargle": "https://waterlevel.ie/data/day/10051_0001.csv"
    }
    for river, endpoint in endpoints.items():
        levels = get_water_levels(endpoint)
        LOGGER.info(f"received levels for {river} adding to table")
        batch_update_level_db(river, levels)


if __name__ == "__main__":
    handler("", "")
