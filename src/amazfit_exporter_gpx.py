#!/usr/bin/python3
import collections
from time import ctime
from datetime import datetime
import logging
import os
from lxml import etree
import amazfit_exporter_config

GPX_NAMESPACE = "http://www.topografix.com/GPX/1/1"
GPX_LOCATION = "https://www.topografix.com/GPX/1/1/gpx.xsd"

TRACK_POINT_EXTENSION_NAMESPACE = "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
TRACK_POINT_EXTENSION = "{%s}" % TRACK_POINT_EXTENSION_NAMESPACE
TRACK_POINT_EXTENSION_LOCATION = "https://www8.garmin.com/xmlschemas/TrackPointExtensionv1.xsd"

GPXDATA_EXTENSION_NAMESPACE = "http://www.cluetrust.com/XML/GPXDATA/1/0"
GPXDATA_EXTENSION = "{%s}" %  GPXDATA_EXTENSION_NAMESPACE
GPXDATA_EXTENSION_LOCATION = "https://www.cluetrust.com/Schemas/gpxdata10.xsd"

XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
    
GPX_NSMAP = {
    None: GPX_NAMESPACE,
    "xsi": XML_SCHEMA_NAMESPACE,
    "gpxtpx": TRACK_POINT_EXTENSION_NAMESPACE,
    "gpxdata": GPXDATA_EXTENSION_NAMESPACE}

GPX_SCHEMA_LOCATION = GPX_NAMESPACE + " " +\
    GPX_LOCATION + " " +\
    TRACK_POINT_EXTENSION_NAMESPACE + " " +\
    TRACK_POINT_EXTENSION_LOCATION + " " +\
    GPXDATA_EXTENSION_NAMESPACE + " " +\
    GPXDATA_EXTENSION_LOCATION

# Trackpoints are recorded every 1-3 seconds
# The last 20 values should be sufficient to calculate cadence
STEPS_FOR_CADENCE = collections.deque(maxlen=20)

sport_type = None

logger = logging.getLogger(__name__)

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
    global sport_type
    sport_type = amazfit_exporter_config.SPORT_MAPPING.get(activity['type'], "Other")
    # Use track_id (the starting time) as identifier
    identifier = local_date_to_utc(activity['track_id'])

    track_element = create_sub_element(parent_element, "trk")

    name_element  = create_sub_element(track_element, "name", sport_type + " at " + identifier.isoformat())

    # Currently every activity has only one segment
    add_segment(track_element, activity)

def add_segment(parent_element, activity):

    STEPS_FOR_CADENCE.clear()

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
    
    # use realistic altitude values
    if altitude > -20:
        create_sub_element(trackpoint_element, "ele", str(altitude))

    create_sub_element(trackpoint_element, "time", timestamp.isoformat() + "Z")

    if heart_rate is not None:
        extensions_element = create_sub_element(trackpoint_element, "extensions")
        trackpointextension_element = create_sub_element(extensions_element, "TrackPointExtension", namespace="gpxtpx")
        
        heart_rate_bpm = int(heart_rate[0])
        # include only positive bpm values
        if heart_rate_bpm > 0:
            create_sub_element(trackpointextension_element, "hr", str(heart_rate_bpm), "gpxtpx")
            create_sub_element(extensions_element, "hr", str(heart_rate_bpm), "gpxdata")
        
        # cadence just for sport type 'Running'
        if sport_type == "Running":   
            STEPS_FOR_CADENCE.append(heart_rate[1])
            cadence = int(sum(STEPS_FOR_CADENCE) * (60 / len(STEPS_FOR_CADENCE)))
            create_sub_element(trackpointextension_element, "cad", text=str(cadence), namespace="gpxtpx")
            create_sub_element(extensions_element, "cadence", text=str(cadence), namespace="gpxdata")
    else:
        # sometimes values are missing. Interpolate cadence from the last recorded values.
        if sport_type == "Running" and STEPS_FOR_CADENCE:
            logger.debug("HeartRate and cadence value missing. Interpolate cadence.")
            extensions_element = create_sub_element(trackpoint_element, "extensions")
            trackpointextension_element = create_sub_element(extensions_element, "TrackPointExtension", namespace="gpxtpx")
            cadence = int(sum(STEPS_FOR_CADENCE) * (60 / len(STEPS_FOR_CADENCE)))
            create_sub_element(trackpointextension_element, "cad", text=str(cadence), namespace="gpxtpx")
            create_sub_element(extensions_element, "cadence", text=str(cadence), namespace="gpxdata")
            STEPS_FOR_CADENCE.popleft()        

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
    logger.info("Started gpx export")
    print("GPX export:")
    gpx_dest = dest + "/GPX/"
    os.makedirs(os.path.dirname(gpx_dest), exist_ok=True)
    for activity in amazfit_exporter_config.activities:
        document = create_gpx_document()
        add_track(document.getroot(), activity)
        identifier = activity['track_id']
        with open(os.path.join(gpx_dest, str(identifier) + ".gpx"), 'wb') as output_file:
            print("\tDate: " + local_date_to_utc(identifier).isoformat() + ", id: " + str(identifier) + ', type: ' + str(activity['type']) + ':' + amazfit_exporter_config.SPORT_MAPPING.get(activity['type']))
            output_file.write(document_to_string(document))
            output_file.close()
    logger.info("Finished gpx export")
