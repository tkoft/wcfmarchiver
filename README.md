# The WCFM Archival Tool
https://github.com/tkoft/wcfmarchiver

[bit.ly/WCFMarchives](http://bit.ly/WCFMarchives)

#### Overview
The WCFM Archiver:

1. is a small Python script for Windows
2. uses the PyAudio library to record from the default recording input
* writes recorded audio as separate .wav files 
* delimits files by absolute time intervals
* adds a specified amount of "padding" or "overlap" to the beginning and end of recordings  
* immediately deletes silent recordings, identified by a specified threshold
* only keeps a specified number of recordings, deleting the oldest ones if necessary
* write file names with the hour and number of file, and keeps an output log of filenames and their creation time
* reads and stores settings in a .ini config file
* exits with the "q" key

## More Details
### 1. About the Script
It's a single file, `wcfmarchiver.py`.  It can be packaged as a .exe executable using pyinstaller (try `makeexe.bat`).  Look in the `dist` directory.
  
### 2. Libraries
[PyAudio website](https://people.csail.mit.edu/hubert/pyaudio/).  Other standard libraries used:  `wave, time, os.path, msvcrt, array, configparser`

### 3. WAVE File Writing
Uses the Python `wave` library.

### 4. Recording Intervals
Interval recording uses _absolute_ epoch time, which means it's modular from 00:00:00 January 1, 1970.  So intervals of 60min will always be delimited at the top of each hour, 30min at the top and middle, 90min at every hour and a half starting at midnight, etc... I'd stay away from prime numbers.  So starting a 60min interval archival at 03:36 will record the rest of the hour, then start a new file at 04:00.


### 5. Padding
The Archiver adds a specified amount of "padding" or "overlap" to the beginning and end of recordings.  How this works is when the archiver starts a new file, it writes the padding from the pevious one first before resuming recording straight from audio input.  The archiver writes straight to file until (interval end time - pad amount).  Then it starts recording audio to internal storage, and also to the previous file if it wasn't silence, until (interval end time + pad amount).  The next file begins, and it again adds the previous pad audio to the beginning of the next one before resuming recording straight to file.  

### 6. Silence Detection
The Archiver tracks the max level of the entire recording, including the front padding but not the back.  I'm not sure what the units are, it just does something with the actual wave bit data written to file, but I know it works.  At (interval end time - pad amount), the program checks the max level against the threshold and deletes the file if it doesn't pass.  

This means if you only make noise on your hour-long show for the last 5 minutes, it will not be saved.  But that will be saved as part of the next show no matter what, since the next time silence is checked that padding will be included.  Moral of the story:  front padding of interval is checked for silence, not back.  

### 7. File Limit
The Archiver keeps an index of all the files it has written, and will delete the oldest (the first, sorted alphabetically) file once the specified file limit is reached.  If the "DeleteOld" option is specified, the Archiver indexes all `.wav` files in its `/archives` directory at program start , and will also delete those if necessary.  

### 8. Output Filenames and Log
The Archiver save output files under the `/archives` directory, and names them with the specified name from the config file, the year, month, day, hour, and the number of recording for that hour:
  `/archives/filename-yyyy-mm-dd-hh-##.wav`
  
When each file is completed (and not deleted from silence), it's logged into `/archives/outputLog.txt` with the filename and the time it was created (interval start time + padding amount).  

### 9. Configuration and Settings
Settings are stored in `config.ini` and interpreted using Python's configparser library.  If the file doesn't exist, if will be created; if a setting is missing, it will be written with the default value.  Currently, the entire file is re-written each time the program starts, so things might be in a different order than you left them after you run the Archiver, but all the values should be preserved.

Recording settings that can be specified in the config file:

|Label |Default |Description |
|------|---------|---------| 
|RecordMin|`60`|Recording interval.|
|PadMin|`5`|Amount of padding to add to the start and end of interval.|
|WaveOutoputFilename|`wcfm`|Name for WAVE files.|
|MaxFiles|`200`|Maximum number of files to keep before deleting oldest.|
|DeleteOld|`False`|Delete files from previous instance of program if necessary.  Defaults false to be safe, but should probably be changed to true.|
|Threshold|`333`|Silence threshold, not sure what units are.|

**NOTE:** `DeleteOld` does NOT specify whether files are deleted once the limit is reached.  It specifies whether .wav files that were in the archives directory _before the program was started_ should be indexed and deleted as well.  See _7. File Limit_ below.

 File settings that can be specified in the config file:

|Label |Default |Description |
|------|---------|---------|
|Chunk|`1024`|Samples written to file at a time from stream|
|Format|`8`|WAVE encoding format, use values from [PyAudio documentation](https://people.csail.mit.edu/hubert/pyaudio/docs/#pyaudio.paFloat32)|
|Channels|`2`|Just use `2`|
|Rate|`44100`|Sampling rate.|

### 10. Termination
The program clean-exits at any time using the 'q' key.  Lowercase only right now, lol.  It will execute the rest of the main control loop, skipping recording loops, close all streams and files, stop recording, still check for silence and delete if silent.

ONE CAVEAT:  If the program is closed or terminated, unexpectedly or not, during the padding interval after a silent recording that was deleted, anything recorded during that padding will be saved in `temp.wav`.  Basically, whenever the program says "DELETED: filename.wav, still recording padding..." it writes to `temp.wav` until the next file starts, then deletes it since it's saved in the new file.  `temp.wav` only exists to save this bit of audio in case the program terminates.

### Extraneous Info

The control loop is maybe better shown like this:

1. Program start or new file begins:  check if old file(s) should be deleted
2. Write previous padding to new file
3. Write stream directly to file until (interval end - padding amount)
4. Check silence
  * If file so far is silence, assume no need for padding; write stream to internal storage only until (interval end + padding amount)
  * Else write stream to both file and internal storage until (interval end + padding amount).
6. Write to output log, rinse and repeat


All output from the program is saved to `out.txt`.  This is the actual program output, not the archive log.

