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
parser.add_argument('-o', '--output', dest='output', type=str, default='./', help="path to the output directory (default: './')")

# Logging level options
parser.add_argument('-v', '--verbose', dest='verbose',  action='store_true', default=False, help='print more information about runtime progress')
parser.add_argument('-d', '--debug', dest='debug',  action='store_true', default=False, help="print debug information about runtime progress. This is more detailed than '--verbose'")

# Version option
parser.add_argument('--version', action='version', version='Amazfit Exporter 2.10')
  
args = parser.parse_args()

# First set logging level
if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.verbose:
    logging.getLogger().setLevel(logging.INFO)

logger.info("Input args: %r", args)

db = os.path.abspath(args.database)
dest = os.path.abspath(args.output)

lstupdtime = 0

print("Exporting database '" + db + "' to '" + dest + "'")

lstupd_file = os.path.join(dest, "lstupd.txt")
if os.path.exists(lstupd_file):
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
