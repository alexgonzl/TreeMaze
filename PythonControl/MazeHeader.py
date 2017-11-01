
import os, sys, argparse
import serial, datetime, time
from transitions import Machine, State
import random
import numpy as np
#from RPi.GPIO import GPIO as gpio
import RPi.GPIO
from collections import Counter

#gpio.setmode(gpio.BOARD)
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

def close():
    if hasattr(datFile,'close'): 
        datFile.close()
    arduino.__exit__()

    ## This is the main state machine code.
class Maze(object):
    nWells = 6
    nCues = 6
    def __init__(self):
        self.Act_Well = np.zeros(self.nWells,dtype=bool)
        self.PrevAct_Well = np.zeros(self.nWells,dtype=bool)
        self.LED_Status = np.zeros(self.nWells,dtype=bool)
        self.Act_Cue  = 0
        self.Act_Cue_State = False
        self.DetectedWellNum = 0
        self.WellDetectSeq = []
        self.ValidWellDetectSeq = []
        self.StateChangeFlag = 0

    def activate_cue(self):
        # send command to activate relevant cue
        if self.Act_Cue > 1:
            self.Act_Cue_State = True
            ArdComm.ActivateCue(self.Act_Cue)

    def deactivate_cue(self):
        # send command to inactivate cue
        self.Act_Cue_State = False
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
        state = int(self.state[2:])
        self.PrevAct_Well = np.array(self.Act_Well)

        if (state==99): #activate all
          if all(self.Act_Well)==False:
              self.Act_Well[:] = True
        elif (state>=1 and state<=6):
          if self.Act_Well[state-1] == False:
              self.Act_Well[state-1] = True
        elif (state==34):
          if (self.Act_Well[2]==False):
              self.Act_Well[2]=True
          if (self.Act_Well[3]==False):
              self.Act_Well[3]=True
        elif (state==56):
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
        if self.Act_Cue==1 or self.Act_Cue==2:
            return True
        return False
    def G4(self):
        if self.Act_Cue==1 or self.Act_Cue==2:
            return True
        return False
    def G5(self):
        if self.Act_Cue==3 or self.Act_Cue==4:
            return True
        return False
    def G6(self):
        if self.Act_Cue==3 or self.Act_Cue==4:
            return True
        return False
    def stop(self):
         self.Act_Well[:] = False
         self.Act_Cue = 0
         self.Act_Cue_State = False


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
    global baud
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
    global datFile
    global saveFlag
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
        h = open("%s%s.txt" % (save_folder,filename),'w')
        h.write("Date: %s \n" % date_str)
        h.write("Current Time: %s \n" % time_str)
        h.write("Experimenter: %s \n" % experimenter)
        h.write("Subject: %s \n" % subj_id)
        h.write("Experiment: %s \n" % expt)
        h.write("Baud Rate: %s \n" % baud)
        h.write("Experiment Code: %s \n" % code)
        h.close()

        # Data file
        datFile = open("%s%s.csv" % (save_folder,filename),'w')

    else:
        saveFlag = False
        datFile =[]

def readArduino(ArdCommInst,arduinoEv, interruptEv):
    while True:
        if not interruptEv.is_set():
            # reduce cpu load by reading arduino slower
            time.sleep(0.001)
            data = ArdCommInst.ReadLine()
            try:
                if data:
                    try:
                        if isinstance(data,bytes):
                            x = data.decode('utf-8')
                            if (x[0]=='<'):
                                if (x[1:4]=='EC_'):
                                    code = x[4:]
                                    print (code)
                                    if saveFlag:
                                        logEvent(code)
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
                        #print ("error", sys.exc_info()[0])
                        pass
            except:
                #print ("error", sys.exc_info()[0])
                pass
        else:
            break

def logEvent(code):
    datFile.write("%s,%f\n" % (code,time.time()-time_ref) )

