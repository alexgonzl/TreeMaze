#!/usr/bin/python3

import os, sys
import argparse, serial, threading
import datetime,time

## Input Parameters
parser = argparse.ArgumentParser()
parser.add_argument("Experimenter_ID", help="Please indicate the experimenters ID")
parser.add_argument("Subject_ID", help="Please the Subject's ID")
parser.add_argument("Experiment_ID", help="Please indicate the experiment")
parser.add_argument("--code", help="Specific experimental protocol for the session")
parser.add_argument("--baud",type=int, choices = [9600,14400,19200,28800,38400,57600,115200],
                    help="Baud rate for arduino. Defaults to 115200.")
parser.add_argument("--save_folder", help="Data storage folder. \n Defaults to '/home/pi/Documents/TreeMaze/Data/Experiment/Subject_ID/'")
args = parser.parse_args()

experimenter = args.Experimenter_ID
subj_id = args.Subject_ID
expt = args.Experiment_ID

# baud rate
if args.baud:
    baud = args.baud
else:
    baud = 115200

# Code
if args.code:
    args.code
else:
    code = 'XXXX'

#Dictionary of event codes:

## File saving information.
time_str = datetime.datetime.now().strftime('%H:%M:%S')
time_str2 = datetime.datetime.now().strftime('h%H_m%M')
date_obj = datetime.date.today()
date_str = "%s_%s_%s" % (date_obj.month,date_obj.day,date_obj.year)
if args.save_folder:
    save_folder = args.save_folder
else:
    save_folder = "/home/pi/Documents/TreeMaze/Data/%s/%s/%s/" % (expt,subj_id,date_str)
filename = "%s_%s_%s" % (subj_id,date_str,time_str2)

# Header
os.makedirs(save_folder,exist_ok=True)
f = open("%s%s.txt" % (save_folder,filename),'w')
f.write("Date: %s \n" % date_str)
f.write("Current Time: %s \n" % time_str)
f.write("Experimenter: %s \n" % experimenter)
f.write("Subject: %s \n" % subj_id)
f.write("Experiment: %s \n" % expt)
f.write("Baud Rate: %s \n" % baud)
f.write("Experiment Code: %s \n" % code)
f.close()


## Serial comm with arduino
if args.baud:
    baud = args.baud
else:
    baud = 115200
arduino = serial.Serial('/dev/ttyUSB1',baud,timeout=0.1)
arduino.reset_input_buffer()
arduino.reset_output_buffer()

# data file
f = open("%s%s.csv" % (save_folder,filename),'w')
time_ref = time.time()

#### threads ##########
def readArduino(f, code, time_ref, arduinoEv, interruptEv): 
    while True:
        if not interruptEv.is_set():
            # reduce cpu load by reading arduino slower
            time.sleep(0.001)
            data = arduino.readline()[:-2] ## the last bit gets rid of the new-line chars
            if data:
                ## send event to interrupt other threads
                try:
                    if isinstance(data,bytes):
                        x = data.decode('utf-8')
                        if (x[0]=='<'):
                            if (x[1:4]=='EC_'):
                                code = x[4:]
                                print (code)
                                logEvent(f,code,time_ref)
                            else:
                                print (x[1:])
                        elif (x[0]=='>'):
                            arduinoEv.set()
                    else:
                        if data[0]=='>':
                            arduinoEv.set()
                        else:
                            print (data[1:])        
                except:
                    pass
        else:
            break
                

def getCmdLineInput(arduinoEv,interruptEv):
    time.sleep(1)
    while True:
        if not interruptEv.is_set():
            arduinoEv.wait(1)
            try:
                print ("Enter 'w' to activate a well")
                print ("Enter 'd' to activate a well")
                print ("Enter 's' to check status")
                print ("Enter 'r' to reset all wells")
                print ("Enter 'q' to exit")
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
                    elif (CL_in == "q"):
                        print ("Exiting arduino communication.")
                        interruptEv.set()
                        break
                    else:
                        print ("Invalid Instruction.\n")
                    print()
                else:
                    print(type(CL_in))
                    print("error")
            except:
                print ("error", sys.exc_info()[0])
            arduinoEv.clear()
        else:
            break

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

def logEvent(f, code, time_ref):
    f.write("%s,%f\n" % (code,time.time()-time_ref) )
    
# Main
arduinoEv = threading.Event()
interruptEv = threading.Event()

# Declare threads
t1 = threading.Thread(target = readArduino, args = (f, code, time_ref, arduinoEv, interruptEv,))
t2 = threading.Thread(target = getCmdLineInput, args = (arduinoEv,interruptEv,))

try:
    # Start threads  
    t1.start()
    t2.start()   
    
except KeyboardInterrupt:
    print ("Keyboard Interrupt. Arduino Comm closed.")
    f.close()
    arduino.close()
    interruptEv.set()
    t1.join()
    t2.join()
    quit()

except:
    print ("error", sys.exc_info()[0])
    f.close()
    arduino.close()
    interruptEv.set()
    t1.join()
    t2.join()
    quit()

    
