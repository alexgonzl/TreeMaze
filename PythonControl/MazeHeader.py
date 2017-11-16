
import os, sys, argparse
import serial, datetime, time
from transitions import Machine, State
import random
import numpy as np
#from RPi.GPIO import GPIO as gpio
# import RPi.GPIO
from collections import Counter

# #gpio.setmode(gpio.BOARD)
# GPIOChans = [33,35,36,37,38,40]
# IRD_GPIOChan_Map = {1:33, 2:35, 3:36, 4:37, 5:38, 6:40}

global MS, StateMachine
global baud, datFile,saveFlag
global arduino
global PythonControlFlag
PythonControlFlag=False

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
    if datFile:
        if hasattr(datFile,'close'):
            datFile.close()
    arduino.__exit__()

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

    return baud

# Main Threads:
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
                                    if PythonControlFlag:
                                        detectNum = int(code[2])
                                        PythonControl('DD',detectNum)
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
def getCmdLineInput(ArdCommInst,arduinoEv,interruptEv):
    ArdWellInstSet = ['w','d','p','l','z'] # instructions for individual well control
    ArdGlobalInstSet = ['a','s','r','y'] # instructions for global changes
    PythonControlSet = ['T2','T3a','T3b','T4a','T4b']
    time.sleep(1)
    PythonControlFlag=False
    while True:
        if not interruptEv.is_set():
            # wait 1 second for arduino information to come in
            arduinoEv.wait(0.5)
            try:
                print ("Enter 'Auto=T#', for automatic sequencing.")
                print ("Enter 'Auto=C#', to queue a cue for the next trial.")
                print ("Enter 'Stop', to stop automation of well sequencing.")
                print()
                print ("Enter 'a','r' activate / reset all")
                print ("Enter 's' to check status")
                print ("Enter 'w#','d#', to activate/deactivate a well (e.g 'w1')")
                print ("Enter 'p#', to turn on pump (e.g 'p3') ")
                print ("Enter 'l#', to toggle LED (e.g 'l1') ")
                print ("Enter 'z#=dur' to change pump duration ('z4=20') ")
                print ("Enter 'c#','y' to turn on/off cues ('c1')")
                print ("Enter 'q' to exit")
                CL_in = input()
                if (isinstance(CL_in,str) and len(CL_in)>0):
                    if (CL_in[:4]=='Auto'):
                        if (CL_in[5:7] in PythonControlSet):
                            PythonControlFlag=True
                            PythonControl('setup',protocol=CL_in[5:7])
                            try:
                                cueinput = int(input('Enter cue to enable: '))
                                if cueinput>=1 and cueinput<=9:
                                    PythonControl('cue',cueinput)
                                PythonControl('start')
                            except:
                                print('Unable to start automation. Talk to Alex about it.')
                                PythonControl('stop')
                                pass
                        if (CL_in[5]=='C'):
                            PythonControl('cue',cue=cueinput)
                            print("Cue queued for the next trial.")

                    elif (CL_in=='Stop'):
                        PythonControl('Stop')
                        # stop thhingsss

                    ins = CL_in[0]
                    # quit instruction
                    if (ins == 'q'):
                        print('Terminating Arduino Communication')
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
                                if ins=='w' and not PythonControlFlag :
                                    ArdCommInst.ActivateWell(well)
                                elif ins=='d' and not PythonControlFlag :
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
                            print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)
                            print('Incorrect Instruction Format, Try again')
                            pass

                    # cue control
                    elif ins=='c' and not PythonControlFlag :
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

def logEvent(code):
    datFile.write("%s,%f\n" % (code,time.time()-time_ref) )

# function for sending automatic commands to arduino without comand line input.
class ArdComm(object):
    """Spetialized functions for arduino communication."""
    def __init__(self,baud):
        self.ard = serial.Serial('/dev/ttyUSB0',baud,timeout=0.1)
        self.ard.reset_input_buffer()
        self.ard.reset_output_buffer()

    def SendDigit(self,num):
        # arduino reads wells zero based. adding
        self.ard.write(bytes([num+48]))

    def SendChar(self,ch):
        self.ard.write(ch.encode())

    def ReadLine(self):
        data = self.ard.readline()[:-2] # the last bit gets rid of the new-line chars
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

