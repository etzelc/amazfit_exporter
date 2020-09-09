#!/usr/bin/python3
import logging
import sqlite3
import pathlib
from datetime import datetime
from lxml import etree
import amazfit_exporter_config
from amazfit_exporter_tcx import db_to_tcx
from amazfit_exporter_gpx import db_to_gpx

# global variable for the database cursor
cursor = None

logger = logging.getLogger(__name__)

# FIXME remove or do
def local_date_to_utc(date):
    return datetime.utcfromtimestamp(int(date / 1000))

def get_activities_data(begin_time):
    # Use begin_time to load only data beyond that time
    cursor.execute('SELECT track_id, start_time, end_time, calorie, type, content FROM sport_summary WHERE track_id >=' + str(begin_time) + ' AND (type BETWEEN 1 AND 15)')
    return cursor.fetchall()

def get_track_data(begin_time):
    cursor.execute('SELECT track_id, cast(latitude as text) as latitude, cast(longitude as text) as longitude, altitude, timestamp FROM location_data WHERE track_id>=' + str(begin_time) + ' AND point_type > 0')
    return cursor.fetchall()

def get_heart_rate_data(begin_time):
    cursor.execute('SELECT time, rate, step_count from heart_rate where time >=' + str(begin_time))
    heart_rates = {}
    for hr in cursor.fetchall():
        if not hr['time'] in heart_rates:
            heart_rates[hr['time']] = hr[1:]
    return heart_rates

def document_to_string(document):
    return etree.tostring(document.getroot(), xml_declaration=True, encoding="UTF-8", pretty_print=True)

def start_export(db,dest,begin_time):
    logger.info("Started export")

    new_update_begin_time = -1

    # Connect to the sport database
    try:
        db_uri = pathlib.Path(db).as_uri() + "?mode=ro"
        db_connection = sqlite3.connect(db_uri, uri=True)
        db_connection.row_factory = sqlite3.Row
        with db_connection:
            global cursor
            global activities
            global trackpoints
            global heart_rate_data
            cursor = db_connection.cursor()
            amazfit_exporter_config.activities = get_activities_data(begin_time)
            amazfit_exporter_config.trackpoints = get_track_data(begin_time)
            amazfit_exporter_config.heart_rate_data = get_heart_rate_data(begin_time)
            db_to_tcx(dest)
            db_to_gpx(dest)
            # search for highest track_id as new update begin time
            new_update_begin_time = max([act[0] for act in amazfit_exporter_config.activities], default=-1) 
            logger.info("Highest track id found %d", new_update_begin_time)
    except sqlite3.OperationalError:
        logger.error("Error: Database not readable! Check database: '%s'", db)
    
    logger.info("Finished export")
    return new_update_begin_time
