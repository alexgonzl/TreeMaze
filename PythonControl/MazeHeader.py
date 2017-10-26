
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
      ArdComm.ActivateCue(self.Act_Cue)

    def deactivate_cue(self):
      # send command to inactivate cue
      self.Act_Cue = 0
      ArdComm.DeActivateCue()

    def activate_well(self,well):
      if self.Act_Well[well]:
          print('activated well', well+1)
          ArdComm.ActivateWell(well)

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
class ArdComm(object):
    """Spetialized functions for arduino communication."""
    def __init__(self,baud):
        arduino = serial.Serial('/dev/ttyUSB0',baud,timeout=0.1)
        arduino.reset_input_buffer()
        arduino.reset_output_buffer()

    def SendDigit(self,num):
        # arduino reads wells zero based. adding
        self.arduino.write(bytes([num+48]))

    def SendChar(self,ch):
        self.arduino.write(ch.encode())

    def ActivateWell(self,well):
        SendChar('w')
        SendDigit(well)

    def DeActivateWell(self,well):
        SendChar('d')
        SendDigit(well)

    def ActivateCue(self,cueNum):
        SendChar('z')
        SendDigit(cueNum)

    def DeActivateCue(self):
        SendChar('y')

    def ActivateAllWells(self):
        SendChar('a')

    def DeliverReward(self,well):
        SendChar('p')
        SendDigit(well)

    def ChangeReward(self,well, dur):
        SendChar('c')
        SendDigit(well)
        dur_str = '<'+str(dur)+'>'
        for ch in dur_str:
            SendChar(ch)

    def Reset():
        SendChar('r')

def getCmdLineInput(ArdComm,arduinoEv,interruptEv):
    ArdWellInstSet = ['w','d','p','c'] # instructions for individual well control
    ArdGlobalInstSet = ['a','s','r','y'] # instructions for global changes
    ArdPumpInst = 'c' # instruction to change pump duration.
    ArdCueInst = ['z','y'] # instructions for cue control
    time.sleep(1)
    while True:
        if not interruptEv.is_set():
            # wait 1 second for arduino information to come in
            arduinoEv.wait(1)
            try:
                print ("Enter 'a' to activate all wells")
                print ("Enter 'r' to reset all wells")
                print ("Enter 's' to check status")
                print ("Enter 'w#', to activate a well (e.g 'w1')")
                print ("Enter 'p#', to turn on pump (e.g 'p3') ")
                print ("Enter 'z#=dur' to change pump duration ('z4=20') ")
                print ("Enter 'd#' to deactivate a well ('d5')")
                print ("Enter 'c#' to turn on a cue ('c1')")
                print ("Enter 'y' to turn off the cue")
                print ("Enter 'q' to exit")
                CL_in = input()

                if (isinstance(CL_in,str)):
                    ins = CL_in[0]
                    # quit instruction
                    if (ins == 'q'):
                        print ("Exiting arduino communication.")
                        ArdComm.SendChar(CL_in)
                        interruptEv.set()
                        break
                    # global instructions: a,s,r,y
                    elif any( ch in ins for ch in ArdGlobalInstSet):
                        ArdComm.SendChar(ch)
                    # actions on individual wells
                    elif any( ch in ins for ch in ArdWellInstSet):
                        try:
                            well = int(CL_in[1])-1 # zero indexing the wells
                            if well>=0 and well <=5:
                                if ins=='w':
                                    ArdComm.ActivateWell(well)
                                elif ins=='d':
                                    ArdComm.DeActivateWell(well)
                                elif ins=='p':
                                    ArdComm.DeliverReward(well)
                                elif ins=='z':
                                    try:
                                        dur = int(CL_in[3:])
                                        if dur>0 and dur<=1000:
                                            ArdComm.ChangeReward(well,dur)
                                    except
                                        print('Invalid duration for reward.')
                        except:
                            print('Incorrect Instruction Format, Try again')
                            pass

                    # cue control
                    elif (ins=='c'):
                        try:
                            cuenum = int(CL_in[1])
                            if cuenum=>1 & cuenum<=6:
                                ArdComm.ActivateCue(cuenum)
                        except:
                            print('Invalid Cue Number')
                            pass
            except:
                print ("error", sys.exc_info()[0])
            arduinoEv.clear()
        else:
            break


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