class Maze(object):
    nWells = 6
    nCues = 6
    def __init__(self, protocol):
        self.Act_Well = np.zeros(self.nWells,dtype=bool)
        self.PrevAct_Well = np.zeros(self.nWells,dtype=bool)
        self.Act_Cue  = 0
        self.Act_Cue_State = False
        self.Queued_Cue = 0
        self.DetectedGoalWell = -1
        self.PrevDetectedGoalWell = -1
        self.WellDetectSeq = []
        self.ValidWellDetectSeq = []
        self.Protocol = protocol

    def activate_cue(self):
        # send command to activate relevant cue
        if self.Act_Cue_State:
            ArdComm.ActivateCue(self.Act_Cue)
    def enable_cue(self):
        # enables the use of cues
        self.Act_Cue_State = True
    def disable_cue(self):
        # this function disables the use of cues, until enabling it again
        self.Act_Cue_State = False
        self.Act_Cue = 0
        self.deactivate_cue()

    def deactivate_cue(self):
        # send command to deactivate cue, but does not disable the use of cue
        ArdComm.DeActivateCue()

    def activate_well(self,well):
        if self.Act_Well[well]:
          print('activated well', well+1)
          ArdComm.ActivateWell(well)

    def LED_ON(self):
        if self.Act_Well[well]:
          ArdComm.ToggleLED(well)

    def deactivate_well(self,well):
        if not self.Act_Well[well]:
          ArdComm.DeActivateWell(well)

    def detect(self,well):
        #well = event.kwargs.get('well',0)
        self.WellDetectSeq.append(well)
        well = well-1 # zero indexing the wells
        if self.Act_Well[well]==True:
            self.Act_Well[well]=False
            self.ValidWellDetectSeq.append(well+1)
            if (well>=1):
                self.PrevDetectGoalWell = well

    def update_states(self):
        state = int(self.state[2:])
        if state==1 and self.Queued_Cue!=0:
            if self.Queued_Cue != self.Act_Cue:
                self.Act_Cue=self.Queued_Cue
                self.Queued_C

        self.PrevAct_Well = np.array(self.Act_Well)
        if (state==123456): #activate all
            posWells=range(nWells)
        elif (state>=1 and state<=6):
            posWells = state-1
        elif (state==34):
            posWells = [2,3]
        elif (state==56):
            posWells = [4,5]
        elif (state==3456):
            posWells = [2,3,4,5]
        else: # inactivate all
            posWells=[]

        for well in range(nWells):
            if well in posWells:
                self.Act_Well[well] = True
            else:
                self.Act_Well[well] = False

        wells2activate = np.array((self.PrevAct_Well==False and self.Act_Well==True).nonzero()).flatten()
        wells2deactivate = np.array((self.PrevAct_Well==True and self.Act_Well==False).nonzero()).flatten()
        for well in wells2activate:
            self.activate_well(ii)
        for well in wells2deactivate:
            self.deactivate_well(ii)

    def next_trial(self):
        pass

    def G3456(self):
        return True

    def G34(self):
        if self.Act_Cue==5:
          return True
        return False

    def G56(self):
        if self.Act_Cue==6:
          return True
        return False

    def G3(self):
        if self.Act_Cue==1 or self.Act_Cue==2 or self.Act_Cue==5:
            if self.Protocol == 'T4a' or self.Protocol == 'T4b':
                if self.PrevDetectGoalWell==3:
                    return True
            else:
                return True
        return False

    def G4(self):
        if self.Act_Cue==1 or self.Act_Cue==2 or self.Act_Cue==5:
            if self.Protocol == 'T4a' or self.Protocol == 'T4b':
                if self.PrevDetectGoalWell==2:
                    return True
            else:
                return True
        return False

    def G5(self):
        if self.Act_Cue==3 or self.Act_Cue==4 or self.Act_Cue==6:
            if self.Protocol == 'T4a' or self.Protocol == 'T4b':
                if self.PrevDetectGoalWell==5:
                    return True
            else:
                return True
        return False

    def G6(self):
        if self.Act_Cue==3 or self.Act_Cue==4 or self.Act_Cue==6:
            if self.Protocol == 'T4a' or self.Protocol == 'T4b':
                if self.PrevDetectGoalWell==4:
                    return True
            else:
                return True
        return False

    def stop(self):
        self.Act_Well[:] = False
        self.Act_Cue_State = False
        self.Act_Cue = 0
        ArdComm.reset()

    def D0(self):
        pass

    def incorrectT3(self):
        print('Incorrect arm. Back to home well.')
        pass
    def incorrectT4_goal(self):
        print('Incorrect goal well.')
        pass
    def incorrectT4_arm(self):
        print('Incorrect arm. Back to home well.')
        pass

