# amazfit_exporter
This python script helps you to export your huami Amazfit activities to other platforms like Strava,Runtastic...

At current version the script can be used in both CLI or GUI modes:

For CLI:
- py amazfit_exporter_cli.py sport_data.db /path/to/destination/folder

For GUI: (does not work with the latest version yet)
- py amazfit_exporter_gui.py

The sport_data.db file has to be get from the Amazfit by ADB, there are two methods for this
- connect amazfit to pc
- Pace:
   - adb backup -f /export_data.ab -noapk com.huami.watch.sport
- Stratos
   - adb backup -f /export_data.ab -noapk com.huami.watch.newsport
- java -jar abe.jar unpack export_data.ab export_data.tar (abe is android backup extractor which is included inside tools folder)
- extract the tar file using winrar
- navigate to export_data\apps\com.huami.watch.(new)sport\db folder and copy sport_data.db

or if you have a rooted rom, just execute command

- Pace: 
   - adb pull /data/data/com.huami.watch.sport/databases/sport_data.db
- Stratos
   - adb pull /data/data/com.huami.watch.newsport/databases/sport_data.db

# CHANGELOG

- V1.0 generates .gpx file for each activity
 
- V1.1 Added GUI
 
- V2.0 Changed to TCX format.  Add last sync time option.  Bug fixes.  Add indoor running with no GPS data. Optimize cadence calculation.
 
- V2.1 Add Bike and Trail Running Mode. Remember when last time sync so one can need to update new data. real-time sync feedback.
 
- V2.2 Add Device name so Strava will use the barometric sensor readings for elevation.
 
- V2.3 Speed up heart rate fetching. Fixes for TCX format.
 
- V2.4 Redesign code
 
- V2.5 Readded GPX export and cadence

- V2.6 Add biking export for Stratos

- V2.7 Use less trackpoints to calculate cadence