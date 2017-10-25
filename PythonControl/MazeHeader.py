
import argparse
from transitions import Machine, State
import random
import numpy as np
from collections import Counter

GPIO.setmode(GPIO.BOARD)
GPIOChans = [33,35,36,37,38,40]
IRD_GPIOChan_Map = {1:33, 2:35, 3:36, 4:37, 5:38, 6:40}

class TrialSeq(object):
    def __init__(self,N):
        _CueTypes = [5,6]
        _nCueTypes = len(_CueTypes)
        _GoalIDs = [3,4,5,6]
        _GoalIDsByCue = {5:[3,4],6:[5,6]}
        _nGoalsByCue = {k: len(v) for k, v in _GoalIDsByCue.items()}

        # increase N if not divisible by number of conditions
        _nConds = 4
        while N%_nConds != 0:
            N = N+1

        # seq refers to the cue sequence, indicating trial type.
        _nTrialsPerCue = int(N/_nCueTypes)
        _seq = _CueTypes*_nTrialsPerCue # create sequence of length N for CueTypes
        _seq = np.array(np.random.permutation(_seq))

        # assign goal to cues
        _GoalSeq = np.zeros(N)-1
        for cue in _CueTypes:
            _sublist = _seq==cue
            _nTrialsPerCueGoal = int(_nTrialsPerCue/_nGoalsByCue[cue])
            _cuegoalseq = np.array(_GoalIDsByCue[cue]*_nTrialsPerCueGoal)
            _cuegoalseq = np.random.permutation(_cuegoalseq)
            _GoalSeq[_sublist] = _cuegoalseq

        # another implementation of goal allocation, no restrain for # of goal
#         for ii in range(N):
#             for jj in _CueTypes:
#                 rr = random.random():
#                 for kk in range(_GoalIDsByCue[jj]):
#                     if rr < (kk+1)*(1/_nGoalsByCue[jj]):
#                         self.GoalSeq[ii] = _GoalIDsByCue[jj][kk]
#                         break
        # del temp variables
        del _sublist, _cuegoalseq

        # visible variables
        self.N = N
        self.CueSeq = _seq
        self.GoalSeq = _GoalSeq.astype(int)
        self.CueIDs = _CueTypes
        self.GoalIDsByCue = _GoalIDsByCue
        self.CurrentTrial = 0

    def CueID(self):
        return self.CueSeq[self.CurrentTrial]
    def GoalID(self):
        return self.GoalSeq[self.CurrentTrial]
    def NextTrial(self):
        self.CurrentTrial = self.CurrentTrial + 1

    def SeqCounts(self):
        print("Number of trials = ", self.N)
        print("Trial Cue Counts: ")
        print(Counter(self.CueSeq))
        print("Trial Goal Counts: ")
        print(Counter(self.GoalSeq))