# function for sending automatic commands to arduino without comand line input.
class ArdComm(object):
    """Spetialized functions for arduino communication."""
    def __init__(self):
        global arduino
        arduino = serial.Serial('/dev/ttyUSB0',baud,timeout=0.1)
        arduino.reset_input_buffer()
        arduino.reset_output_buffer()

    def SendDigit(self,num):
        # arduino reads wells zero based. adding
        arduino.write(bytes([num+48]))

    def SendChar(self,ch):
        arduino.write(ch.encode())

    def ReadLine(self):
        data = arduino.readline()[:-2] # the last bit gets rid of the new-line chars
        return data

    def ActivateWell(self,well):
        self.SendChar('w')
        self.SendDigit(well)

    def DeActivateWell(self,well):
        self.SendChar('d')
        self.SendDigit(well)

    def ToggleLED(self,well):
        self.SendChar('l')
        self.SendDigit(well)

    def ActivateCue(self,cueNum):
        self.SendChar('c')
        self.SendDigit(cueNum)

    def DeActivateCue(self):
        self.SendChar('y')

    def ActivateAllWells(self):
        self.SendChar('a')

    def DeliverReward(self,well):
        self.SendChar('p')
        self.SendDigit(well)

    def ChangeReward(self,well, dur):
        self.SendChar('z')
        self.SendDigit(well)
        dur_str = '<'+str(dur)+'>'
        for ch in dur_str:
            self.SendChar(ch)

    def Reset():
        self.SendChar('r')

def getCmdLineInput(ArdCommInst,arduinoEv,interruptEv):
    ArdWellInstSet = ['w','d','p','l','z'] # instructions for individual well control
    ArdGlobalInstSet = ['a','s','r','y'] # instructions for global changes
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
                print ("Enter 'l#', to toggle LED (e.g 'l1') ")
                print ("Enter 'z#=dur' to change pump duration ('z4=20') ")
                print ("Enter 'd#' to deactivate a well ('d5')")
                print ("Enter 'c#' to turn on a cue ('c1')")
                print ("Enter 'y' to turn off the cue")
                print ("Enter 'q' to exit")
                CL_in = input()

                if (isinstance(CL_in,str) and len(CL_in)>0):
                    ins = CL_in[0]
                    # quit instruction
                    if (ins == 'q'):
                        print('Terminating Arduino Communication')
                        #ArdCommInst.SendChar(ins)
                        #time.sleep(1)
                        interruptEv.set()
                        close()
                        break
                    # global instructions: a,s,r,y
                    elif ins in ArdGlobalInstSet:
                        ArdCommInst.SendChar(ins)
                    # actions on individual wells
                    elif ins in ArdWellInstSet:
                        try:
                            well = int(CL_in[1])-1 # zero indexing the wells
                            if well>=0 and well <=5:
                                if ins=='w':
                                    ArdCommInst.ActivateWell(well)
                                elif ins=='d':
                                    ArdCommInst.DeActivateWell(well)
                                elif ins=='p':
                                    ArdCommInst.DeliverReward(well)
                                elif ins=='l':
                                    ArdCommInst.ToggleLED(well)
                                elif ins=='z':
                                    try:
                                        dur = int(CL_in[3:])
                                        if dur>0 and dur<=1000:
                                            ArdCommInst.ChangeReward(well,dur)
                                    except:
                                        print('Invalid duration for reward.')
                        except:
                            #print ("error", sys.exc_info()[0])
                            print('Incorrect Instruction Format, Try again')
                            pass

                    # cue control
                    elif ins=='c':
                        try:
                            cuenum = int(CL_in[1])
                            if cuenum>=1 & cuenum<=6:
                                ArdCommInst.ActivateCue(cuenum)
                            else:
                                print('Invalid Cue Number')
                        except:
                            print('Invalid Cue Number')
                            pass
            except:
                print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)
            arduinoEv.clear()
        else:
            break

