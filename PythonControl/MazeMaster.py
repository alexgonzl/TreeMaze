#!/usr/bin/python3

###
#  Master controller for the TreeMaze. It communicates with the arduino through serial port.
#  Receives data through GPIO inputs and serial.
###

import threading
from MazeHeader import *

## Input Parameters
ParseArguments()

## Set serial comm with arduino
Comm = ArdComm()

global time_ref
time_ref = time.time()

# Main
arduinoEv = threading.Event()
interruptEv = threading.Event()

# Declare threads
readArdThr = threading.Thread(target = readArduino, args = (Comm, arduinoEv, interruptEv,))
cmdLine = threading.Thread(target = getCmdLineInput, args = (Comm,arduinoEv,interruptEv,))

try:
    # Start threads
    readArdThr.start()
    cmdLine.start()

except KeyboardInterrupt:
    print ("Keyboard Interrupt. Arduino Comm closed.")
    close()
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    quit()

except:
    print ("error", sys.exc_info()[0])
    close()
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    quit()
