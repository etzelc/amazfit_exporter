@title Download and Export Sport DB Script
@echo off
setlocal

rem The script can be called with an optional parameter 
rem specifying the export directory.
rem E.g. 'downloadAndExport.bat "D:\myExportDirectory"'
rem .
rem The 'amazfit_exporter_cli.py' has to be located at 
rem "..\src\amazfit_exporter_cli.py" from the 'run.bat' file directory
rem Example tree:
rem   path/to/folder
rem   ├──src
rem   │  ├──amazfit_exporter_cli.py
rem   │  └──...
rem   ├──scripts
rem   │  ├──downloadAndExport.bat
rem   │  └──...
rem   └──tools
rem      ├──abe.jar
rem      ├──sport_data_empty_stratos.db
rem      └──...

rem Path to adb executable. If in PATH variable then "adb", otherwise for 
rem example "C:\Users\[USER]\AppData\Local\Android\sdk\platform-tools\adb"
set _ADB_EXECUTABLE=adb

rem Path to python executable. If in PATH variable then "py", otherwise for 
rem example "C:\Users\[USER]\AppData\Local\Programs\Python\Launcher\py"
set _PYTHON_EXECUTABLE=py

rem Only necessary for non-rooted devices:
rem Path to 7-Zip executable. 
set _7Z_EXECUTABLE=C:\Program Files\7-Zip\7z.exe

rem Only necessary for non-rooted devices:
rem Path to Java executable. If in PATH variable then "java", otherwise for 
rem example "C:\Program Files (x86)\Java\jre1.8.0_271\bin\java"
set _JAVA_EXECUTABLE=java

rem optional parameter for the output directory
set $OUTPUTDIRECTORY=%~1

rem Variable for the empty db. Gets set during watch selection.
set $EMPTY_DB_PATH=

echo -------------------------------------------------------
echo Download sport_data from the Huami Amazfit Pace/Stratos
echo and export database with Amazfit Exporter.

if "%$OUTPUTDIRECTORY%" == "" (
	echo %cd%
	set $OUTPUTDIRECTORY=%cd%
)
echo -------------------------------------------------------
echo Export directory is set to:
echo '%$OUTPUTDIRECTORY%'

if exist "%$OUTPUTDIRECTORY%\db\sport_data.db" goto DB_EXISTS

echo -------------------------------------------------------
echo 'sport_data.db' does not exist at:
echo '%$OUTPUTDIRECTORY%\db\'

goto CHOOSE_DEVICE

:DB_EXISTS
echo -------------------------------------------------------
echo sport_data.db found at:
echo '%$OUTPUTDIRECTORY%\db\'

:ASK_RELOAD_IF_DB_EXISTS
echo -------------------------------------------------------
echo Do you want to download again? 
echo Existing db gets backed up to 'sport_data_backup.db'

set /P $DOWN_AGAIN=Type Y/N and press Enter:   
if /I "%$DOWN_AGAIN%"=="Y" goto BACKUP_EXISTING_DB 
if /I "%$DOWN_AGAIN%"=="Yes" goto BACKUP_EXISTING_DB
if /I "%$DOWN_AGAIN%"=="N" goto EXPORT
if /I "%$DOWN_AGAIN%"=="No" goto EXPORT

echo -------------------------------------------------------
echo '%$DOWN_AGAIN%' is not a valid input!

goto ASK_RELOAD_IF_DB_EXISTS

:BACKUP_EXISTING_DB
move /y "%$OUTPUTDIRECTORY%\db\sport_data.db" "%$OUTPUTDIRECTORY%\db\sport_data_backup.db" 

:CHOOSE_DEVICE
echo -------------------------------------------------------
echo Connect your watch to the PC and choose
echo    'rp' for a rooted Pace  
echo    'rs' for a rooted Stratos 
echo    'np' for a non rooted Pace 
echo    'ns' for a non rooted Stratos 
echo    'exit' to stop the script 

set /P $WATCH_TYPE=Type option and press enter: 
if /I "%$WATCH_TYPE%"=="rp" (
	set $SPORTAPP=com.huami.watch.sport
	goto DB_DOWNLOAD_ROOT
)
if /I "%$WATCH_TYPE%"=="rs" (
	set $SPORTAPP=com.huami.watch.newsport
	set $EMPTY_DB_PATH="%~dp0..\tools\sport_data_empty_stratos.db"
	goto DB_DOWNLOAD_ROOT
)
if /I "%$WATCH_TYPE%"=="np" (
	set $SPORTAPP=com.huami.watch.sport
	goto DB_DOWNLOAD_NON_ROOT
)
if /I "%$WATCH_TYPE%"=="ns" (
	set $SPORTAPP=com.huami.watch.newsport
	goto DB_DOWNLOAD_NON_ROOT
)
if /I "%$WATCH_TYPE%"=="exit" (
	goto EXIT
)

echo -------------------------------------------------------
echo '%$WATCH_TYPE%' is not a valid input!

goto CHOOSE_DEVICE

:DB_DOWNLOAD_ROOT
echo -------------------------------------------------------
echo Download sport_data.db from rooted device. 
echo If it's not responding, reconnect your watch. 

if not exist "%$OUTPUTDIRECTORY%\db" md "%$OUTPUTDIRECTORY%\db"
%_ADB_EXECUTABLE% devices
%_ADB_EXECUTABLE% wait-for-device
%_ADB_EXECUTABLE% pull "/data/data/%$SPORTAPP%/databases/sport_data.db" "%$OUTPUTDIRECTORY%"\db\
%_ADB_EXECUTABLE% wait-for-device
%_ADB_EXECUTABLE% kill-server
%_ADB_EXECUTABLE% wait-for-device
if not exist "%$OUTPUTDIRECTORY%\db\sport_data.db" goto DB_DOWNLOAD_FAILED
goto DB_DOWNLOAD_COMPLETE

