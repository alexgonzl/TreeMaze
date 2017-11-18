#!/usr/bin/python3

###
#  Master controller for the TreeMaze. It communicates with the arduino through serial port.
#  Receives data through GPIO inputs and serial.
###

import threading
from MazeHeader import *
PythonControlSet = ['T2','T3a','T3b','T4a','T4b']

# Parse Input:
baud,datFile,expt =ParseArguments()
# Set serial comm with arduino
Comm = ArdComm(baud)

# Creat Maze object
if expt in PythonControlSet:
    MS = Maze(Comm,expt)
else:
    MS = Maze(Comm)

# leave some time
time.sleep(0.2)

# Main
arduinoEv = threading.Event()
interruptEv = threading.Event()

# Declare threads
readArdThr = threading.Thread(target = readArduino, args = (MS,arduinoEv, interruptEv))
cmdLine = threading.Thread(target = getCmdLineInput, args = (MS,arduinoEv,interruptEv))

try:
    # Start threads
    readArdThr.start()
    cmdLine.start()

except KeyboardInterrupt:
    print ("Keyboard Interrupt. Arduino Comm closed.")
    close(MS)
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    quit()

except:
    print ("error", sys.exc_info()[0])
    close(MS)
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    quit()
