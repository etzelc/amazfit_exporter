#!/usr/bin/python3
import sqlite3 as lite
import sys
import datetime
import os
import json

def db_to_tcx(db,dest):
	con = lite.connect(db)

	with con:
		cur = con.cursor()    
		cur.execute('SELECT track_id, start_time, type, content from sport_summary where type=1 or type=2 or type=4')
		running_sessions = cur.fetchall()
		for running_session in running_sessions:
			# load the summary information JSON
			content_json = json.loads(running_session[3])
			
			track_id=running_session[0]
			tiempo_init=running_session[1]
			# find out what type of activity it is
			if running_session[2] == 1:
				activity = "running"
			elif running_session[2] == 2:
				activity = "walking"
			elif running_session[2] == 4:
				activity = "treadmill"
			else:
				activity = "unknwon"
			cad1 = 0
			cad2 = 0 
			cad3 = 0 
			cad4 = 0 
			cad5 = 0
			cad_avg = 0 
			step_cum = 0
			# calculate stride length for treadmill runs because Amazfit stride info is incorrect
			step_tot = content_json['step_count']
			dist_tot = content_json['distance']
			stride = dist_tot/step_tot
			dist = 0
			year=datetime.datetime.utcfromtimestamp(running_session[1]/1000).strftime('%Y')
			month=datetime.datetime.utcfromtimestamp(running_session[1]/1000).strftime('%m')
			day=datetime.datetime.utcfromtimestamp(running_session[1]/1000).strftime('%d')
			hour=datetime.datetime.utcfromtimestamp(running_session[1]/1000).strftime('%H')
			minute=datetime.datetime.utcfromtimestamp(running_session[1]/1000).strftime('%M')
			second=datetime.datetime.utcfromtimestamp(running_session[1]/1000).strftime('%S')
			try:
				os.remove(dest+'/'+year+month+day+'_'+hour+minute+second+'.tcx')
			except OSError:
				pass
			with open(dest+'/'+year+month+day+'_'+hour+minute+second+'Z.tcx', 'a') as out:	
				# Write Header
				out.write('<?xml version="1.0" encoding="UTF-8"?>' + '\n')
				out.write('<TrainingCenterDatabase xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd" xmlns:ns5="http://www.garmin.com/xmlschemas/ActivityGoals/v1" xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2" xmlns:ns2="http://www.garmin.com/xmlschemas/UserProfile/v2" xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' + '\n')
				out.write(' <Activities>' + '\n')
				out.write('  <Activity Sport="'+ activity + '">' + '\n')
				out.write('   <Id>'+year+'-'+month+'-'+day+'T'+hour+':'+minute+':'+second+ 'Z'+ '</Id>'+ '\n')
				out.write('   <Lap StartTime="'+ year+'-'+month+'-'+day+'T'+hour+':'+minute+':'+second +'Z">' + '\n')
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
							out.write('       <Value>'+ str(dato[0]) +'</Value>' + '\n')
							out.write('      </HeartRateBpm>' + '\n')
						# push the new step count in and recalculate the cadence
						cad1 = cad2
						cad2 = cad3
						cad3 = cad4
						cad4 = cad5
						cad5 = dato[1]
						cad_avg = int((cad1 + cad2 + cad3 + cad4 + cad5)/5*30)
						#Write the cadence
						out.write('      <Extensions>'+ '\n')
						out.write('       <TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">'+ '\n')
						out.write('        <RunCadence>'+ str(cad_avg) + '</RunCadence>' + '\n')
						out.write('       </TPX>' + '\n')
						out.write('      </Extensions>'+ '\n')
						out.write('     </Trackpoint>' + '\n')
				else:
				# ignore false and extra data points.  Also fixed the bug generating duplicate data.
					cur.execute('SELECT location_data.latitude, location_data.longitude, location_data.altitude, location_data.timestamp from location_data where location_data.track_id=' + str(track_id) + ' and location_data.point_type > 1')
					datos = cur.fetchall()
					for dato in datos:
						latitud=str(dato[0])
						longitud=str(dato[1])
						altitud = str(round(dato[2],1))
						time=((dato[3]+tiempo_init)/1000)
						year=datetime.datetime.utcfromtimestamp(time).strftime('%Y')
						month=datetime.datetime.utcfromtimestamp(time).strftime('%m')
						day=datetime.datetime.utcfromtimestamp(time).strftime('%d')
						hour=datetime.datetime.utcfromtimestamp(time).strftime('%H')
						minute=datetime.datetime.utcfromtimestamp(time).strftime('%M')
						second=datetime.datetime.utcfromtimestamp(time).strftime('%S')			
						# Make it prettier and more flexible in the future
						cur.execute('SELECT rate,step_count from heart_rate where heart_rate.time = ?', (round(time)*1000,))
						rate=cur.fetchone()
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
							out.write('       <Value>'+ str(rate[0]) +'</Value>' + '\n')
							out.write('      </HeartRateBpm>' + '\n')
							# push the new step count in and recalculate the cadence
							cad1 = cad2
							cad2 = cad3
							cad3 = cad4
							cad4 = cad5
							cad5 = rate[1]
							cad_avg = int((cad1 + cad2 + cad3 + cad4 + cad5)/5*30)
							#Write the cadence
							out.write('      <Extensions>'+ '\n')
							out.write('       <TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">'+ '\n')
							out.write('        <RunCadence>'+ str(cad_avg) + '</RunCadence>' + '\n')
							out.write('       </TPX>' + '\n')
							out.write('      </Extensions>'+ '\n')
						out.write('     </Trackpoint>' + '\n')
				out.write('    </Track>'+ '\n')
				out.write('   </Lap>'+ '\n')
				out.write('  </Activity>'+ '\n')
				out.write(' </Activities>'+ '\n')
				out.write('</TrainingCenterDatabase>'+ '\n')
				out.close()
