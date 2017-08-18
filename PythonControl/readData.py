#!/usr/bin/python

import serial, time, threading
arduino = serial.Serial('/dev/ttyUSB0',115200,timeout=0.1)

def readArduino():
    while True:
        data = arduino.readline()[:-2] #the last bit gets rid of the new-line chars
        if data:
            print data
            
def sendWellInputToArduino(well):
    arduino.write(bytes(well))
    
def getCmdLineInput():
    while True:
        cmin = input("well number = ")
        sendWellInputToArduino(cmin)

t1 = threading.Thread(target=readArduino)
t2 = threading.Thread(target=getCmdLineInput)
    
t1.start()
t2.start()
