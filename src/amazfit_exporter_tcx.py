#!/usr/bin/python3
import collections
from time import ctime
from datetime import datetime
import logging
import os
from lxml import etree
import amazfit_exporter_config

TRAINING_CENTER_DATABASE_NAMESPACE = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
TRAINING_CENTER_DATABASE_LOCATION = "https://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd"

ACTIVITY_EXTENSION_V2_NAMESPACE = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"
ACTIVITY_EXTENSION_V2_LOCATION = "https://www8.garmin.com/xmlschemas/ActivityExtensionv2.xsd"
ACTIVITY_EXTENSION_V2 = "{%s}" % ACTIVITY_EXTENSION_V2_NAMESPACE

XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

TDC_NSMAP = {
    None: TRAINING_CENTER_DATABASE_NAMESPACE,
    "ae": ACTIVITY_EXTENSION_V2_NAMESPACE,
    "xsi": XML_SCHEMA_NAMESPACE}

TDC_SCHEMA_LOCATION = TRAINING_CENTER_DATABASE_NAMESPACE + " " + \
    TRAINING_CENTER_DATABASE_LOCATION + " " + \
    ACTIVITY_EXTENSION_V2_NAMESPACE + " " + \
    ACTIVITY_EXTENSION_V2_LOCATION

# Trackpoints are recorded every 1-3 seconds
# The last 20 values should be sufficient to calculate cadence
STEPS_FOR_CADENCE = collections.deque(maxlen=20)

sport_type = None

logger = logging.getLogger(__name__)

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
    global sport_type
    # Try to map Amazfit types to TCX types. If there's no match use "Other"
    sport_type = amazfit_exporter_config.SPORT_MAPPING.get(activity['type'], "Other")
    # Use track_id (the starting time) as identifier
    identifier = local_date_to_utc(activity['track_id'])

    activity_element = create_sub_element(parent_element, "Activity")

    activity_element.set("Sport", sport_type)
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
    
    STEPS_FOR_CADENCE.clear()

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
        heart_rate_bpm = int(heart_rate[0])
        # include only positive bpm values
        if heart_rate_bpm > 0:
            heart_rate_element = create_sub_element(trackpoint_element, "HeartRateBpm")
            create_sub_element(heart_rate_element, "Value", str(heart_rate_bpm))

        # cadence just for sport type 'Running'
        if sport_type == "Running":            
            extensions_element = create_sub_element(trackpoint_element, "Extensions")
            trackpointextension_element = create_sub_element(extensions_element, "TPX", namespace="ae")
            STEPS_FOR_CADENCE.append(heart_rate[1])
            cadence = int(sum(STEPS_FOR_CADENCE) * (60 / len(STEPS_FOR_CADENCE)))
            create_sub_element(trackpointextension_element, "RunCadence", text=str(cadence), namespace="ae")
    else:
        if sport_type == "Running" and STEPS_FOR_CADENCE:
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

def db_to_tcx(dest):
    logger.info("Started tcx export")
    print("TCX export:")
    tcx_dest = dest + "/TCX/"
    os.makedirs(os.path.dirname(tcx_dest), exist_ok=True)
    for activity in amazfit_exporter_config.activities:
        logger.debug("Activity: %r", tuple(activity))
        document = create_tcd_document()
        element = create_sub_element(document.getroot(), "Activities")
        add_activity(element, activity)
        add_author(document.getroot())
        identifier = activity['track_id']
        with open(os.path.join(tcx_dest, str(identifier) + ".tcx"), 'wb') as output_file:
            print("\tDate: " + local_date_to_utc(identifier).isoformat() + ", id: " + str(identifier) + ', type: ' + str(activity['type']) + ':' + amazfit_exporter_config.SPORT_MAPPING.get(activity['type']))
            output_file.write(document_to_string(document))
            output_file.close()  
    logger.info("Finished tcx export")
