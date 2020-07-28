#!/usr/bin/python3
import sqlite3
import sys
from time import ctime
from datetime import datetime
import time as t
import os
from lxml import etree
import amazfit_exporter_config
from amazfit_exporter_tcx import db_to_tcx
from amazfit_exporter_gpx import db_to_gpx

# global variable for the database cursor
cursor = None

# FIXME remove or do
def local_date_to_utc(date):
    return datetime.utcfromtimestamp(int(date / 1000))

def get_activities_data(begin_time):
    # Use begin_time to load only data beyond that time
    cursor.execute('SELECT track_id, start_time, end_time, calorie, type, content FROM sport_summary WHERE track_id >=' + str(begin_time) + ' AND (type BETWEEN 1 AND 5)')
    return cursor.fetchall()

def get_track_data(begin_time):
    cursor.execute('SELECT track_id, latitude, longitude, altitude, timestamp FROM location_data WHERE track_id>=' + str(begin_time) + ' AND point_type > 0')
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
    new_update_begin_time = -1

    # Connect to the sport database
    db_connection = sqlite3.connect(db)
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
        # identifier = amazfit_exporter_config.activities[,]
        identifier = 0
        for activity in amazfit_exporter_config.activities:
            if identifier < activity['track_id']:
                identifier = activity['track_id']
        if new_update_begin_time < identifier:
            new_update_begin_time = identifier 
    return new_update_begin_time
