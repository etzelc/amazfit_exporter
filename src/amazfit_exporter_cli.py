#!/usr/bin/python3
import sys
import argparse
import amazfit_exporter
import amazfit_exporter_config
import datetime
import logging
import time
import os

# Set logger
logger = logging.getLogger(__name__)

# Create command line argument parser
parser = argparse.ArgumentParser(description='Export data from Amazfit Pace and Stratos database.')

# Path to database. Mandatory argument.
parser.add_argument('database', type=str, help='path to the database')

# Output directory argument
parser.add_argument('-o', '--output', metavar='PATH', dest='output', type=str, default='./', help="path to the output directory (default: './')")

# Export format argument
parser.add_argument('--export-formats', nargs='+', metavar='FORMAT', choices=amazfit_exporter_config.AVAILABLE_EXPORT_FORMATS.keys(), help='define list of export formats (default: all). Available formats: %(choices)s')

# Exclude data from export options
parser.add_argument('--no-hr', '--no-heart-rate', dest='no_heart_rate', action='store_true', default=False, help='disable heart rate export')
parser.add_argument('--no-cadence', dest='no_cadence', action='store_true', default=False, help='disable cadence export')
parser.add_argument('--no-calories', dest='no_calories', action='store_true', default=False, help='disable calories export')

# Logging level options
parser.add_argument('-v', '--verbose', dest='verbose',  action='store_true', default=False, help='print more information about runtime progress')
parser.add_argument('-d', '--debug', dest='debug',  action='store_true', default=False, help="print debug information about runtime progress. This is more detailed than '--verbose'")

# Version option
parser.add_argument('--version', action='version', version='Amazfit Exporter 3.0')
  
args = parser.parse_args()

# First set logging level
if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.verbose:
    logging.getLogger().setLevel(logging.INFO)

logger.debug("Input args: %r", args)

db = os.path.abspath(args.database)
dest = os.path.abspath(args.output)

# Set export formats if defined
if args.export_formats:
    amazfit_exporter_config.export_formats = args.export_formats 
logger.info("Selected export formats: %r", amazfit_exporter_config.export_formats)

amazfit_exporter_config.no_heart_rate = args.no_heart_rate
logger.info("Disable heart rate: %s", amazfit_exporter_config.no_heart_rate)
amazfit_exporter_config.no_cadence = args.no_cadence
logger.info("Disable cadence: %s", amazfit_exporter_config.no_cadence)
amazfit_exporter_config.no_calories = args.no_calories
logger.info("Disable calories: %s", amazfit_exporter_config.no_calories)

lstupdtime = 0

print("Exporting database '" + db + "' to '" + dest + "'")

# Check if a potential db file exists
if not os.path.isfile(db):
    logger.error("Error: Database not found! Check path to database: '%s'", db)
    sys.exit(1)

lstupd_file = os.path.join(dest, "lstupd.txt")
if os.path.isfile(lstupd_file):
    lstupd_f = open(lstupd_file,'r')
    lstupdtime = int(lstupd_f.read().strip() or 0)
    lstupd_f.close()

updtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(lstupdtime/1000)))
print ('The last synced activity was at: '+ str(updtime))
upd_begin_time = input('Press <Enter> to accept, 0 to resync everything>>') or (lstupdtime + 1 if lstupdtime > 0 else 0)

new_lstupdtime = amazfit_exporter.start_export(db,dest,int(upd_begin_time))

# Complete without crashing, check if new activity was synced, so update the last update file for next time
if new_lstupdtime >= 0:
    lstupd_f = open(lstupd_file,'w')
    lstupd_f.write(str(new_lstupdtime))
    lstupd_f.close()
else:
    print ("Nothing to sync")