def PythonControl(inst,cue=0,protocol=[],detect=-1):
    """This function manages state transitions"""
    if PythonControlFlag:
        if inst == 'setup' and len(protocol)>0:
            MS = Maze(protocol)
            states,trans = MS_Setup(protocol)
            StateMachine = Machine(MS,states,transitions=trans,
            ignore_invalid_triggers=True , initial='AW0',
            after_state_change='update_states')

            Wells = [1,2,3,4,5,6]
            MS_Trigger = []
            # dummy first append tr
            MS_Trigger.append(getattr(MS,'D0'))
            for well in Wells:
                MS_Trigger.append(getattr(MS,'D'+str(well)))

        if inst == 'start':
            if MS.Act_Cue>0:
                MS.start()
            else:
                print('Cannot start without a cue')

        if inst == 'cue' :
            if cue>0:
                MS.Queued_Cue=cue

        if inst == 'DD' and detect>=0:
            try:
                detectNum = int(inst[2])
                if detectNum>=1 and detectNum <=6:
                    MS.detect(detectNum)
                    MS_Trigger[detectNum]()
            except:
                print('Invalid Detect')
                pass

        if inst == 'stop':
            PythonControlFlag=False
            MS.stop()
            print('Automatic control disabled.')

        if inst[""]:
            PythonControlFlag=False
            MS.stop()
            print('Unknown State. Disableling AutoControl.')
 

