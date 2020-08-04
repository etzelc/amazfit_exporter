#!/usr/bin/python3
import sqlite3
import sys
from time import ctime
from datetime import datetime
import time as t
import os
from lxml import etree
import amazfit_exporter_config

GPX_NAMESPACE = "http://www.topografix.com/GPX/1/1"
GPX_LOCATION = "https://www.topografix.com/GPX/1/1/gpx.xsd"
GPX_TRACK_POINT_EXTENSION_NAMESPACE = "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
GPX_TRACK_POINT_EXTENSION = "{%s}" % GPX_TRACK_POINT_EXTENSION_NAMESPACE
GPX_TRACK_POINT_EXTENSION_LOCATION = "https://www8.garmin.com/xmlschemas/TrackPointExtensionv1.xsd"

XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
    
GPX_NSMAP = {
    None: GPX_NAMESPACE,
    "xsi": XML_SCHEMA_NAMESPACE,
    "gpxtpx": GPX_TRACK_POINT_EXTENSION_NAMESPACE}

GPX_SCHEMA_LOCATION = GPX_NAMESPACE + " " +\
    GPX_LOCATION + " " +\
    GPX_TRACK_POINT_EXTENSION_NAMESPACE + " " +\
    GPX_TRACK_POINT_EXTENSION_LOCATION
    
# Map Amazfit DB to strings
SPORT_MAPPING = {
    None: "Other",
    1: "Running", # Running
    2: "Walking", # Walking
    3: "Trail Running", # Trail Running
    4: "Indoor Running", # Indoor Running
    5: "Biking" # Biking
}

# FIXME remove or do
def local_date_to_utc(date):
    return datetime.utcfromtimestamp(int(date / 1000))

def create_element(tag, text=None, namespace=None):
    namespace = GPX_NSMAP[namespace]
    tag = "{%s}%s" % (namespace, tag)
    element = etree.Element(tag, nsmap=GPX_NSMAP)
    if text is not None:
        element.text = text
    return element

def create_sub_element(parent, tag, text=None, namespace=None):
    element = create_element(tag, text, namespace)
    parent.append(element)
    return element
    
def create_gpx_document():
    document = create_element("gpx")
    document.set("version", "1.1")
    document.set("creator", "Amazfit Exporter")
    document.set(("{%s}" % XML_SCHEMA_NAMESPACE) + "schemaLocation", GPX_SCHEMA_LOCATION)
    document = etree.ElementTree(document)
    return document

def add_track(parent_element, activity):
    sport = SPORT_MAPPING.get(activity['type'], "Other")
    # Use track_id (the starting time) as identifier
    identifier = local_date_to_utc(activity['track_id'])

    track_element = create_sub_element(parent_element, "trk")

    name_element  = create_sub_element(track_element, "name", sport + " at " + identifier.isoformat())

    # Currently every activity has only one segment
    add_segment(track_element, activity)

def add_segment(parent_element, activity):

    track_element = create_sub_element(parent_element, "trkseg")

    gen = (trackpoint for trackpoint in amazfit_exporter_config.trackpoints if trackpoint['track_id'] == activity['track_id'])
    for trackpoint in gen:
        add_trackpoint(track_element, trackpoint)

def add_trackpoint(parent_element, trackpoint):
    trackpoint_element = create_sub_element(parent_element, "trkpt")
    # reduce precision of timestamp by setting last three digits to zero to find corresponding heart rate
    timestamp_str = str(trackpoint['timestamp'])
    imprecise_timestamp = int(timestamp_str[0:len(timestamp_str)-3] + "000")
     
    latitude = trackpoint['latitude']
    longitude = trackpoint['longitude']
    altitude = trackpoint['altitude']

    raw_timestamp = trackpoint['track_id'] + imprecise_timestamp
    heart_rate = amazfit_exporter_config.heart_rate_data.get(raw_timestamp, None)
    timestamp = local_date_to_utc(raw_timestamp)

    trackpoint_element.set("lat", str(latitude))
    trackpoint_element.set("lon", str(longitude))
    
    # only use realistic altitude values
    if altitude > -20:
        create_sub_element(trackpoint_element, "ele", str(altitude))

    create_sub_element(trackpoint_element, "time", timestamp.isoformat() + "Z")

    extensions_element = create_sub_element(trackpoint_element, "extensions")
    
    trackpointextension_element = create_sub_element(extensions_element, "TrackPointExtension", namespace="gpxtpx")

    if heart_rate is not None:
        heart_rate_element = create_sub_element(trackpointextension_element, "hr", str(int(heart_rate[0])), "gpxtpx")

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

def db_to_gpx(dest):
    print("GPX export:")
    for activity in amazfit_exporter_config.activities:
        document = create_gpx_document()
        add_track(document.getroot(), activity)
        identifier = activity['track_id']
        with open(os.path.join(dest, str(identifier) + ".gpx"), 'wb') as output_file:
            print(t.strftime("\tDate: " + local_date_to_utc(identifier).isoformat() + ", id " + str(identifier) + ', type: ' + str(activity['type']) + ':' + SPORT_MAPPING.get(activity['type'])))
            output_file.write(document_to_string(document))
            output_file.close()
