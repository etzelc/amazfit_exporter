#!/usr/bin/python3
import logging, sys

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

AVAILABLE_EXPORT_FORMATS = {
    'TCX': 'Training Center XML',
    'GPX': 'GPS Exchange Format'
}

export_formats = AVAILABLE_EXPORT_FORMATS.keys()

no_heart_rate = False
no_cadence = False
no_calories = False

activities = []
trackpoint_data = []
heart_rate_data = []

# Map Amazfit DB to strings
SPORT_MAPPING = {
    None: "Other",
    1: "Running", # Running
    2: "Running", # Walking
    3: "Running", # Trail Running
    4: "Running", # Indoor Running
    5: "Biking", # Biking
    6: "Other", #Walking
    7: "Running", # Trail Runing
    8: "Running", # Treadmil
    9: "Biking", # Outdoor Biking
    10: "Biking", # Indoor Biking
}

