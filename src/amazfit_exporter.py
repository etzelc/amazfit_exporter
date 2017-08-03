#!/usr/bin/python3
import sqlite3 as lite
import sys
import datetime
import time as t
import os
import json
from collections import deque

def db_to_tcx(db,dest,begtime):

	# Connect to the sport database
	con = lite.connect(db)
	with con:
		cur = con.cursor()
		cur.execute('SELECT track_id, start_time, type, content, end_time, calorie from sport_summary where track_id >'+ str(begtime) + ' and (type=1 or type=2 or type=3 or type=4 or type=5)')
		running_sessions = cur.fetchall()
		for running_session in running_sessions:
			# load the summary information JSON
			content_json = json.loads(running_session[3])
			# Get the track ID and starting time
			track_id=running_session[0]
			time_init=running_session[1]
			time_end=running_session[4]
			# find out what type of activity it is
			if running_session[2] == 1:
				activity = "running"
				garmin_v2_activity = "Running"
			elif running_session[2] == 2:
				activity = "walking"
				garmin_v2_activity = "Running"
			elif running_session[2] ==3:
				activity = "trail running"
				garmin_v2_activity = "Running"
			elif running_session[2] == 4:
				activity = "treadmill"
				garmin_v2_activity = "Running"
			elif running_session[2] == 5:
				activity = "bike"
				garmin_v2_activity = "Biking"
			else:
				activity = "unknown"
				garmin_v2_activity = "Other"
			#initialize
			cad = deque([])
			stride = 0
			cad_avg = 0
			step_cum = 0
			# calculate stride length for treadmill runs because Amazfit stride info is incorrect
			step_tot = content_json['step_count']
			dist_tot = content_json['distance']
			if step_tot > 0:
				stride = dist_tot/step_tot
			dist = 0
			session_strt = time_init/1000
			year=datetime.datetime.utcfromtimestamp(session_strt).strftime('%Y')
			month=datetime.datetime.utcfromtimestamp(session_strt).strftime('%m')
			day=datetime.datetime.utcfromtimestamp(session_strt).strftime('%d')
			hour=datetime.datetime.utcfromtimestamp(session_strt).strftime('%H')
			minute=datetime.datetime.utcfromtimestamp(session_strt).strftime('%M')
			second=datetime.datetime.utcfromtimestamp(session_strt).strftime('%S')
			with open(dest+'/'+year+month+day+'_'+hour+minute+second+'Z.tcx', 'w') as out:
				# Write Header
				print(t.strftime('%Y-%m-%d %H:%M:%S', t.localtime(session_strt))+' activity:' + activity + ' syncing...')
				out.write('<?xml version="1.0" encoding="UTF-8"?>' + '\n')
				out.write('<TrainingCenterDatabase xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd" xmlns:ns5="http://www.garmin.com/xmlschemas/ActivityGoals/v1" xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2" xmlns:ns2="http://www.garmin.com/xmlschemas/UserProfile/v2" xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' + '\n')
				out.write(' <Activities>' + '\n')
				out.write('  <Activity Sport="'+ garmin_v2_activity + '">' + '\n')
				out.write('   <Id>'+year+'-'+month+'-'+day+'T'+hour+':'+minute+':'+second+ 'Z'+ '</Id>'+ '\n')
				out.write('   <Lap StartTime="'+ year+'-'+month+'-'+day+'T'+hour+':'+minute+':'+second +'Z">' + '\n')
				out.write('    <TotalTimeSeconds>' + str((time_end - time_init) / 1000) + '</TotalTimeSeconds>\n')
				# FIXME Currently no distance is available at this point
				out.write('    <DistanceMeters>0</DistanceMeters>\n')
				# FIXME Check if calories value is plausible
				out.write('    <Calories>' + str(int(running_session[5] / 1000)) + '</Calories>\n')
				out.write('    <Intensity>Active</Intensity>\n')
				out.write('    <TriggerMethod>Manual</TriggerMethod>\n')
				out.write('    <Track>' + '\n')

				# Going to get the different datos depending on whether it is a GPX or a indoor stationary activity
				if activity == "treadmill":
					cur.execute('SELECT rate, step_count, time from heart_rate where track_id=' + str(track_id))
					datos = cur.fetchall()
					for dato in datos:
						time=dato[2]/1000
						year=datetime.datetime.utcfromtimestamp(time).strftime('%Y')
						month=datetime.datetime.utcfromtimestamp(time).strftime('%m')
						day=datetime.datetime.utcfromtimestamp(time).strftime('%d')
						hour=datetime.datetime.utcfromtimestamp(time).strftime('%H')
						minute=datetime.datetime.utcfromtimestamp(time).strftime('%M')
						second=datetime.datetime.utcfromtimestamp(time).strftime('%S')
						# Write the trackpoint
						out.write('     <Trackpoint>' + '\n')
						out.write('      <Time>'+year+'-'+month+'-'+day+'T'+hour+':'+minute+':'+second+ 'Z</Time>'+ '\n')
						# Calculate the distance based on cumualtive steps
						step_cum = step_cum + dato[1]
						dist = step_cum * stride
						out.write('      <DistanceMeters>'+ str(dist) + '</DistanceMeters>' + '\n')
						# Check that you have a valid HR reading
						if dato[0] > 0:
							# Write the HR
							out.write('      <HeartRateBpm>' + '\n')
							out.write('       <Value>'+ str(int(dato[0])) +'</Value>' + '\n')
							out.write('      </HeartRateBpm>' + '\n')
						# push the new step count in and recalculate the cadence
						if dato[1] > 0:
							cad.append(dato[1])
						if len(cad) > 30:
							cad.popleft()
							cad_avg = int(sum(cad)/len(cad)*30)
							#Write the cadence
							out.write('      <Extensions>'+ '\n')
							out.write('       <TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">'+ '\n')
							out.write('        <RunCadence>'+ str(cad_avg) + '</RunCadence>' + '\n')
							out.write('       </TPX>' + '\n')
							out.write('      </Extensions>'+ '\n')
						out.write('     </Trackpoint>' + '\n')
				else:
				# ignore false and extra data points.  Also fixed the bug generating duplicate data.
					cur.execute('SELECT location_data.latitude, location_data.longitude, location_data.altitude, location_data.timestamp from location_data where location_data.track_id=' + str(track_id) + ' and location_data.point_type > 0')
					datos = cur.fetchall()
					cur.execute('SELECT time,rate,step_count from heart_rate')
					heart_rates = {}
					for hr in cur.fetchall():
						if not hr[0] in heart_rates:
							heart_rates[hr[0]] = hr[1:]
					for dato in datos:
						latitud=str(dato[0])
						longitud=str(dato[1])
						altitud = str(round(dato[2],1))
						time=((dato[3] + time_init)/1000)
						year=datetime.datetime.utcfromtimestamp(time).strftime('%Y')
						month=datetime.datetime.utcfromtimestamp(time).strftime('%m')
						day=datetime.datetime.utcfromtimestamp(time).strftime('%d')
						hour=datetime.datetime.utcfromtimestamp(time).strftime('%H')
						minute=datetime.datetime.utcfromtimestamp(time).strftime('%M')
						second=datetime.datetime.utcfromtimestamp(time).strftime('%S')
						# Make it prettier and more flexible in the future
						rate = heart_rates.get(round(time) * 1000)
						# Write the trackpoint
						out.write('     <Trackpoint>' + '\n')
						out.write('      <Time>'+year+'-'+month+'-'+day+'T'+hour+':'+minute+':'+second+ 'Z</Time>'+ '\n')
						out.write('      <Position>' + '\n')
						out.write('       <LatitudeDegrees>' + latitud + '</LatitudeDegrees>' + '\n')
						out.write('       <LongitudeDegrees>' + longitud + '</LongitudeDegrees>' + '\n')
						out.write('      </Position>' + '\n')
						# only write altitude if valid (greater than -1000 meters)
						if dato[2] > -1000:
							out.write('      <AltitudeMeters>'+altitud+'</AltitudeMeters>' + '\n')
						# Check that you have a valid HR reading
						if rate is not None and rate[0] > 0:
							# Write the HR
							out.write('      <HeartRateBpm>' + '\n')
							out.write('       <Value>'+ str(int(rate[0])) +'</Value>' + '\n')
							out.write('      </HeartRateBpm>' + '\n')
							# push the new step count in and recalculate the cadence
							if rate[1] > 0:
								cad.append(rate[1])
							if len(cad) > 30:
								cad.popleft()
								cad_avg = int(sum(cad)/len(cad)*30)
								#Write the cadence
								out.write('      <Extensions>'+ '\n')
								out.write('       <TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">'+ '\n')
								out.write('        <RunCadence>'+ str(cad_avg) + '</RunCadence>' + '\n')
								out.write('       </TPX>' + '\n')
								out.write('      </Extensions>'+ '\n')
						out.write('     </Trackpoint>' + '\n')
				out.write('    </Track>'+ '\n')
				out.write('   </Lap>'+ '\n')
				out.write('   <Creator xsi:type="Device_t">\n')
				out.write('    <Name>Huami Amazfit Pace</Name>\n')
				out.write('    <UnitId>0</UnitId>\n')
				out.write('    <ProductID>0</ProductID>\n')
				out.write('    <Version>\n')
				out.write('     <VersionMajor>0</VersionMajor>\n')
				out.write('     <VersionMinor>0</VersionMinor>\n')
				out.write('    </Version>\n')
				out.write('   </Creator>\n')
				out.write('  </Activity>'+ '\n')
				out.write(' </Activities>'+ '\n')
				out.write('</TrainingCenterDatabase>'+ '\n')
				out.close()
