
import os, sys, argparse
import serial, string, sys, struct, datetime, time
from transitions import Machine
from transitions.extensions.states import add_state_features, Timeout, State
import random, copy
import numpy as np
import PyCmdMessenger
from collections import Counter

# #gpio.setmode(gpio.BOARD)
# GPIOChans = [33,35,36,37,38,40]
# IRD_GPIOChan_Map = {1:33, 2:35, 3:36, 4:37, 5:38, 6:40}
@add_state_features(Timeout)

class Machine2(Machine):
    pass

def close(MS):
    if MS.datFile:
        if hasattr(MS.datFile,'close'):
            MS.datFile.close()
    if MS.headFile:
        if hasattr(MS.headFile,'close'):
            MS.headFile.close()
    MS.Comm.close()

def ParseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("Experimenter_ID", help="Please indicate the experimenters ID")
    parser.add_argument("Subject_ID", help="Please the Subject's ID")
    parser.add_argument("Experiment_ID", help="Please indicate the experiment")
    parser.add_argument("--code", help="Specific experimental protocol for the session")
    parser.add_argument("--baud",type=int, choices = [9600,14400,19200,28800,38400,57600,115200],
                        help="Baud rate for arduino. Defaults to 115200.")
    parser.add_argument("--save", choices=['y','n'])
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

    ## File saving information.
    if args.save=='y':
        saveFlag = True
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
        headFile = open("%s%s.txt" % (save_folder,filename),'w')
        headFile.write("Date: %s \n" % date_str)
        headFile.write("Current Time: %s \n" % time_str)
        headFile.write("Experimenter: %s \n" % experimenter)
        headFile.write("Subject: %s \n" % subj_id)
        headFile.write("Experiment: %s \n" % expt)
        headFile.write("Baud Rate: %s \n" % baud)
        headFile.write("Experiment Code: %s \n" % code)

        # Data file
        datFile = open("%s%s.csv" % (save_folder,filename),'w')

    else:
        saveFlag = False
        headFile=[]
        datFile =[]

    return expt, baud, headFile, datFile, saveFlag

def logEvent(code,MS):
    MS.datFile.write("%s,%f\n" % (code,time.time()-MS.time_ref) )

# function for sending automatic commands to arduino without comand line input.
class ArdComm(object):
    """Spetialized functions for arduino communication."""
    def __init__(self,baud):
        try:
            self.ard = serial.Serial('/dev/ttyUSB0',baud,timeout=0.1)
        except:
            self.ard = serial.Serial('/dev/ttyUSB1',baud,timeout=0.1)
        self.ard.reset_input_buffer()
        self.ard.reset_output_buffer()

    def close(self):
        self.ard.__exit__()

    def SendDigit(self,num):
        # arduino reads wells zero based. adding
        self.ard.write(bytes([num+48]))

    def SendChar(self,ch):
        self.ard.write(ch.encode())

    def ReadLine(self):
        data = self.ard.readline()[:-2] # the last bit gets rid of the new-line chars
        return data

    def ActivateWell(self,well):
        if well>=0 and well <=5:
            self.SendChar('w')
            self.SendDigit(well)

    def DeActivateWell(self,well):
        if well>=0 and well <=5:
            self.SendChar('d')
            self.SendDigit(well)

    def ToggleLED(self,well):
        if well>=0 and well <=5:
            self.SendChar('l')
            self.SendDigit(well)

    def ActivateCue(self,cueNum):
        if cueNum>0 and cueNum <=9:
            self.SendChar('c')
            self.SendDigit(cueNum)

    def DeActivateCue(self):
        self.SendChar('y')

    def ActivateAllWells(self):
        self.SendChar('a')

    def DeliverReward(self,well):
        if well>=0 and well <=5:
            self.SendChar('p')
            self.SendDigit(well)

    def ChangeReward(self,well, dur):
        if well>=0 and well <=5:
            self.SendChar('z')
            self.SendDigit(well)
            dur_str = '<'+str(dur)+'>'
            for ch in dur_str:
                self.SendChar(ch)

    def Reset(self):
        self.SendChar('r')

