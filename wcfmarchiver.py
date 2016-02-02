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

Deletes oldest files after max file number is reached.  Will only delete made during current instance of the program.

Future features:
	Currently, if program is stopped at top of interval +/- padding, new interval will not be saved, only old one. Fix this?
	Some UI for inputting configs, or selecting default.  Maybe read from config file?
	Some way to stop the program besides force closing it

(c) 2016 gary chen - for WCFM

"""

import pyaudio
import wave
import time
import os.path
import msvcrt
from collections import deque
from array import array

# file write settings
RECORD_MIN = 60
PAD_MIN = 5
WAVE_OUTPUT_FILENAME = "wcfm"
MAX_FILES = 180

# recording settings
RECORD_SECONDS = int(RECORD_MIN * 60)
PAD_OVERLAP = int(PAD_MIN * 60)
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
THRESHOLD = 150

# setup variables, data structs, files
quit = False
p = pyaudio.PyAudio()
framesOverlap = []
frame = []
fileNames = [None]*MAX_FILES
count = 0
hr = time.localtime(time.time()).tm_hour
if not os.path.exists("archives"):
	os.makedirs("archives")
log = open("archives/outputLog.txt", "a+")

def quitPressed():
	global quit
	if (msvcrt.kbhit()):
   		if (ord(msvcrt.getch()) == 113):
   			quit = True
	return quit

print("------------------------------------------------------------")		
print("| WCFM ARCHIVER by Gary Chen '18")
print("| interval: \t\t" + str(RECORD_SECONDS/60) + " min")
print("| padding: \t\t" + str(PAD_OVERLAP/60) + " min")
print("| max # of files: \t" + str(MAX_FILES))
print("| approx size on disk: \t" + str(11*(RECORD_MIN+2*PAD_MIN)*MAX_FILES/1000) + " GB")

print("| capturing audio...")

stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

print("------------------------------------------------------------")

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
	formatHr = str(month).zfill(2) + "-" + str(day).zfill(2) + "-" + str(yr) + "-" + str(hr).zfill(2)
	
	# update count, set file name based on new count
	while (os.path.isfile("archives/" + WAVE_OUTPUT_FILENAME + "-" + formatHr + "-" + str(count).zfill(3) + ".wav")):
		count = count + 1
	fileName = WAVE_OUTPUT_FILENAME + "-" + formatHr + "-" + str(count).zfill(3) + ".wav"

	# delete oldest file
	while (len(fileNames) >= MAX_FILES):
		toDelete = fileNames.pop(0)
		if (toDelete != None):
			os.remove(toDelete)
			print("* DELETED: \t\t" + toDelete)

	# open file
	print("* now writing to: \tarchives/" + fileName)
	wf = wave.open("archives/" + fileName, 'wb')
	wf.setnchannels(CHANNELS)
	wf.setsampwidth(p.get_sample_size(FORMAT))
	wf.setframerate(RATE)
	fileNames.append("archives/" + fileName)

	# write -5 minutes from top of hour to file
	wf.writeframes(b''.join(framesOverlap))

	# write 55 min into the hour, or until keypress
	maxVol = 1
	while (not quitPressed() and int(time.time())%RECORD_SECONDS != (RECORD_SECONDS - PAD_OVERLAP)):
	   data = stream.read(CHUNK)
	   frame.append(data)
	   bitArr = array('h', data)
	   bitArr.append(maxVol)
	   maxVol = max(bitArr)
	   wf.writeframes(b''.join(frame))
	   frame = []


	# no silence detected
	if (maxVol >= THRESHOLD):
		# write +/-5 min at bottom of hour, and record into framesOverlap
		framesOverlap = []
		while (not quitPressed() and int(time.time())%RECORD_SECONDS != PAD_OVERLAP):
		   data = stream.read(CHUNK)
		   frame.append(data)
		   wf.writeframes(b''.join(frame))
		   frame = []
		   framesOverlap.append(data)

		# close audio file
		wf.close()

		# write to log
		log.write(fileName + " \t" + time.asctime(localtime) + "\n")
		log.flush()

		print("* done recording: \tarchives/" + fileName)
		print("------------------------------------------------------------")
	
	# silence detected
	else:
		wf.close()
		os.remove("archives/"+fileName)
		fileNames.pop(len(fileNames)-1)
		print("* DELETED SILENCE:  \tarchives/"+fileName)

		print("* still recording padding...")
		framesOverlap = []
		while (not quitPressed() and int(time.time())%RECORD_SECONDS != PAD_OVERLAP):
			data = stream.read(CHUNK)
			framesOverlap.append(data)



# CLEANUP:  Never runs, as of now.  
stream.stop_stream()
stream.close()
p.terminate()
log.close();
