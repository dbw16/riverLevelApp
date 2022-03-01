import datetime
import logging
import sys
from riverLevels.level import Level
from riverLevels.river import River

from bokeh.models.widgets import DateRangeSlider
from bokeh.layouts import layout
from bokeh.plotting import figure, output_file, save, show
from bokeh.embed import file_html
from bokeh.resources import CDN
from riverLevels.table import get_past_data_dynamo

import boto3
from botocore.exceptions import ClientError

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)
LOGGER.addHandler(log_handler)


def draw_graph_levels(levels: [Level], river: River) -> str:
    now = datetime.datetime.now()
    two_weeks_ago = now - datetime.timedelta(days=14)

    p = figure(
        title=f"{river.name} Gauge, current level: {levels[-1].level}m at {levels[-1].time}" + "\n" + river.description,
        x_axis_type="datetime",
        x_axis_label="Date",
        y_axis_label="Height",
        x_range=(two_weeks_ago, now),
    )
    p.line(
        x=[l.time for l in levels],
        y=[l.level for l in levels],
        legend_label="Level",
        line_width=2,
    )

    p.line(
        x=[l.time for l in levels],
        y=[river.low_water for _ in levels],
        legend_label="Low Water",
        line_color="green",
        line_width=1,
    )
    p.line(
        x=[l.time for l in levels],
        y=[river.high_water for _ in levels],
        legend_label="High Water",
        line_color="red",
        line_width=1,
    )

    date_range_slider = DateRangeSlider(
        title="Date Range",
        start=levels[0].time,
        end=datetime.datetime.now(),
        value=(two_weeks_ago, datetime.datetime.now()),
        step=1,
    )

    date_range_slider.js_link("value", p.x_range, "start", attr_selector=0)
    date_range_slider.js_link("value", p.x_range, "end", attr_selector=1)

    layouts = layout([[p], [date_range_slider]], sizing_mode="stretch_width")

    return file_html(layouts, CDN, river.name)


def draw_special_graph_levels(
        river_one_name, river_one_levels, river_two_name, river_two_levels
) -> str:
    now = datetime.datetime.now()
    two_weeks_ago = now - datetime.timedelta(days=14)

    p = figure(
        title=f"Glenarm Gauge",
        x_axis_type="datetime",
        x_axis_label="Date",
        y_axis_label="Height",
        x_range=(two_weeks_ago, now),
    )

    p.line(
        x=[l.time for l in river_one_levels],
        y=[l.level for l in river_one_levels],
        legend_label=river_one_name,
        line_width=2,
        line_color="blue",
    )

    p.line(
        x=[l.time for l in river_two_levels],
        y=[l.level for l in river_two_levels],
        legend_label=river_two_name,
        line_width=2,
        line_color="black",
    )

    p.line(
        x=[l.time for l in river_two_levels],
        y=[1 for _ in river_two_levels],
        legend_label="Low Water",
        line_color="green",
        line_width=1,
    )
    p.line(
        x=[l.time for l in river_two_levels],
        y=[2 for _ in river_two_levels],
        legend_label="High Water",
        line_color="red",
        line_width=1,
    )

    date_range_slider = DateRangeSlider(
        title="Date Range",
        start=river_two_levels[0].time,
        end=datetime.datetime.now(),
        value=(two_weeks_ago, datetime.datetime.now()),
        step=1,
    )

    date_range_slider.js_link("value", p.x_range, "start", attr_selector=0)
    date_range_slider.js_link("value", p.x_range, "end", attr_selector=1)

    layouts = layout([[p], [date_range_slider]], sizing_mode="stretch_width")

    return file_html(layouts, CDN, "Glenarm")


def get_secret(secret_stored_location):
    session = boto3.session.Session()
    client = session.client("secretsmanager")
    response = client.get_secret_value(
        SecretId=secret_stored_location,
    )
    return response["SecretString"]


def single_graphs(rivers: [River]) -> str:
    html = []
    for river in rivers:
        levels = get_past_data_dynamo(
            river.name, datetime.datetime.now() - datetime.timedelta(days=50)
        )
        html.append(draw_graph_levels(levels, river=river))
    return "\n".join(html)


def copy_html_to_server(html: str):
    with open("/tmp/index.php", "w") as f:
        f.write(html)

    from paramiko import SSHClient
    from paramiko import AutoAddPolicy
    from scp import SCPClient

    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    ssh.load_system_host_keys()
    ssh.connect(
        hostname="salmon.maths.tcd.ie",
        username="dawillia",
        password=get_secret("scp_key"),
    )

    # SCPCLient takes a paramiko transport as an argument
    scp = SCPClient(ssh.get_transport())

    scp.put("/tmp/index.php", remote_path="www/")
    ssh.exec_command("chmod 644 www/index.php")
    scp.close()


def handler(event, context):
    copy_html_to_server(
        single_graphs(
            rivers=[
                River("Flesk", 0.7, 2.0),
                River(
                    "Braid",
                    0.7,
                    1.2,
                    description="Can use this river to tell us the level of the Glenarm",
                ),
                River(
                    "Annalecka", .8, 2.0,
                    description="no clue on high or low water marks https://goo.gl/maps/kZXv3Emq7UNiMok28 ",
                ),
                River(
                    "Dargle", .8, 2.0,
                    description="Gauge currently broken, high and lower markers are a guess",
                )
            ]
        )
    )

    # river_one_name = "Braid"
    # river_one_levels = get_past_data_dynamo(river_one_name, datetime.datetime.now() - datetime.timedelta(days=50))
    # river_two_name = "Tullynewey"
    # river_two_levels = get_past_data_dynamo(river_two_name, datetime.datetime.now() - datetime.timedelta(days=50))
    #
    # special_graph = draw_special_graph_levels(river_one_name, river_one_levels, river_two_name, river_two_levels )
    #
    #
    # with open("../index.html", "w") as f:
    #     f.write(special_graph)

    # html.append(draw_special_graph_levels())


if __name__ == "__main__":
    handler("", "")