class ArdComm2(object):
    """Spetialized functions for arduino communication."""
    # Must be in same order in arduino
     COMMANDS = [["kAcknowledge",""],   # 0
     ["kError","s"],                    # 1
     ["kSendEvent","s"],                # 2
     ["kStatus","s*"],                  # 3
     ["kActivateAllWells",""],          # 4
     ["kSelectWell_ACT",""],            # 5 -
     ["kSelectWell_DeACT",""],          # 6 -
     ["kToggleLED",""],                 # 7 -
     ["kLED_ON",""],                    # 8 -
     ["kLED_OFF",""],                   # 9 -
     ["kSelectPump_ON",""],             # 10
     ["kChangePumpDur",""],             # 11
     ["kTurnPumpOnForXDur",""],         # 12
     ["kSelectCUE_ON",""],              # 13 -
     ["kTurnCUE_OFF",""],               # 14 -
     ["kPrint_States",""],              # 15 -
     ["kReset_States",""],              # 16
      ]
    def __init__(self,baud):
        try:
            self.ard = serial.Serial('/dev/ttyUSB0',baud, timeout=0.1)
        except:
            self.ard = PyCmdMessenger.ArduinoBoard("\\.\COM3", baud_rate=baud, timeout=0.1)
        self.con = PyCmdMessenger.CmdMessenger(board_instance = self.ard, commands= self.COMMANDS, warnings=False)
    def close(self):
        self.ard.close()

    def ReceiveData(self):
        data = self.ard.readline()
        if isinstance(data,bytes):
            x = data.decode()
            if x!='': # if not empty
                if isintance(x[0],int):
                    ardsignal = x[0]
                    if ardsignal == '0': # acknowledge signal from arduino
                        print ("Ack from arduino.")
                    elif ardsignal == '1': # error signal from arduinoEv
                        print ("Arduino sent an error.")
                    elif ardsignal == '2': # event signal
                        return x.decode()[2:-1]
                    elif ardsignal == '3': # ard status
                        y = x.decode()[2:-1].split(",")
                        print ("Arduino Status Check.")
                        self.printListString(y)
                    else:
                        print("Unexpected Arduino.")
                return "NONE"

    def printListString(self,data):
        if isintance(data,list):
            for ii in data:
                print(ii)
        else:
            print("Error reading data from arduino")

    def ActivateAllWells(self):
        self.con.send("kActivateAllWells")

    def ActivateWell(self,well):
        if well>=0 and well <=5:
            self.con.send("kSelectWell_ACT",well,arg_formats="s")

    def DeActivateWell(self,well):
        if well>=0 and well <=5:
            self.con.send("kSelectWell_DeACT",well,arg_formats="s")

    def ActivateCue(self,cueNum):
        if cueNum>0 and cueNum <=9:
            self.con.send("kSelectCUE_ON",cueNum,arg_formats="s")

    def DeActivateCue(self):
        self.con.send("kTurnCUE_OFF")

    def DeliverReward(self,well):
        if well>=0 and well <=5:
            self.con.send("kSelectPump_ON",well,arg_formats="s")

    def ChangeReward(self,well, dur):
        if well>=0 and well <=5:
            self.con.send("kChangePumpDur",well,dur,arg_formats="ss")

    def DeliverSpecifiedReward(self,well,dur):
        if well>=0 and well <=5:
            self.con.send("kTurnPumpOnForXDur",well,dur, arg_formats= "ss")

    def LED_ON(self,well):
        if well>=0 and well <=5:
            self.con.send("kLED_ON",well,arg_formats="s")

    def LED_OFF(self,well):
        if well>=0 and well <=5:
            self.con.send("kLED_OFF",well,arg_formats="s")

    def Reset(self):
        self.con.send("kReset_States")

    def getArdStatus(self):
        self.con.send("kPrint_States")
        x = self.con.receive()