def MS_Setup(protocol):
        conditions = ['G3','G4','G5','G6','G34','G56','G3456']
        states =  [State(name='AW0', on_enter=['disable_cue'], ignore_invalid_triggers=True),
        State(name='AW1',on_enter=['enable_cue','next_trial','LED_ON'],on_exit=['activate_cue'], ignore_invalid_triggers=True),
        State(name='AW2',on_enter='LED_ON',ignore_invalid_triggers=True),
        State(name='AW3',on_enter='LED_ON',ignore_invalid_triggers=True),
        State(name='AW4',on_enter='LED_ON',ignore_invalid_triggers=True),
        State(name='AW5',on_enter='LED_ON',ignore_invalid_triggers=True),
        State(name='AW6',on_enter='LED_ON',ignore_invalid_triggers=True),
        State(name='AW34',ignore_invalid_triggers = True),
        State(name='AW56',ignore_invalid_triggers=True),
        State(name='AW3456',ignore_invalid_triggers=True),
        ]
        transitions = [
        # stop trigger
        {'trigger':'stop','source':'*','dest':'AW0','after':'disable_cue'},
        # start striger
        {'trigger':'start','source':'*','dest':'AW1','after':'enable_cue'},
        # valid global transitions
        {'trigger':'D1','source':'AW1','dest':'AW2'},
        {'trigger':'D3','source':['AW3','AW34','AW3456'],'dest':'AW1'},
        {'trigger':'D4','source':['AW4','AW34','AW3456'],'dest':'AW1'},
        {'trigger':'D5','source':['AW5','AW56','AW3456'],'dest':'AW1'},
        {'trigger':'D6','source':['AW6','AW56','AW3456'],'dest':'AW1'},
        ]

        if not (protocol in ['T2','T3a','T3b','T4a','T4b']):
            print('Undefined protocol. Defaulting to T2.')
            protocol = 'T2'

        if protocol=='T2':
            """T2 refers to training regime 2. In this regime the animal can obtain reward at all the goals. Note that there is only one rewarded goal location. """
            transitions = transitions + [
                {'trigger':'D2','source':'AW2','dest':'AW3456', 'conditions':'G3456','after':['deactivate_cue','LED_ON']}]

        elif protocol=='T3a':
            """T3 refers to training regime 3. In this regime the animal can obtain reward at the left or right goals depending on the cue with goal well LED ON. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':['deactivate_cue','LED_ON']},
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','LED_ON']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','LED_ON']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':['deactivate_cue','LED_ON']},
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','LED_ON']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','LED_ON']},

                ## incorrect choices
                {'trigger':'D3','source':'AW56','dest':'AW1','after':'incorrectT3'},
                {'trigger':'D4','source':'AW56','dest':'AW1','after':'incorrectT3'},

                {'trigger':'D5','source':'AW34','dest':'AW1','after':'incorrectT3'},
                {'trigger':'D6','source':'AW34','dest':'AW1','after':'incorrectT3'}]

        elif protocol=='T3b':
            """T3 refers to training regime 3. In this regime the animal can obtain reward at the left or right goals depending on the cue with goal without LEDs on the wells. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':['deactivate_cue']},
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':['deactivate_cue']},
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue']},

                ## incorrect choices
                {'trigger':'D3','source':'AW56','dest':'AW1','after':'incorrectT3'},
                {'trigger':'D4','source':'AW56','dest':'AW1','after':'incorrectT3'},

                {'trigger':'D5','source':'AW34','dest':'AW1','after':'incorrectT3'},
                {'trigger':'D6','source':'AW34','dest':'AW1','after':'incorrectT3'}]

        elif protocol=='T4a':
            """T4 class refers to training regime 4. In this regime the animal can obtain reward at alternating goal wells on any arm with LEDs. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

            transitions = transitions + [
                
                ## right goals
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':'deactivate_cue'},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':'deactivate_cue'},

                ## left goals
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':'deactivate_cue'},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':'deactivate_cue'},

                ## incorrect choices
                {'trigger':'D3','source':'AW4','dest':'=','after':'incorrectT4_goal'},
                {'trigger':'D3','source':['AW5','AW6'],'dest':'AW1','after':'incorrectT4_arm'},

                {'trigger':'D4','source':'AW3','dest':'=','after':'incorrectT4_goal'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'AW1','after':'incorrectT4_arm'},

                {'trigger':'D5','source':'AW6','dest':'=','after':'incorrectT4_goal'},
                {'trigger':'D5','source':['AW3','AW4'],'dest':'AW1','after':'incorrectT4_arm'},

                {'trigger':'D6','source':'AW5','dest':'=','after':'incorrectT4_goal'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'AW1','after':'incorrectT4_arm'},
                ]
            
        elif protocol=='T4b':
            """T4 class refers to training regime 4. In this regime the animal can obtain reward at alternating goal wells on any arm without LEDs. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

            transitions = transitions + [
                ## right goals
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','LED_ON']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','LED_ON']},

                ## left goals
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','LED_ON']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','LED_ON']},

                ## incorrect choices
                {'trigger':'D3','source':'AW4','dest':'=','after':'incorrectT4_goal'},
                {'trigger':'D3','source':['AW5','AW6'],'dest':'AW1','after':'incorrectT4_arm'},

                {'trigger':'D4','source':'AW3','dest':'=','after':'incorrectT4_goal'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'AW1','after':'incorrectT4_arm'},

                {'trigger':'D5','source':'AW6','dest':'=','after':'incorrectT4_goal'},
                {'trigger':'D5','source':['AW3','AW4'],'dest':'AW1','after':'incorrectT4_arm'},

                {'trigger':'D6','source':'AW5','dest':'=','after':'incorrectT4_goal'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'AW1','after':'incorrectT4_arm'},
                ]

        return states,transitions
# MS = Maze()
# StateMachine = Machine(MS,states,transitions=transitions, ignore_invalid_triggers=True ,initial='AW0',
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
