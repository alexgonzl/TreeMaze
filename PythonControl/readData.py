#!/usr/bin/python3

import serial, time, threading, sys
arduino = serial.Serial('/dev/ttyUSB1',115200,timeout=0.1)
arduino.reset_input_buffer()
arduino.reset_output_buffer()

def readArduino(e): 
    while True:
        data = arduino.readline()[:-2] ## the last bit gets rid of the new-line chars
        if data:
            ## send event to interrupt other threads
            try:
                if isinstance(data,bytes):
                    x = data.decode('utf-8')
                    if (x[0]=='<'):
                        print (x[1:])
                    elif (x[0]=='>'):
                        e.set()
                else:
                    if data[0]=='>':
                        e.set()
                    else:
                        print (data[1:])        
            except:
                pass

def getCmdLineInput(e):
    time.sleep(2)
    while True:
        e.wait(1)
        try:
            print ("Enter 'w' to activate a well")
            print ("Enter 'd' to activate a well")
            print ("Enter 's' to check status")
            print ("Enter 'r' to reset all wells") 
            CL_in = input()            
            if (isinstance(CL_in,str)):
                if (CL_in == "w"):
                    arduino.write("w".encode())
                    num = input('Enter Well Number:')
                    if num.isnumeric():
                        well = int(num);
                        if (well>=1 & well<=6):
                            arduino.write(bytes([well+48]))
                        else:
                            print ("Invalid Well Number")
                    else:
                        print ("Invalid Input")
                elif (CL_in == "d"):
                    arduino.write("d".encode())
                    num = input('Enter Well Number:')
                    if num.isnumeric():
                        well = int(num);
                        if (well>=1 & well<=6):
                            arduino.write(bytes([well+48]))
                        else:
                            print ("Invalid Well Number")
                    else:
                        print ("Invalid Input") 
                elif (CL_in == "s" ):
                    arduino.write("s".encode())
                elif (CL_in == "r"):
                    arduino.write("r".encode())
                else:
                    print ("Invalid Instruction.\n")
                print()
            else:
                print(type(CL_in))
                print("error")
        except:
            print ("error", sys.exc_info()[0])
        e.clear()

def getWell2Arduino():   
    well = input('Enter Well Number:')
    if well.isnumeric():
        well = int(well);
        if (well>=1 & well<=6):
            arduino.write(bytes([num+48]))
        else:
            print ("Invalid Well Number")
    else:
        print ("Invalid Input")

arduinoInputEv = threading.Event()
# Start threads
t1 = threading.Thread(target=readArduino,args=(arduinoInputEv,))
t2 = threading.Thread(target=getCmdLineInput,args=(arduinoInputEv,))
    
t1.start()
t2.start()