:DB_DOWNLOAD_NON_ROOT
echo -------------------------------------------------------
echo Download sport_data.db from non rooted device.
echo If it's not responding, reconnect your watch.

if not exist "%$OUTPUTDIRECTORY%\db" md "%$OUTPUTDIRECTORY%\db"
"%_ADB_EXECUTABLE%" devices
"%_ADB_EXECUTABLE%" wait-for-device
"%_ADB_EXECUTABLE%" backup -f "%$OUTPUTDIRECTORY%\db\export_data.ab" -noapk %$SPORTAPP%
"%_JAVA_EXECUTABLE%" -jar "%~dp0..\tools\abe.jar" unpack "%$OUTPUTDIRECTORY%\db\export_data.ab" "%$OUTPUTDIRECTORY%\db\export_data.tar"
"%_7Z_EXECUTABLE%" x "%$OUTPUTDIRECTORY%\db\export_data.tar" -o"%$OUTPUTDIRECTORY%\db" > NUL
move /y "%$OUTPUTDIRECTORY%\db\apps\%$SPORTAPP%\db\sport_data.db" "%$OUTPUTDIRECTORY%\db"
del /q "%$OUTPUTDIRECTORY%\db\export_data.ab" 
del /q "%$OUTPUTDIRECTORY%\db\export_data.tar" 
rd /s /q "%$OUTPUTDIRECTORY%\db\apps"
"%_ADB_EXECUTABLE%" wait-for-device
"%_ADB_EXECUTABLE%" kill-server
"%_ADB_EXECUTABLE%" wait-for-device
if not exist "%$OUTPUTDIRECTORY%\db\sport_data.db" goto DB_DOWNLOAD_FAILED

:DB_DOWNLOAD_COMPLETE
echo -------------------------------------------------------
echo Download sport_data.db is completed. 

:EXPORT
echo -------------------------------------------------------
echo Export options for Python Amazfit Exporter:
echo -------------------------------------------------------

%_PYTHON_EXECUTABLE% "%~dp0..\src\amazfit_exporter_cli.py" --help
 
echo -------------------------------------------------------
echo The path to the db should not be changed!
echo Not changable: amazfit_exporter_cli.py "%$OUTPUTDIRECTORY%\db\sport_data.db" -o "%$OUTPUTDIRECTORY%" 

set /P $EXPORTER_OPTIONS=Enter optional command line arguments or press enter: 

echo -------------------------------------------------------

@echo on

%_PYTHON_EXECUTABLE% "%~dp0..\src\amazfit_exporter_cli.py" "%$OUTPUTDIRECTORY%\db\sport_data.db" -o "%$OUTPUTDIRECTORY%" %$EXPORTER_OPTIONS% 

@echo off

if not %errorlevel% == 0 goto EXPORT_FAILED

echo -------------------------------------------------------
echo Export is done. Check output directory:
echo '%$OUTPUTDIRECTORY%'

:CHOOSE_EMPTY_DB_PUSH
REM Empty db upload currently only available for rooted 
REM Stratos, as I don't have an empty DB for Pace.
if "%$EMPTY_DB_PATH%" == "" goto EXIT
echo -------------------------------------------------------
echo Push an empty db to your device?

set /P $PUSH_EMPTY_DB=Type Y/N and press Enter:   
if /I "%$PUSH_EMPTY_DB%"=="Y" goto PUSH_EMPTY_DB
if /I "%$PUSH_EMPTY_DB%"=="Yes" goto PUSH_EMPTY_DB
if /I "%$PUSH_EMPTY_DB%"=="N" goto EXIT
if /I "%$PUSH_EMPTY_DB%"=="No" goto EXIT

echo -------------------------------------------------------
echo '%$PUSH_EMPTY_DB%' is not a valid input!

goto CHOOSE_EMPTY_DB_PUSH

:PUSH_EMPTY_DB
echo -------------------------------------------------------
echo Pushing empty db to your device. 
echo If it's not responding, reconnect your watch. 

if not exist "%$EMPTY_DB_PATH%" goto EMPTY_DB_NOT_FOUND
%_ADB_EXECUTABLE% devices
%_ADB_EXECUTABLE% wait-for-device
%_ADB_EXECUTABLE% push "%$EMPTY_DB_PATH%" /data/data/%$SPORTAPP%/databases/sport_data.db
%_ADB_EXECUTABLE% wait-for-device
%_ADB_EXECUTABLE% kill-server
%_ADB_EXECUTABLE% wait-for-device

if not %errorlevel% == 0 goto PUSH_EMPTY_DB_FAILED

echo -------------------------------------------------------
echo Empty db was successfully pushed to your device.

goto EXIT

:PUSH_EMPTY_DB_FAILED
echo -------------------------------------------------------
echo ERROR: Push of empty db failed.
echo        Check console output for additional information.

exit /b 4

:EMPTY_DB_NOT_FOUND
echo -------------------------------------------------------
echo ERROR: Empty db not found at '%$EMPTY_DB_PATH%'.
echo        Check console output for additional information.

exit /b 3

:EXPORT_FAILED
echo -------------------------------------------------------
echo ERROR: Export may have failed.
echo        Check console output for additional information.

exit /b 2

:DB_DOWNLOAD_FAILED
echo -------------------------------------------------------
echo ERROR: Download sport_data.db failed.

exit /b 1

:EXIT
exit /b
