# Amazfit Exporter

This python script helps you to export your activities recorded on the Huami Amazfit Pace and Stratos to other platforms like RUNALYZE, Strava, Runkeeper, Runtastic, ...

## Usage

```
amazfit_exporter_cli.py [-h] [-o PATH] [--export-formats FORMAT [FORMAT ...]] [--no-hr] [--no-cadence]
                               [--no-calories] [-v] [-d] [--version]
                               database

positional arguments:
  database              path to the database

optional arguments:
  -h, --help            show this help message and exit
  -o PATH, --output PATH
                        path to the output directory (default: './')
  --export-formats FORMAT [FORMAT ...]
                        define list of export formats (default: all). Available formats: TCX, GPX
  --no-hr, --no-heart-rate
                        disable heart rate export
  --no-cadence          disable cadence export
  --no-calories         disable calories export
  -v, --verbose         print more information about runtime progress
  -d, --debug           print debug information about runtime progress. This is more detailed than '--verbose'
  --version             show program's version number and exit
```

### Usage Examples

`py amazfit_exporter_cli.py sport_data.db`

`py amazfit_exporter_cli.py sport_data.db -o /path/to/export/folder`

`py amazfit_exporter_cli.py sport_data.db --export-formats TCX --no-calories`

## Load Database from Watch

The `sport_data.db` file has to be downloaded from the Amazfit Pace or Stratos with ADB. There is a more complex method for non-rooted devices and a very simple for rooted roms. 

### Non-rooted Device
1. connect Pace or Stratos to the computer
2. execute adb command
   - Pace: `adb backup -f /export_data.ab -noapk com.huami.watch.sport`
   - Stratos `adb backup -f /export_data.ab -noapk com.huami.watch.newsport`
3. `java -jar abe.jar unpack export_data.ab export_data.tar` (abe is android backup extractor which is included inside tools folder)
4. extract the tar file using tar, 7-Zip, winRAR, ...
5. navigate to export_data\apps\com.huami.watch.(new)sport\db folder and copy sport_data.db

### Rooted Rom
1. connect Pace or Stratos to the computer
2. execute adb command
   - Pace: `adb pull /data/data/com.huami.watch.sport/databases/sport_data.db`
   - Stratos `adb pull /data/data/com.huami.watch.newsport/databases/sport_data.db`

## Changelog

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

- V2.8 Interpolate cadence if value is missing

- V2.9 Read latitude and longitude as strings from the database to avoid floating point approximation

- V3.0 Add command line arguments
