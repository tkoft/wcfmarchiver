""" 
WCFM ARCHIVAL TOOL

Records audio into WAV files of specified length, with specified amount of padding/overlap.  For WCFM.
Files are delimited modularly using epoch time. Examples:

	Interval of 3600 s (60 min) will be split at the top of each hour (+/- padding)
	Interval of 5400 s (90 min) will be split every hour and a half, starting at 00:00 (+/- padding).
	Other more funky intervals will likewise split as if they started on Thusrday 1 Jan 1970 (UTC).  
	I would avoid prime numbers.

Files are named with specified name, the date, and the number of splits since the beginning of the day.
Written to /archives.  Time of file write for all files can be foud in outputLog.txt.

Deletes oldest files after max file number is reached, if option is chosen.

(c) 2016 gary chen - for WCFM

"""
import pyaudio 					
import wave
import time
import os.path
import msvcrt
from array import array
import configparser

# Create config.ini with defaults if doesn't exist
config = configparser.ConfigParser()

config['FILE'] = {
	'RecordMin'  : '60',
	'PadMin' : '5', 
	'WaveOutputFilename':'wcfm',
	'MaxFiles' : '200',
	'DeleteOld' : 'False',
	'Threshold' : '333',}
config['RECORD']  = {
	'Chunk' : '1024', 
	'Format' : '8', 		#pyaudio.paInt16 = 8
	'Channels' : '2',
	'Rate' : '44100',}

# Parse config.ini for configuration settings
if (os.path.isfile("config.ini")):
	config.read("config.ini")
RECORD_MIN = float(config['FILE']['RecordMin'])
PAD_MIN = float(config['FILE']['PadMin'])
WAVE_OUTPUT_FILENAME = config['FILE']['WaveOutputFilename']
MAX_FILES = int(config['FILE']['MaxFiles'])
DELETE_OLD = config['FILE'].getboolean('DeleteOld')
THRESHOLD = int(config['FILE']['Threshold'])

CHUNK = int(config['RECORD']['Chunk'])
FORMAT = int(config['RECORD']['Format']) #pyaudio.paInt = 8
CHANNELS = int(config['RECORD']['Channels'])
RATE = int(config['RECORD']['Rate'])

with open('config.ini', 'w') as configfile:
	config.write(configfile)	

# setup variables, data structs, files
RECORD_SECONDS = int(RECORD_MIN * 60)
PAD_SEC = int(PAD_MIN * 60)
quit = False
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
framesOverlap = []
frame = []
count = 0
hr = 24
if not os.path.exists("archives"):
	os.makedirs("archives")
log = open("archives/outputLog.txt", "a+")
out = open("out.txt", "a+")

# load up files currently in archives directory

if (DELETE_OLD):
	readIn = os.listdir("archives")
	readIn = ["archives/"+x for x in os.listdir("archives") if x.endswith(".wav")]
else:
	readIn = []
readIn.sort()
fileNames = ([None]*(MAX_FILES - len(readIn)))
fileNames.extend(readIn)

# message printing; writes to stdout and out.txt
def output(mes):
	global out
	print(mes)
	out.write(mes)
	out.write("\n")
	out.flush()

# checks if quit key has been pressed before or now
def quitPressed():
	global quit
	if (msvcrt.kbhit()):
   		if (ord(msvcrt.getch()) == 113):
   			quit = True
	return quit

# initialization info
output("------------------------------------------------------------")		
output("| WCFM ARCHIVER by Gary Chen '18")
output("| init date: \t\t" + time.asctime(time.localtime(time.time())))
output("| interval: \t\t" + str(RECORD_SECONDS/60) + " min")
output("| padding: \t\t" + str(PAD_SEC/60) + " min")
output("| silence threshold: \t" + str(THRESHOLD))
output("| max # of files: \t" + str(MAX_FILES))
output("| delete old files: \t" + str(DELETE_OLD))
output("| approx size on disk: \t" + str(11*(RECORD_MIN+2*PAD_MIN)*MAX_FILES/1000) + " GB")
output("------------------------------------------------------------")

# MAIN RECORDING LOOP
while not quitPressed():
	# refresh the time; should be five minutes into hour or script start time
	# also reset file count if new day
	localtime = time.localtime(time.time())
	yr = localtime.tm_year
	month = localtime.tm_mon
	if (hr != localtime.tm_hour):
		hr = localtime.tm_hour
		count = 0
	day = localtime.tm_mday
	formatHr = str(yr) + "-" + str(month).zfill(2) + "-" + str(day).zfill(2) + "-" + str(hr).zfill(2)
	
	# update count, set file name based on new count
	while (os.path.isfile("archives/" + WAVE_OUTPUT_FILENAME + "-" + formatHr + "-" + str(count).zfill(3) + ".wav")):
		count = count + 1
	fileName = WAVE_OUTPUT_FILENAME + "-" + formatHr + "-" + str(count).zfill(3) + ".wav"

	# delete oldest file(s)
	while (len(fileNames) >= MAX_FILES):
		toDelete = fileNames.pop(0)
		if (toDelete != None):
			os.remove(toDelete)
			output("* DELETED: \t\t" + toDelete)

	# delete temp file
	if (os.path.isfile("archives/temp.wav")):
		os.remove("archives/temp.wav")

	# open file
	output("* now writing to: \tarchives/" + fileName)
	wf = wave.open("archives/" + fileName, 'wb')
	wf.setnchannels(CHANNELS)
	wf.setsampwidth(p.get_sample_size(FORMAT))
	wf.setframerate(RATE)
	fileNames.append("archives/" + fileName)

	# write +/-5 minutes from top of hour to file
	wf.writeframes(b''.join(framesOverlap))

	# write 55 min into the hour, or until keypress
	maxVol = -1
	while (not quitPressed() and int(time.time())%RECORD_SECONDS != (RECORD_SECONDS - PAD_SEC)):
	   data = stream.read(CHUNK)
	   frame.append(data)
	   wf.writeframes(b''.join(frame))
	   frame = []
	   # silence detection; keept rack of max level		
	   bitArr = array('h', data)
	   bitArr.append(maxVol)
	   maxVol = max(bitArr)

	# silence detected
	if (maxVol <= THRESHOLD):
		# remove file
		wf.close()
		os.remove("archives/"+fileName)
		fileNames.pop(len(fileNames)-1)
		output("* DELETED SILENCE:  \tarchives/"+fileName)

		#record padding to temp and for next file
		wf = wave.open("archives/temp.wav", 'wb')
		wf.setnchannels(CHANNELS)
		wf.setsampwidth(p.get_sample_size(FORMAT))
		wf.setframerate(RATE)
		output("* still recording padding...")
		framesOverlap = []
		while (not quitPressed() and int(time.time())%RECORD_SECONDS != PAD_SEC):
			data = stream.read(CHUNK)
			frame.append(data)
			wf.writeframes(b''.join(frame))
			frame = []
			framesOverlap.append(data)
		wf.close()

	# no silence detected
	else:
		# write +/-5 min at bottom of hour, and record into framesOverlap
		framesOverlap = []
		while (not quitPressed() and int(time.time())%RECORD_SECONDS != PAD_SEC):
			data = stream.read(CHUNK)
			frame.append(data)
			wf.writeframes(b''.join(frame))
			frame = []
			framesOverlap.append(data)

		# close audio file
		wf.close()

		# write to log
		log.write("\n" + fileName + " \t" + time.asctime(localtime))
		log.flush()

		output("* done recording: \tarchives/" + fileName)
		output("------------------------------------------------------------")

# Cleanup  
stream.stop_stream()
stream.close()
p.terminate()
log.close();
out.close();
