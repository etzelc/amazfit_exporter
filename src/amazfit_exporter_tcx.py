#!/usr/bin/python3
import sqlite3
import sys
from time import ctime
from datetime import datetime
import time as t
import os
from lxml import etree
import amazfit_exporter_config

TRAINING_CENTER_DATABASE_NAMESPACE = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
TRAINING_CENTER_DATABASE_LOCATION = "https://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd"

XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

TDC_NSMAP = {
    None: TRAINING_CENTER_DATABASE_NAMESPACE,
    "xsi": XML_SCHEMA_NAMESPACE}

TDC_SCHEMA_LOCATION = TRAINING_CENTER_DATABASE_NAMESPACE + " " +\
    TRAINING_CENTER_DATABASE_LOCATION

# Map Amazfit DB to TCX values
SPORT_MAPPING = {
    None: "Other",
    1: "Running", # Running
    2: "Running", # Walking
    3: "Running", # Trail Running
    4: "Running", # Indoor Running
    5: "Biking" # Biking
}

# FIXME remove or do
def local_date_to_utc(date):
    return datetime.utcfromtimestamp(int(date / 1000))

def create_element(tag, text=None, namespace=None):
    namespace = TDC_NSMAP[namespace]
    tag = "{%s}%s" % (namespace, tag)
    element = etree.Element(tag, nsmap=TDC_NSMAP)
    if text is not None:
        element.text = text
    return element

def create_sub_element(parent, tag, text=None, namespace=None):
    element = create_element(tag, text, namespace)
    parent.append(element)
    return element

def create_tcd_document():
    document = create_element("TrainingCenterDatabase")
    document.set(("{%s}" % XML_SCHEMA_NAMESPACE) + "schemaLocation", TDC_SCHEMA_LOCATION)
    document = etree.ElementTree(document)
    return document

def add_activity(parent_element, activity):
    # Try to map Amazfit types to TCX types. If there's no match use "Other"
    sport = SPORT_MAPPING.get(activity['type'], "Other")
    # Use track_id (the starting time) as identifier
    identifier = local_date_to_utc(activity['track_id'])

    activity_element = create_sub_element(parent_element, "Activity")

    activity_element.set("Sport", sport)
    create_sub_element(activity_element, "Id", identifier.isoformat() + "Z")

    # Currently every activity has only one lap
    add_lap(activity_element, activity)

    add_creator(activity_element)

def add_lap(parent_element, activity):
    start_time = activity['start_time']
    end_time = activity['end_time']
    total_time = (end_time - start_time) // 1000
    total_distance = 0
    calories = activity['calorie'] / 1000
    intensity = "Active"
    trigger_method = "Manual"

    lap_element = create_sub_element(parent_element, "Lap")
    lap_element.set("StartTime", local_date_to_utc(start_time).isoformat() + "Z")

    create_sub_element(lap_element, "TotalTimeSeconds", str(total_time))
    create_sub_element(lap_element, "DistanceMeters", str(total_distance))
    create_sub_element(lap_element, "Calories", str(int(calories)))
    create_sub_element(lap_element, "Intensity", intensity)
    create_sub_element(lap_element, "TriggerMethod", trigger_method)

    track_element = create_sub_element(lap_element, "Track")

    gen = (trackpoint for trackpoint in amazfit_exporter_config.trackpoints if trackpoint['track_id'] == activity['track_id'])
    for trackpoint in gen:
        add_trackpoint(track_element, trackpoint)

def add_trackpoint(parent_element, trackpoint):
    trackpoint_element = create_sub_element(parent_element, "Trackpoint")
    # reduce precision of timestamp by setting last three digits to zero to find corresponding heart rate
    timestamp_str = str(trackpoint['timestamp'])
    imprecise_timestamp = int(timestamp_str[0:len(timestamp_str)-3] + "000")
     
    latitude = trackpoint['latitude']
    longitude = trackpoint['longitude']
    altitude = trackpoint['altitude']

    raw_timestamp = trackpoint['track_id'] + imprecise_timestamp
    heart_rate = amazfit_exporter_config.heart_rate_data.get(raw_timestamp, None)
    timestamp = local_date_to_utc(raw_timestamp)

    create_sub_element(trackpoint_element, "Time", timestamp.isoformat() + "Z")

    position_element = create_sub_element(trackpoint_element, "Position")
    create_sub_element(position_element, "LatitudeDegrees", str(latitude))
    create_sub_element(position_element, "LongitudeDegrees", str(longitude))

    # only use realistic altitude values
    if altitude > -20:
        create_sub_element(trackpoint_element, "AltitudeMeters", str(altitude))

    if heart_rate is not None:
        heart_rate_element = create_sub_element(trackpoint_element, "HeartRateBpm")
        create_sub_element(heart_rate_element, "Value", str(int(heart_rate[0])))

def add_creator(parent_element):
    creator_element = create_sub_element(parent_element, "Creator")
    qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "type")
    creator_element.set(qname, "Device_t")

    create_sub_element(creator_element, "Name", "Huami Amazfit Pace")
    create_sub_element(creator_element, "UnitId", "0")
    create_sub_element(creator_element, "ProductID", "0")

    version_element = create_sub_element(creator_element, "Version")
    create_sub_element(version_element, "VersionMajor", "0")
    create_sub_element(version_element, "VersionMinor", "0")

def add_author(parent_element):
    author_element = create_sub_element(parent_element, "Author")
    qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "type")
    author_element.set(qname, "Application_t")

    create_sub_element(author_element, "Name", "Amazfit Exporter")

    build_element = create_sub_element(author_element, "Build")

    version_element = create_sub_element(build_element, "Version")
    create_sub_element(version_element, "VersionMajor", "0")
    create_sub_element(version_element, "VersionMinor", "0")

    create_sub_element(author_element, "LangID", "en")
    create_sub_element(author_element, "PartNumber", "000-00000-00")

def document_to_string(document):
    return etree.tostring(document.getroot(), xml_declaration=True, encoding="UTF-8", pretty_print=True)

def db_to_tcx(dest):
    for activity in amazfit_exporter_config.activities:
        document = create_tcd_document()
        element = create_sub_element(document.getroot(), "Activities")
        add_activity(element, activity)
        add_author(document.getroot())
        identifier = activity['track_id']
        with open(os.path.join(dest, str(identifier) + ".tcx"), 'wb') as output_file:
            print(t.strftime(str(identifier) + ' activity: ' + str(activity['type']) + ':' + SPORT_MAPPING.get(activity['type'])))
            output_file.write(document_to_string(document))
            output_file.close()