## This is the main state machine code.
 class Maze(object):
    nWells = 6
    nCues = 6
    def __init__(self):
      self.Act_Well = np.zeros(self.nWells,dtype=bool)
      self.PrevAct_Well = np.zeros(self.nWells,dtype=bool)
      self.Act_Cue  = 0
      self.DetectedWellNum = 0
      self.WellDetectSeq = []
      self.ValidWellDetectSeq = []
      self.StateChangeFlag = 0

    def activate_cue(self):
      # send command to activate relevant cue
      #self.Act_Cue
      pass
    def inactivate_cue(self):
      # send command to inactivate cue
      self.Act_Cue = 0

    def activate_well(self,well):
      if self.Act_Well[well]:
          print('activated well', well+1)
          ActivateWell(well)
          #send command to arduino

    def detect(self,well):
      #well = event.kwargs.get('well',0)
      well = well-1 # zero indexing the wells
      self.DetectedWellNum = well
      self.WellDetectSeq.append(well+1)
      if self.Act_Well[well]==True:
          self.Act_Well[well]=False
          self.ValidWellDetectSeq.append(well+1)

    def update_states(self):
      well = int(self.state[2:])
      self.PrevAct_Well = np.array(self.Act_Well)

      if (well==99): #activate all
          if all(self.Act_Well)==False:
              self.Act_Well[:] = True
      elif (well>=1 and well<=6):
          if self.Act_Well[well-1] == False:
              self.Act_Well[well-1] = True
      elif (well==34):
          if (self.Act_Well[2]==False):
              self.Act_Well[2]=True
          if (self.Act_Well[3]==False):
              self.Act_Well[3]=True
      elif (well==56):
          if (self.Act_Well[4]==False):
              self.Act_Well[4]=True
          if (self.Act_Well[5]==False):
              self.Act_Well[5]=True
      else: # inactivate all
          if any(self.Act_Well)==True:
              self.Act_Well[:] = False

      change_wells = np.array((self.PrevAct_Well != self.Act_Well).nonzero()).flatten()
      for ii in change_wells:
          self.activate_well(ii)


    def next_trial(self):
      pass
    def G34(self):
      if self.Act_Cue==5:
          return True
      return False
    def G56(self):
      if self.Act_Cue==6:
          return True
      return False
    def G3(self):
      pass
      # if sequence.goal(current trial) == 3
      # return true
    def G4(self): pass
    def G5(self): pass
    def G6(self): pass

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

        # Data file
        if args.save=='y':
            f = open("%s%s.csv" % (save_folder,filename),'w')
        else:
            f = []

        return f, baud

def readArduino(f, code, arduinoEv, interruptEv):
    while True:
        if not interruptEv.is_set():
            # reduce cpu load by reading arduino slower
            time.sleep(0.001)
            data = arduino.readline()[:-2] ## the last bit gets rid of the new-line chars
            if data:
                processArdData(data)
            else:
                break

def processArdData(arduinoEv, data):
    try:
        if isinstance(data,bytes):
            x = data.decode('utf-8')
            if (x[0]=='<'):
                if (x[1:4]=='EC_'):
                    code = x[4:]
                    print (code)
                    if args.save=='y':
                        logEvent(f,code,time_ref)
                else:
                    print (x[1:])
            elif (x[0]=='>'):
                arduinoEv.set()
            else:
                print (x)
        else:
            if data[0]=='>':
                arduinoEv.set()
            else:
                print (data)
    except:
        pass

def logEvent(f, code):
    f.write("%s,%f\n" % (code,time.time()-time_ref) )

# function for sending automatic commands to arduino without comand line input.
def ArdSendDigit(num):
    # arduino reads wells zero based. adding
    arduino.write(bytes([num+48]))
def ArdSendChar(ch):
    arduino.write(ch.encode())

def ArdActivateWell(well):
    ArdSendChar('w')
    ArdSendDigit(well)

def ArdDeActivateWell(well):
    ArdSendChar('d')
    ArdSendDigit(well)

def ArdActivateCue(cueNum):
    ArdSendChar('z')
    ArdSendDigit(cueNum)

def ArdDeActivateCue():
    ArdSendChar('y')

def ArdReset():
    ArdSendChar('r')

def ArdActivateAllWells():
    ArdSendChar('a')

def ArdChangePumpDur(well, dur):
    ArdSendChar('c')
    ArdSendDigit(well)
    dur_str = '<'+str(dur)+'>'
    for ch in dur_str:
        ArdSendChar(ch)