def T3(object):
    """T3 class refers to training regime 3. In this regime the animal can obtain reward at the left or right goals depending on the cue. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

    states = [State(name='AW0', on_enter=['deactivate_cue'], ignore_invalid_triggers=True), State(name='AW1',on_enter=['deactivate_cue','next_trial'],on_exit=['activate_cue'], ignore_invalid_triggers=True),
    State(name='AW2',ignore_invalid_triggers=True),
    State(name='AW34',ignore_invalid_triggers=True),
    State(name='AW56',ignore_invalid_triggers=True)
    ]

    conditions = ['G3','G4','G5','G6','G34','G56']
    transitions = [
        # start/stop
        {'trigger':'stop','source':'*','dest':'AW0'},
        {'trigger':'start','source':'*','dest':'AW1'},

        # valid transitions
        {'trigger':'D1','source':'AW1','dest':'AW2'},

        # goals on the right
        {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':'deactivate_cue'},
        {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':'deactivate_cue'},
        {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':'deactivate_cue'},

        # goals on the left
        {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':'deactivate_cue'},
        {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':'deactivate_cue'},
        {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':'deactivate_cue'},

        # correct choices
        {'trigger':'D3','source':'AW34','dest':'AW1'},
        {'trigger':'D4','source':'AW34','dest':'AW1'},

        {'trigger':'D5','source':'AW56','dest':'AW1'},
        {'trigger':'D6','source':'AW56','dest':'AW1'},

        # incorrect choices
        {'trigger':'D3','source':'AW56','dest':'AW1','after':'incorrect'},
        {'trigger':'D4','source':'AW56','dest':'AW1','after':'incorrect'},

        {'trigger':'D5','source':'AW34','dest':'AW1','after':'incorrect'},
        {'trigger':'D6','source':'AW34','dest':'AW1','after':'incorrect'},

        # # error transitions
        # {'trigger':'D1','source':'*','dest':'AW0','after':'error'},
        # {'trigger':'D2','source':'*','dest':'AW0','after':'error'},
        # {'trigger':'D3','source':'*','dest':'AW0','after':'error'},
        # {'trigger':'D4','source':'*','dest':'AW0','after':'error'},
        # {'trigger':'D5','source':'*','dest':'AW0','after':'error'},
        # {'trigger':'D6','source':'*','dest':'AW0','after':'error'}
        ]

def T4():
        """T4 class refers to training regime 4. In this regime the animal can obtain reward at alternating goal wells on any arm. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

        states = [
            State(name='AW0', on_enter=['inactivate_cue'], ignore_invalid_triggers=True),
            State(name='AW1',on_enter='next_trial',on_exit=['activate_cue'], ignore_invalid_triggers=True),
            State(name='AW2',ignore_invalid_triggers=True),
            State(name='AW3',ignore_invalid_triggers=True),
            State(name='AW4',ignore_invalid_triggers=True),
            State(name='AW5',ignore_invalid_triggers=True),
            State(name='AW6',ignore_invalid_triggers=True)
        ]

        conditions = ['G3','G4','G5','G6','G34','G56']
        transitions = [
            # stop
            {'trigger':'stop','source':'*','dest':'AW0'},

            # basic
            {'trigger':'D1','source':'AW1','dest':'AW2'},

            # right goals
            {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':'inactivate_cue'},
            {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':'inactivate_cue'},
            {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':'inactivate_cue'},


            # left goals
            {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':'inactivate_cue'},
            {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':'inactivate_cue'},

            # go back
            {'trigger':'D3','source':'AW3','dest':'AW1'},
            {'trigger':'D4','source':'AW4','dest':'AW1'},
            {'trigger':'D5','source':'AW5','dest':'AW1'},
            {'trigger':'D6','source':'AW6','dest':'AW1'},

            # error transitions
            {'trigger':'D1','source':'*','dest':'AW0','after':'error'},
            {'trigger':'D2','source':'*','dest':'AW0','after':'error'},
            {'trigger':'D3','source':'*','dest':'AW0','after':'error'},
            {'trigger':'D4','source':'*','dest':'AW0','after':'error'},
            {'trigger':'D5','source':'*','dest':'AW0','after':'error'},
            {'trigger':'D6','source':'*','dest':'AW0','after':'error'}
            ]

#MS = Maze()
#machine = Machine(MS,states,transitions=transitions, ignore_invalid_triggers=True ,initial='AW0',
#           after_state_change='update_states')

# # list of detections
# dlist = [1,2,3,4,1,2,4,3,1,2,3,5,6]
# goals = [1,2,3,4,5,6]
# cuelist = [5,5,6,6,5,6]
# detect_callback = []
# MS.Act_Cue=5
# for ii in goals:
#     detect_callback.append(getattr(MS,'D'+str(ii)))
#
#
# MS.to_AW1()
# trialcount =0
# for ii in dlist:
#     print(MS.state)
#     if ii==1 and MS.state==1:
#         MS.activate_cue=cuelist(trialcount)
#         trialcount=trialcount+1
#     MS.detect(ii)
#     detect_callback[ii-1]()
