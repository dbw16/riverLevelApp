import requests
import datetime
from decimal import Decimal
import logging
from riverLevels.level import Level
from riverLevels.table import batch_update_level_db
import sys

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)
LOGGER.addHandler(log_handler)


def get_water_levels(endpoint: str) -> [Level]:
    r = requests.get(endpoint)

    data = [
        line.strip().strip(",") for line in r.text.splitlines() if "[Date.UTC(" in line
    ]

    levels = []
    for d in data:
        date = d.strip("[").split(")")[0].split("(")[1].split(",")
        date = [int(x) for x in date]
        parsed_date = datetime.datetime(
            year=date[0], month=date[1] + 1, day=date[2], hour=date[3], minute=date[4]
        )
        height = d.split(",")[6].strip("]")
        levels.append(Level(parsed_date, Decimal(height)))

    return levels


def handler(event, context):
    LOGGER.info("started handler")
    endpoints = {
        "Braid": "https://www.hydrometcloud.de/Rivers_Agency/SiteController?type=stationgraph&siteid=111"
                 "&groupid=364&dataId=174784&daterange=1&predefval=lastXdays&days=2",
        # "Tullynewey": "https://www.hydrometcloud.de/Rivers_Agency/SiteController?type=stationgraph&siteid=1247&groupid"
        #               "=364&daterange=1&&predefval=lastXdays&days=10",
    }
    for river, endpoint in endpoints.items():
        levels = get_water_levels(endpoint)
        LOGGER.info(f"received levels for {river} adding to table")
        batch_update_level_db(river, levels)


if __name__ == "__main__":
    handler("", "")