def getCmdLineInput(arduinoEv,interruptEv):
    ArdWellInstSet = ['w','d','p'] # instructions for individual well control
    ArdGlobalInstSet = ['a','s','r'] # instructions for global changes
    ArdPumpInst = 'c' # instruction to change pump duration.
    ArdCueInst = ['z','y'] # instructions for cue control
    time.sleep(1)
    while True:
        if not interruptEv.is_set():
            arduinoEv.wait(1)
            try:
                print ("Enter 'w' to activate a well")
                print ("Enter 'a' to activate all wells")
                print ("Enter 'p' to turn-on a pump")
                print ("Enter 'c' to change reward amount per well")
                print ("Enter 'd' to deactivate well")
                print ("Enter 'r' to reset all wells")
                print ("Enter 's' to check status")
                print ("Enter 'z' to turn on a cue")
                print ("Enter 'y' to turn off the cue")
                print ("Enter 'q' to exit")
                CL_in = input()
                if (isinstance(CL_in,str)):
                    # quit instruction
                    if (CL_in == "q"):
                        print ("Exiting arduino communication.")
                        interruptEv.set()
                        break
                    # global instructions
                    if any( ch in CL_in for ch in ArdGlobalInstSet):
                        arduino.write(CL_in.encode())
                    # individual wells
                    elif any( ch in CL_in for ch in ArdWellInstSet):
                        arduino.write(CL_in.encode())
                        getWell2Arduino()

                    # cue control
                    elif (CL_in=='z' or CL_in =='y'):
                        arduino.write(CL_in.encode())
                        if (CL_in =='z'):
                            num = input("Enter Cue Number [5-6]:")
                            if num.isnumeric():
                                cue = int(num)
                                if (cue>=1 and cue<=6):
                                    arduino.write(bytes([cue+48]))
                                else:
                                    print ("Invalid Cue Number")
                            else:
                                print ("Invalid Input")

                    # change pump duration.
                    elif (CL_in == ArdPumpInst):
                        arduino.write(CL_in.encode())
                        num = input("Enter Well Number:")
                        if num.isnumeric():
                            well = int(num)
                            if (well>=1 & well<=6):
                                arduino.write(bytes([well+48]))
                                dur = input("Enter Pump duration on (in ms), or 'x' to reset:")
                                print(dur)
                                if len(dur)>4:
                                    print("input needs to be less than 10s")
                                else:
                                    if dur.isnumeric(): # enter integer
                                        dur_int = int(dur)
                                        if (dur_int>0 & dur_int<1000):
                                            arduino.write("<".encode())
                                            for ch in dur:
                                                arduino.write(ch.encode())
                                                #print(ch.encode())
                                            arduino.write(">".encode())
                                    elif (dur=='x'): # reset to default
                                         arduino.write("<".encode())
                                         arduino.write("x".encode())
                                         arduino.write(">".encode())
                            else:
                                print ("Invalid Well Number")
                        else:
                            print ("Invalid Input to well.")
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

def IR_Detect():
    pass

def getWell2Arduino():
    well = input('Enter Well Number:')
    if well.isnumeric():
        well = int(well)-1;
        if (well>=0 & well<=5):
            arduino.write(bytes([well+48]))
        else:
            print ("Invalid Well Number")
    else:
        print ("Invalid Input")

states = [State(name='AW0',on_enter=['inactivate_cue']),
          State(name='AW1',on_enter='next_trial',on_exit=['activate_cue'],ignore_invalid_triggers=True),
          State(name='AW2'),
          'AW3','AW4','AW5','AW6','AW34','AW56'
         ]

conditions = ['G3','G4','G5','G6','G34','G56']
transitions = [
    {'trigger':'D1','source':'AW1','dest':'AW2'},
    {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':'inactivate_cue'},
    {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':'inactivate_cue'},
    {'trigger':'D2','source':'AW2','dest':'AW0'},

    {'trigger':'D3','source':'AW34','dest':'AW4'},
    {'trigger':'D3','source':'AW3','dest':'AW1'},
    {'trigger':'D4','source':'AW34','dest':'AW3'},
    {'trigger':'D4','source':'AW4','dest':'AW1'},

    {'trigger':'D5','source':'AW5','dest':'AW1'},
    {'trigger':'D5','source':'AW56','dest':'AW6'},
    {'trigger':'D6','source':'AW6','dest':'AW1'},
    {'trigger':'D6','source':'AW56','dest':'AW5'},

    {'trigger':'stop','source':'*','dest':'AW0'}]

MS = Maze()
machine = Machine(MS,states,transitions=transitions, ignore_invalid_triggers=True ,initial='AW0',
           after_state_change='update_states')
