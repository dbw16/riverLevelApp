import csv
import datetime
from zipfile import ZipFile
import io
from io import BytesIO

from dateutil import parser
import requests
from decimal import *
import logging
from riverLevels.level import Level
from riverLevels.table import batch_update_level_db, get_past_data_dynamo
from riverLevels.table import update_level_db

import sys

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)
LOGGER.addHandler(log_handler)

# FLESK_GAUGE_NUMBER = 22039
# ANNALECKA_GAUGE_NUMBER = 09026
# FLESK_PAST_DATA = "https://epawebapp.epa.ie/Hydronet/output/internet/stations/LIM/22039/S/complete_15min.zip"


def get_latest_level(gauge_id: str) -> Level:
    gauge_number = gauge_id.split("/")[-1]
    response = requests.get(
        "https://epawebapp.epa.ie/Hydronet/output/internet/layers/10/index.json"
    )
    gauges = response.json()
    for gauge in gauges:
        if gauge["metadata_station_no"] == str(gauge_number):
            parsed_time = parser.parse(gauge["L1_timestamp"])
            return Level(
                level=Decimal(gauge["L1_ts_value"])
                - Decimal(gauge["L1_station_gauge_datum"]),
                time=parsed_time,
            )
    print("could not find gauge...")


def get_past_data_epa(gauge_id: int, n_last_readings: int) -> [Level]:
    LOGGER.info("requesting endpoint")
    endpoint = f"https://epawebapp.epa.ie/Hydronet/output/internet/stations/{gauge_id}/S/complete_15min.zip"
    response = requests.get(endpoint, stream=True)
    print(response.status_code)
    print(endpoint)
    LOGGER.info("reading in zip content endpoint")
    zipfile = ZipFile(BytesIO(response.content))
    lines = [line.decode('utf-8') for line in zipfile.open("complete_15min.csv").readlines()]
    rows = [line.split(" ") for line in lines if "#" not in line]

    levels = []
    LOGGER.info("creating levels list")
    for row in rows[-n_last_readings:]:
        date = row[0]
        time = row[1].split(";")[0]
        parsed_time = datetime.datetime(
            year=int(date.split("-")[0]),
            month=int(date.split("-")[1]),
            day=int(date.split("-")[2]),
            hour=int(time.split(":")[0]),
            minute=int(time.split(":")[1]),
        )

        try:
            levels.append(Level(time=parsed_time, level=Decimal(row[1].split(";")[1])))
        except:
            pass

    return levels


def handler(event, context):
    LOGGER.info(event)

    rivers = {"Flesk": "LIM/22039",
              "Annalecka": "DUB/09026"}

    if "current" in event:
        LOGGER.info("current event")
        for river_name, gauge_id in rivers.items():
            levels = get_latest_level(gauge_id)
            update_level_db(river_name, levels)

    elif "past" in event:
        LOGGER.info("past event")
        for river_name, gauge_id in rivers.items():
            LOGGER.info(f"getting levels from epa for {river_name}")
            epa_levels = get_past_data_epa(gauge_id, 3000)
            # get the most resent river levels in our table
            LOGGER.info("getting levels from dynamo table")
            dynamo_levels = get_past_data_dynamo(
                river_name, datetime.datetime.now() - datetime.timedelta(days=50)
            )
            dynamo_times = {level.time for level in dynamo_levels}

            # to save doing extra work we only try to write new level readings to db
            new_river_levels = [
                level for level in epa_levels if level.time not in dynamo_times
            ]

            if new_river_levels:
                LOGGER.info(f"Updating db with new {river_name} epa.zip data ")
                batch_update_level_db(river_name, new_river_levels)
            else:
                LOGGER.info(f"No new data from {river_name} epa.zip")

    else:
        LOGGER.info("did nothing, could not parse event payload")


if __name__ == "__main__":
    handler("current", "")
