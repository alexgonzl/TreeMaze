#!/usr/bin/python3

###
#  Master controller for the TreeMaze. It communicates with the arduino through serial port.
#  Receives data through GPIO inputs and serial.
###

import os, sys
import argparse, serial, threading
import datetime,time
from RPI.GPIO import GPIO
from MazeHeader import *



## Input Parameters
f,baud = ParseArguments()

## Set serial comm with arduino
ArdCommInst = ArdComm(baud) 

global time_ref = time.time()


TrialTypes = ["L","R"]
def TrialScheduler(arduinoEv,interruptEv):

# Main
arduinoEv = threading.Event()
interruptEv = threading.Event()

# Declare threads
readArdThr = threading.Thread(target = readArduino, args = (f, code, arduinoEv, interruptEv,))
cmdLine = threading.Thread(target = getCmdLineInput, args = (arduinoEv,interruptEv,))

try:
    # Start threads
    readArdThr.start()
    cmdLine.start()

except KeyboardInterrupt:
    print ("Keyboard Interrupt. Arduino Comm closed.")
    f.close()
    arduino.close()
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    quit()

except:
    print ("error", sys.exc_info()[0])
    f.close()
    arduino.close()
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    quit()
