
import os, sys, argparse
import serial, string, sys, struct, datetime, time
from transitions import Machine, State
from transitions.extensions.states import add_state_features, Timeout
#from transitions import Machine
#from transitions.extensions.states import add_state_features, Timeout, State
import random, copy
import numpy as np
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
    if MS.saveFlag:
        np.save(MS.npyFile,MS.data)
    MS.Comm.close()

def ParseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("Experimenter_ID", help="Please indicate the experimenters ID")
    parser.add_argument("Subject_ID", help="Please the Subject's ID")
    parser.add_argument("Experiment_ID", help="Please indicate the experiment")
    parser.add_argument("--code", help="Specific experimental protocol for the session")
    parser.add_argument("--baud",type=int, choices = [9600,14400,19200,28800,38400,57600,115200], help="Baud rate for arduino. Defaults to 115200.")
    parser.add_argument("--save", choices=['y','n'])
    parser.add_argument("--verbose", choices=['y','n'])
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

    if args.verbose:
        verbose = args.verbose
    else:
        verbose = False

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

        # numpy file name
        npyFile = "%s%s" % (save_folder,filename)
    else:
        saveFlag = False
        headFile=[]
        datFile =[]
        npyFile =[]

    return expt, baud, verbose, headFile, datFile, saveFlag, npyFile

def logEvent(code,MS):
    try:
        if isinstance(code,str):
            MS.datFile.write("%s,%f\n" % (code,time.time()-MS.time_ref) )
        elif isinstance(code,list):
            for cc in code:
                MS.datFile.write("%s,%f\n" % (cc,time.time()-MS.time_ref) )
    except:
        print("error saving data")

class ArdComm(object):
    """Spetialized functions for arduino communication."""
    def __init__(self,baud,verbose=False):
        try:
            self.ard = serial.Serial('/dev/ttyUSB0',baud,timeout=0.1)
        except:
            #self.ard = serial.Serial('/dev/ttyUSB1',baud,timeout=0.1)
            self.ard = serial.Serial('/dev/ttyACM1',baud,timeout=0.1)
            

        #self.ard.flush()
        #self.ard.reset_input_buffer()
        if hasattr(self.ard,'reset_input_buffer'):
            self.ard.reset_input_buffer()
        elif hasattr(self.ard,'flushInput'):
            self.ard.flushInput()
        if hasattr(self.ard,'reset_output_buffer'):
            self.ard.reset_output_buffer()
        elif hasattr(self.ard,'flushOutput'):
            self.ard.flushOutput()
        self.verbose = verbose
        # empty the buffer
        self.ard.readline()
        self.ard.readline()

    def close(self):
        self.ard.close()

    def SendDigit(self,num):
        # arduino reads wells zero based. adding
        self.ard.write(bytes([num+48]))

    def SendChar(self,ch):
        self.ard.write(ch.encode())

    def datsplit(self,data):
        try:
            if isinstance(data,str) and data!='':
                commands = data.split(';')
                #out_list=[]
                #for com in commands:
                #    com_elem = com.split(',')
                #    com_list = []
                #    for el in com_elem:
                #        com_list.append(el)
                #    out_list.append(com_list)
                return commands
            else:
                return ['','']
        except:
            print('Data Splittig Error', sys.exc_info())
            return ['','']
            

    def ReceiveData(self):
        try:
            ardSignal = []
            ardDat = []
            data = self.ard.readline()
            
            time.sleep(1)
            if isinstance(data,bytes):
                dat = data.decode().strip('\r\n').split(';')
                x = dat
                #x = self.datsplit(dat)
                #print(x,len(x))
                #print(dat_list)
                #for x in dat_list:
               
                sig = x[0]
                if sig!='': # if not empty
                    if sig == '0': # acknowledge signal from arduino
                        ardSignal.append(0)
                        ardDat.append([])
                        if self.verbose:
                            if len(x)>1:
                                print("Ack. ",x[1])
                            else:
                                print ("Ack from arduino.")
                    elif sig == '1': # error signal from arduinoEv
                        ardSignal.append(1)
                        ardDat.append(x[1])
                        print ("Arduino sent an error.")
                        #print(x[1])
                    elif sig == '2': # event signal
                        ardSignal.append(2)
                        ardDat.append(x[1])
                    elif sig == '3': # ard status
                        ardSignal.append(3)
                        ardDat.append([])
                        print(x[1])
                    elif sig == '4': # state vector
                        try:
                            dat_state = list(map(int,x[1].split('-')))
                            ardSignal.append(4)
                            ardDat.append(dat_state)
                        except:
                            print('Error reading an arduino data update',sys.exc_info())
                        if self.verbose:
                            print(x[1])
                    else:
                        ardSignal.append(-1)
                        ardDat.append([])

               # elif len(x)>1:
               #     if self.verbose:
               #         print(x[1])

            return ardSignal,ardDat
        except UnicodeDecodeError:
            print('Decoding data error.', sys.exc_info())
            print(ardSignal,ardDat)
            return ardSignal,ardDat
        except:
            print("Error reading data. ", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2])
            return ardSignal,ardDat

    def GetStateVec(self):
        #self.con.send("kStatusReq");
        #self.ard.write("S")
        self.SendChar("x")
        self.SendChar("S")
        self.SendChar("V")
        self.SendChar("y")

    def getArdStatus(self):
        #self.con.send("kPrint_States")
        self.SendChar("x")
        self.SendChar("S")
        self.SendChar("T")
        self.SendChar("y")

    def ActivateAllWells(self):
        #self.con.send("kActivateAllWells")
        self.SendChar('x')
        time.sleep(0.01)
        self.SendChar('w')
        time.sleep(0.01)
        self.SendChar('A')
        time.sleep(0.01)
        self.SendChar('y')
        time.sleep(0.01)

    def ActivateWell(self,well):
        if well>=0 and well <=5:
            #self.con.send("kSelectWell_ACT",well,well,well,arg_formats="iii")
            self.SendChar("x")
            self.SendChar("w")
            self.SendChar("a")
            self.SendDigit(well)
            self.SendChar("y")

    def DeActivateWell(self,well):
        if well>=0 and well <=5:
            #self.con.send("kSelectWell_DeACT",well,well,well,arg_formats="iii")
            self.SendChar("x")
            self.SendChar("w")
            self.SendChar("d")
            self.SendDigit(well)
            self.SendChar("y")

    def DeActivateAllWells(self):
        self.SendChar("x")
        self.SendChar("w")
        self.SendChar("D")
        self.SendChar("y")

    def All_LED_ON(self):
        self.SendChar("x")
        self.SendChar("l")
        self.SendChar("A")
        self.SendChar("y")

    def LED_ON(self,well):
        if well>=0 and well <=5:
            self.SendChar("x")
            self.SendChar("l")
            self.SendChar("a")
            self.SendDigit(well)
            self.SendChar("y")

    def All_LED_OFF(self):
        self.SendChar("x")
        self.SendChar("l")
        self.SendChar("D")
        self.SendChar("y")

    def LED_OFF(self,well):
        if well>=0 and well <=5:
            self.SendChar("x")
            self.SendChar("l")
            self.SendChar("d")
            self.SendDigit(well)
            self.SendChar("y")

    def ActivateCue(self,cueNum):
        if cueNum>0 and cueNum <=9:
            self.SendChar("x")
            self.SendChar("c")
            self.SendChar("a")
            self.SendDigit(cueNum)
            self.SendChar("y")

    def DeActivateCue(self):
        self.SendChar("x")
        self.SendChar("c")
        self.SendChar("d")
        self.SendChar("y")

    def DeliverReward(self,well):
        if well>=0 and well <=5:
            self.SendChar("x")
            self.SendChar("p")
            self.SendChar("a")
            self.SendDigit(well)
            self.SendChar("y")

    def ChangeReward(self,well, dur):
        if well>=0 and well <=5:
            self.SendChar("x")
            self.SendChar("p")
            self.SendChar("c")
            self.SendChar("w")
            self.SendDigit(well)
            self.SendChar("d")
            dur_str = str(dur)
            if len(dur_str)==1:
                dur_str='00'+dur_str
            elif len(dur_str)==2:
                dur_str='0'+dur_str
            for ch in dur_str:
                self.SendChar(ch)
            self.SendChar("y")

    def DeliverSpecifiedReward(self,well,dur):
        if well>=0 and well <=5:
            if dur>=0 and dur<=999:
                self.SendChar("x")
                self.SendChar("p")
                self.SendChar("s")
                self.SendChar("w")
                self.SendDigit(well)
                self.SendChar("d")
                dur_str = str(dur)
                if len(dur_str)==1:
                    dur_str='00'+dur_str
                elif len(dur_str)==2:
                    dur_str='0'+dur_str
                for ch in dur_str:
                    self.SendChar(ch)
                self.SendChar("y")

    def Reset(self):
        self.SendChar('r')

class Maze(object):
    def __init__(self, Comm, protocol="null",headFile=[],datFile =[],npyFile=[],saveFlag=False):
        try:
            self.Comm = Comm
            self.Protocol = protocol
            self.headFile = headFile
            self.datFile = datFile
            self.npyFile  = npyFile
            self.saveFlag = saveFlag

            self.PythonControlFlag = False
            self.time_ref = time.time()

            self._T3_Protocols = ['T3a','T3b','T3c','T3d','T3e','T3f','T3g','T3h','T3i','T3j']
            self._T4_Protocols = ['T4a','T4b','T4c','T4d']
            self._T5_Protocols = ['T5La','T5Lb','T5Lc','T5Ra','T5Rb','T5Rc']

            if protocol!="null":
                # Settings
                self.DefaultRewardDurations = np.array([4,5,10,10,10,12])
                self.RewardDurations = np.array([4,5,10,10,10,12])
                self.TimeOutDuration = 10 # seconds to  wait post incorrect trial.
                # number of consecuitve trials to a given well results in a
                # change of reward. This is a protocol specific variable.
                self.ChangeRewardDur = 6
                # This variable changes the  behavior of the maze for a given number of Trials.
                # this is a protocol specific variable.
                self.EarlyTrialThr = 4
                # time to deactivate cue post decision well (if applicable to protocol)
                self.CueDeactivateTime =  2


                # Stable Variable Initiation.
                self.nWells = 6
                self.Wells = np.arange(self.nWells)
                self.GoalWells = [2,3,4,5]
                self.LeftGoals = [4,5]
                self.RightGoals = [2,3]
                self.nCues = 6

                #  State Variables.
                self.Act_Well = np.zeros(self.nWells,dtype=bool)
                self.PrevAct_Well = np.zeros(self.nWells,dtype=bool)
                self.LED_State = np.zeros(self.nWells,dtype=bool)
                self.Act_Cue  = 0
                self.Act_Cue_State = False
                self.Queued_Cue = 0

                # Record keeping variables
                self.DetectedGoalWell = -1
                self.PrevDetectGoalWell = -1
                self.WellDetectSeq = []
                self.ValidWellDetectSeq = []
                self.DetectionTracker = np.zeros(self.nWells)
                self.CorrectWellsTracker = np.zeros(self.nWells)
                self.ConsecutiveCorrectWellTracker = np.zeros(self.nWells)

                self.DataFields = ['TrialNum','CueID','GoalID','FirstDetectedGoal',
                'SecDetectedGoal','TrialDur','Correct',
                'SwitchTrial','SoftwareErrorFlag']
                self.Data = np.zeros(len(self.DataFields))

                # Reward Tracking
                self.NumRewardsToEachWell = np.zeros(6)
                self.CumulativeRewardDurPerWell = np.zeros(6)
                self.TotalRewardDur = 0
                self.ChangedRewardFlag = False
                self.ResetRewardFlag = False
                self.ChangedRewardWell = -1
                self.ConsecutiveWellRewardThr = 4

                # Trial Tracking
                self.TrialCounter = 0
                self.TrialTime = -1
                self.TrialDur = -1
                self.CueTimerFlag = False
                self.CueTimer = -1
                self.CorrectTrialFlag = False
                self.IncorrectTrialFlag = False
                self.NumCorrectTrials = 0
                self.NumConsecutiveCorrectTrials = 0
                self.TrialGoalWell = -1
                self.TrialFirstDetectedGoal = -1
                self.TrialSecondDetectedGoal = -1
                self.IncorrectArm = 0
                self.IncorrectGoal = 0
                self.NumSwitchTrials = 0
                self.CorrectAfterSwitch = 0
                self.SwitchProb = 0
                self.SwitchFlag = False
                self.SoftwareErrorFlag=False

                # random initiation to chance variables
                self.PrevDetectedGoalWell = np.random.choice(self.GoalWells)
                self.PrevDetectedRightGoalWell = np.random.choice(self.RightGoals)
                self.PrevDetectedLeftGoalWell = np.random.choice(self.LeftGoals)

                # True states from arduino
                self.Ard_Act_Well_State = np.zeros(self.nWells,dtype=bool)
                self.Ard_LED_State = np.zeros(self.nWells,dtype=bool)
                self.Ard_Reward_Dur = np.zeros(self.nWells)

                # Ard/Python state incongruency variables.
                self.IncongruencyFlag=False
                self.IncongruencyTimer = time.time()+120

                if self.Protocol[:2] in ['T3','T4','T5']:
                    while True:
                        try:
                            temp = input('Please enter cue switch probability [0 to 100].')
                            if int(temp)>=0 and int(temp)<=100:
                               self.SwitchProb = float(temp)/100.0
                               break
                            else:
                                print('Invalid Switch Probability')
                        except:
                            print("Error interpreting probability,  try again.")
                            continue
                # State machine creation specefic by protocol
                states,trans, self.ValidCues = MS_Setup(protocol,self.TimeOutDuration)
                StateMachine = Machine2(self,states=states,transitions=trans,
                    ignore_invalid_triggers=True , initial='AW0')

                #  Detection Trigger Creation. Includes a dummy D0 trigger.
                self.TRIGGER = []
                self.TRIGGER.append(getattr(self,'D0'))
                for well in (self.Wells+1):
                    self.TRIGGER.append(getattr(self,'D'+str(well)))

        except:
            print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

    ############################################################################
    ############# Main Control Functions #######################################
    def START(self):
        try:
           # start with valid cues for each protocol. Unless user input.
            if not (self.Act_Cue in self.ValidCues):
                if self.Protocol[:2] in ['T5']:
                    # for T5 choose the alternating cue.
                    self.Act_Cue = self.ValidCues[0]
                elif self.Protocol != 'T2': # for othe protocol choose at random.
                    if random.random()<0.5:
                        self.Act_Cue = copy.copy(self.ValidCues[0])
                    else:
                        self.Act_Cue = copy.copy(self.ValidCues[1])

            # reset all previous states on Arduino
            self.Comm.Reset()
            time.sleep(0.1)
            self.PythonControlFlag = True
            self.resetRewardsDurs()
            self.start()
        except:
             print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

    def STOP(self):
        if self.PythonControlFlag:
            self.PythonControlFlag=False
            print('Automatic control disabled.')
            self.STATUS()
            self.stop()
            self.Act_Well.fill(False)
            self.Act_Cue_State = False
            self.Act_Cue = 0
            self.printSummary()

        self.Comm.Reset()

    def DETECT(self,well):
        #well = event.kwargs.get('well',0)
        try:
            self.WellDetectSeq.append(well)
            if (self.TrialGoalWell>2) and (well in self.GoalWells):
                if self.TrialFirstDetectedGoal == -1:
                    self.TrialFirstDetectedGoal = well
                if self.TrialSecondDetectedGoal == -1:
                    self.TrialSecondDetectedGoal = well

            well = well-1 # zero indexing the wells
            self.DetectionTracker[well] += 1

            if self.Act_Well[well] == True:
                self.ValidWellDetectSeq.append(well+1)
                self.CorrectWellsTracker[well] += 1
                # Goal Wells
                if well in self.GoalWells:
                    # increase counter for consecuitve correct detections on the same well
                    self.ConsecutiveCorrectWellTracker[well] += 1
                    self.PrevDetectGoalWell = copy.copy(well)
                    if well in self.RightGoals:
                        self.PrevDetectedRightGoalWell = copy.copy(well)
                        # reset counter on right arm if detections on both wells
                        if all(self.ConsecutiveCorrectWellTracker[self.RightGoals]>0):
                            self.ConsecutiveCorrectWellTracker[self.RightGoals] = 0
                            self.ResetRewardFlag = True
                    else:
                        self.PrevDetectedLeftGoalWell = copy.copy(well)
                        # reset counter on left arm if detections on both wells
                        if all(self.ConsecutiveCorrectWellTracker[self.LeftGoals]>0):
                            self.ConsecutiveCorrectWellTracker[self.LeftGoals] = 0
                            self.ResetRewardFlag = True

            #print('well ',well)
            self.TRIGGER[well+1]()
        except:
            print("Error on registering the detection")
            print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

    def NEW_TRIAL(self):
        self.CorrectTrialFlag = False
        self.IncorrectTrialFlag = False
        self.NumConsecutiveCorrectTrials = 0
        self.ConsecutiveCorrectWellTracker[self.GoalWells] = 0
        self.Comm.Reset()
        self.ResetRewards()
        self.start()

    def STATUS(self):
        print()
        print('======= State Machine Status =========')
        print('Protocol = ',self.Protocol)
        print('Switch Prob = ', self.SwitchProb)
        print('Active Cue = ', self.Act_Cue)
        print('Queued Cue = ', self.Queued_Cue)
        print('Current State = ', self.state)
        print('SM Act. Wells = ', self.Act_Well)
        print('SM Well LEDs = ', self.LED_State)
        print('Previous Goal = ', self.PrevDetectedGoalWell)
        print('Trial Number = ', self.TrialCounter)
        print('# of Correct Trials = ', self.NumCorrectTrials)
        print('Number of Switches = ', self.NumSwitchTrials)
        print('Number of Correct Switches = ', self.CorrectAfterSwitch)
        print('Total Reward Dur = ', self.TotalRewardDur)
        print('# of Rewards Per Well = ', self.NumRewardsToEachWell)
        print('=====================================')

    ############################################################################
    ############# Support Functions ############################################
    def ResetRewards(self):
        self.ChangedRewardFlag = False
        self.ResetRewardFlag = False
        self.ChangedRewardWell = -1
        for well in self.Wells:
            self.Comm.ChangeReward(well,self.DefaultRewardDurations[well])

    def printSummary(self):
        if hasattr(self.headFile,'write'):
            self.headFile.write('Last Cue Switch Probability = %i \n' % (self.SwitchProb))
            self.headFile.write('\n\n====================================================\n\n')
            self.headFile.write('Session Summary:\n')
            self.headFile.write('Session Time = %f \n' % (time.time() - self.time_ref))
            self.headFile.write('Number of Trials = %i \n' % (self.TrialCounter))
            self.headFile.write('Number of Correct Trials = %i \n' % (self.NumCorrectTrials))
            self.headFile.write('Number of Switches = %i \n'  % (self.NumSwitchTrials))
            self.headFile.write('Number of Correct Trials after a Switch = %i \n' % (self.CorrectAfterSwitch))
            self.headFile.write('Number of Incorrect Arm Trials = %i \n' % (self.IncorrectArm))
            self.headFile.write('Number of Incorrect Goal Trials = %i \n' % (self.IncorrectGoal))

            self.headFile.write('Number of Well Detections: \n')
            self.headFile.write(", ".join(map(str,self.DetectionTracker.astype(int))))

            self.headFile.write('\nNumber of Correct Well Detections: \n')
            self.headFile.write(", ".join(map(str,self.CorrectWellsTracker.astype(int))))

            self.headFile.write('\nTotal Reward Duration = %i \n' % (self.TotalRewardDur))
            self.headFile.write('Number of Rewards Per Well:\n')
            self.headFile.write(", ".join(map(str,self.NumRewardsToEachWell.astype(int))))

            self.headFile.write('\nTotal Reward Duration Per Well:\n')
            self.headFile.write(", ".join(map(str,self.CumulativeRewardDurPerWell.astype(int))))

    def UpdateArdStates(self,stateVec):

        try:
            well = int(stateVec[0])
            self.Ard_Act_Well_State[well] = stateVec[1]
            self.Ard_LED_State[well] = stateVec[2]
            self.Ard_Reward_Dur[well] = stateVec[3]
        except:
            print("warning: couldn't update arduino states.",sys.exc_info())

    def InnerStateCheck(self,well):
        try:
            if well==0:
                if self.IncongruencyFlag==False:
                    self.IncongruencyTimer = time.time()
                else:
                    self.IncongruencyFlag=False


            if self.Ard_Act_Well_State[well]==False and self.Act_Well[well]:
                self.Comm.ActivateWell(well)
                self.IncongruencyFlag=True
                print("activation disagreement")
            if self.Ard_Act_Well_State[well] and self.Act_Well[well]==False:
                self.Comm.DeActivateWell(well)
                self.IncongruencyFlag=True
                print("deactivation disagreement")
            if self.LED_State[well]==False and self.Ard_LED_State[well]:
                self.Comm.LED_OFF(well)
                self.IncongruencyFlag=True
                print("Led off disagreement")
            if self.LED_State[well] and self.Ard_LED_State[well]==False:
                self.Comm.LED_ON(well)
                self.IncongruencyFlag=True
                print("Led on disagreement")

            if (well==5):
                if self.IncongruencyFlag:
                    print("Obtaining Ard States again")
                else:
                    self.IncongruencyTimer = time.time()+2
                    self.IncongruencyFlag=False

        except:
            print("Warning. Error checking states",sys.exc_info())
    ############# CUE Functions ################################################
    def enable_cue(self):
        # enables the use of cues
        self.Act_Cue_State = True

    def disable_cue(self):
        # this function disables the use of cues, until enabling it again
        self.Act_Cue_State = False
        self.Act_Cue = 0
        self.deactivate_cue()

    def activate_cue(self):
        # send command to activate relevant cue
        if self.Act_Cue_State:
            self.Comm.ActivateCue(self.Act_Cue)

    def deactivate_cue(self):
        # send command to deactivate cue, but does not disable the use of cue
        self.Comm.DeActivateCue()

    def deactivate_cue_timer(self):
        # deactivates cue after a determine time has elapsed
        self.CueTimerFlag = True
        self.CueTimer = time.time()

    ############# Well Functions ###############################################
    def activate_well(self,well):
        try:
            if self.Act_Well[well]==False:
                self.Act_Well[well]=True
            self.Comm.ActivateWell(well)
        except:
            print ("error", sys.exc_info())

    def deactivate_well(self,well):
        if self.Act_Well[well]==True:
            self.Act_Well[well]=False
        self.Comm.DeActivateWell(well)
        ## if not self.Act_Well[well]:
        ##    self.Comm.DeActivateWell(well)

    def LED_Active_ON(self):
        for well in self.Wells:
            if self.Act_Well[well] and self.LED_State[well]:
                self.Comm.LED_ON(well)
                time.sleep(0.001)
    def LED_ON(self,well):
        if self.LED_State[well]==False:
            self.LED_State[well]=True
        self.Comm.LED_ON(well)
    def LED_OFF(self,well):
        if self.LED_State[well]==True:
            self.LED_State[well]=False
        self.Comm.LED_OFF(well)

    ############# State Machine Callbacks ######################################
    def update_states(self):
        #self.Comm.GetStateVec()
        try:
            if self.is_TimeOut() or self.is_AW0():
                state = 0
            else:
                state = int(self.state[2:])

            #### trial specific updates (when activating home well)
            if state == 1:
                self.CorrectTrialFlag = False
                self.IncorrectTrialFlag = False

                if self.Protocol not in ['T3e','T3f','T3g','T3h','T3i','T3j']:
                    ## reset rewards duration if animal didn't repeat
                    if self.ChangedRewardFlag:
                        # reset to reward duration to  original
                        if self.ResetRewardFlag:
                            self.Comm.ChangeReward(self.ChangedRewardWell,self.DefaultRewardDurations[self.ChangedRewardWell])
                            self.ChangedRewardFlag = False
                            self.ResetRewardFlag = False
                            self.ChangedRewardWell = -1
                    else:
                        # Check if too many consecutive rewards to goal wells
                        for well in self.Wells:
                            if self.ConsecutiveCorrectWellTracker[well] >= self.ConsecutiveWellRewardThr:
                                self.ChangedRewardFlag = True
                                self.ChangedRewardWell = copy.copy(well)
                                self.Comm.ChangeReward(well,self.ChangeRewardDur)
                                print ("More than 4 consecutive rewards to well# ", well+1)
                                print ("Reducing reward to ", self.ChangeRewardDur)

                ## check for a cue change if in home well
                if self.Queued_Cue!=0:
                    if not self.ChangedRewardFlag:
                        if self.Queued_Cue in self.ValidCues:
                            if self.Queued_Cue != self.Act_Cue:
                                self.NumSwitchTrials +=1
                                self.Act_Cue = copy.copy(self.Queued_Cue)
                                self.SwitchFlag = True
                                self.Queued_Cue = 0
                            else:
                                self.SwitchFlag = False
                                self.Queued_Cue = 0
                        else:
                            print ("Invalid Cue for this Protocol")
                    else:
                        print ("Cue can't change until animal resets rewards")
                else:
                    self.SwitchFlag = False

            ### activate/deactivate wells based on current state
            self.PrevAct_Well = np.array(self.Act_Well)
            #self.PrevAct_Well = np.array(self.Ard_Act_Well_State)

            posWells=[]

            if (state==123456): #activate all
                posWells=np.array(self.Wells)
            elif (state>=1 and state<=6):
                posWells += [state-1]
            elif (state==34):
                posWells += [2,3]
            elif (state==56):
                posWells += [4,5]
            elif (state==3456):
                posWells += [2,3,4,5]

            for well in self.Wells:
                if well in posWells:
                    self.Act_Well[well] = True
                    # all current protocols LED on for wells 1 and 2 if active.
                    if self.Protocol[0:2] in ['T0','T1','T2','T3','T4']:
                        if well in [0,1]:
                            self.LED_State[well]=True

                    # Depending on protocol LEDs on goal wells must be on or not.
                    if self.Protocol in ['T2','T3a','T3d','T3f','T3h','T3j']:
                        self.LED_State[well]=True

                else:
                    self.Act_Well[well] = False
                    self.LED_State[well]= False

            # Python States
            temp = np.logical_and(self.PrevAct_Well==False, self.Act_Well==True)
            wells2activate = self.Wells[temp]

            temp = np.logical_and(self.PrevAct_Well==True, self.Act_Well==False)
            wells2deactivate = self.Wells[temp]

            if len(wells2deactivate)>0:
                for well in wells2deactivate:
                    self.deactivate_well(well)
                    self.LED_State[well]= False
                    #self.LED_OFF(well)
                    time.sleep(0.001)

            if len(wells2activate)>0:
                for well in wells2activate:
                    self.activate_well(well)
                    time.sleep(0.001)

            # Turn on LED lights on special cases:
            # another way to do this is to put a clause in the tranistion check
            # trial number and then do LED_ON()
            if state>=3 and state <=6:
                # turn on lights at begining of alternation trials
                if self.Protocol in ['T4b','T4c','T5Rb','T5Rc','T5Lb','T5Lc'] and self.TrialCounter<=self.EarlyTrialThr:
                    self.LED_State[state-1] = True

            # Turn LEDs on for LED_State==True
            self.LED_Active_ON()

            # Let all changes occur on Arduino
            time.sleep(0.01)
            # Report back arduino states
            self.Comm.GetStateVec()

        except:
            print ('Error updating states')
            print (sys.exc_info())

    def G3456(self):
        self.TrialGoalWell = 3456
        return True

    ## right goals
    def G34(self):
        if self.Protocol[:2] in ['T3','T5']:
            if self.Act_Cue==5:
                self.TrialGoalWell = 34
                return True
        return False

    def G3(self):
        if self.Act_Cue==1 or self.Act_Cue==2 or self.Act_Cue==5:
            if self.Protocol[:2] in ['T4','T5']:
                if self.PrevDetectedRightGoalWell==3:
                    self.TrialGoalWell = 3
                    return True
                else:
                    return False
            elif self.Protocol in ['T3e','T3f','T3g','T3h','T3i','T3j']:
                if random.random()<0.5:
                    self.TrialGoalWell = 3
                    return True
                else:
                    return False
            else:
                return True
        return False

    def G4(self):
        if self.Act_Cue==1 or self.Act_Cue==2 or self.Act_Cue==5:
            if self.Protocol[:2] in ['T4','T5']:
                if self.PrevDetectedRightGoalWell==2:
                    self.TrialGoalWell = 4
                    return True
                else:
                    return False
            elif self.Protocol in ['T3e','T3f','T3g','T3h','T3i','T3j']:
                self.TrialGoalWell = 4
                return True
            else:
                return True
        return False

    ## left goals
    def G56(self):
        if self.Protocol[:2] in ['T3','T5']:
            if self.Act_Cue==6:
                self.TrialGoalWell = 56
                return True
        return False

    def G5(self):
        if self.Act_Cue==3 or self.Act_Cue==4 or self.Act_Cue==6:
            if self.Protocol[:2] in ['T4','T5']:
                if self.PrevDetectedLeftGoalWell==5:
                    self.TrialGoalWell = 5
                    return True
                else:
                    return False
            elif self.Protocol in ['T3e','T3f','T3g','T3h','T3i','T3j']:
                if random.random()<0.5:
                    self.TrialGoalWell = 5
                    return True
                else:
                    return False
            else:
                self.TrialGoalWell = 5
                return True
        return False

    def G6(self):
        if self.Act_Cue==3 or self.Act_Cue==4 or self.Act_Cue==6:
            if self.Protocol[:2] in ['T4','T5']:
                if self.PrevDetectedLeftGoalWell==4:
                    self.TrialGoalWell = 6
                    return True
                else:
                    return False
            elif self.Protocol in ['T3e','T3f','T3g','T3h','T3i','T3j']:
                self.TrialGoalWell = 6
                return True
            else:
                return True
        return False

    def D0(self):
        pass

    # Reward processing
    def rewardDelivered(self,well):
        self.NumRewardsToEachWell[well]+=1
        self.updateRewardCount()

    def rewardDelivered1(self):
        self.NumRewardsToEachWell[0]+=1
        self.updateRewardCount()

    def rewardDelivered2(self):
        self.NumRewardsToEachWell[1]+=1
        self.updateRewardCount()

    def rewardDelivered3(self):
        self.NumRewardsToEachWell[2]+=1
        self.updateRewardCount()

    def rewardDelivered4(self):
        self.NumRewardsToEachWell[3]+=1
        self.updateRewardCount()

    def rewardDelivered5(self):
        self.NumRewardsToEachWell[4]+=1
        self.updateRewardCount()

    def rewardDelivered6(self):
        self.NumRewardsToEachWell[5]+=1
        self.updateRewardCount()

    def resetRewardsDurs(self):
        for well in self.Wells:
            self.Comm.ChangeReward(well,self.DefaultRewardDurations[well])

    def updateRewardCount(self):
        self.CumulativeRewardDurPerWell = np.multiply(self.RewardDurations,self.NumRewardsToEachWell)
        self.TotalRewardDur = np.sum(self.CumulativeRewardDurPerWell)

    # Trial Processing
    def next_trial(self):
        # data storage
        tc = self.TrialCounter
        if tc>0:
            self.Data[tc,0]=self.TrialCounter
            self.Data[tc,1]=self.Act_Cue
            self.Data[tc,2]=self.TrialGoalWell
            self.Data[tc,3]=self.TrialFirstDetectedGoal
            self.Data[tc,4]=self.TrialSecondDetectedGoal
            self.Data[tc,5]=self.TrialDur
            self.Data[tc,6]=self.CorrectTrialFlag
            self.Data[tc,7]=self.SwitchFlag
            self.Data[tc,8]=self.SoftwareErrorFlag

        # updates for next trial
        self.TrialCounter +=1
        if self.Protocol in ['T3c','T3d','T3e','T3f','T3g','T3h','T3i','T3j','T4c','T4d','T5Ra','T5Rb','T5Rc','T5La','T5Lb','T5Lc']:
            rr = random.random()
            if rr < self.SwitchProb: ## switch cue
                if self.Act_Cue==self.ValidCues[0]:
                    self.Queued_Cue = copy.copy(self.ValidCues[1])
                else:
                    self.Queued_Cue = copy.copy(self.ValidCues[0])
            else:
                self.SwitchFlag = False

    def earlyTrials(self):
        if self.TrialCounter<=self.EarlyTrialThr:
            return True
        else:
            return False

    def TrialStart(self):
        self.TrialTime=time.time()
        self.TrialFirstDetectedGoal = -1
        self.TrialSecondDetectedGoal = -1

    def correctTrial(self):
        if not self.IncorrectTrialFlag:
            self.TrialDur = self.TrialTime-time.time()
            self.CorrectTrialFlag = True
            self.NumCorrectTrials += 1
            self.NumConsecutiveCorrectTrials += 1
            if self.SwitchFlag and self.NumConsecutiveCorrectTrials>0:
                self.CorrectAfterSwitch += 1
                self.SwitchFlag= False
                self.Comm.DeliverReward(0)
                self.rewardDelivered1()
                ## self.Comm.DeliverReward(1)
                ## self.rewardDelivered2()

    def incorrectT3(self):
        self.TrialDur = self.TrialTime-time.time()
        self.IncorrectTrialFlag = True
        self.CorrectTrialFlag = False
        self.NumConsecutiveCorrectTrials = 0
        self.IncorrectArm += 1
        print('Incorrect arm. Time-Out')

    def incorrectT4_goal(self):
        self.TrialDur = self.TrialTime-time.time()
        self.CorrectTrialFlag = False
        self.IncorrectTrialFlag = True
        self.NumConsecutiveCorrectTrials = 0
        self.IncorrectGoal += 1

        # if self.TrialCounter >=5 and self.Protocol in ['T4b','T4c']:
        #     self.LED_ON()

    def incorrectT4_arm(self):
        self.TrialDur = self.TrialTime-time.time()
        self.CorrectTrialFlag = False
        self.IncorrectTrialFlag = True
        self.NumConsecutiveCorrectTrials = 0
        self.IncorrectArm += 1
        print('Incorrect arm. Time-Out.')

def MS_Setup(protocol,timeoutdur):
    try:
        conditions = ['G3','G4','G5','G6','G34','G56','G3456']
        states =  [
            State(name='AW0', on_enter=['disable_cue','update_states'], ignore_invalid_triggers=True),
            State(name='AW1',on_enter=['next_trial','update_states','deactivate_cue','enable_cue'],
                  on_exit=['TrialStart','activate_cue'], ignore_invalid_triggers=True),
            State(name='AW2',on_enter=['update_states'],ignore_invalid_triggers=True),
            State(name='AW3',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW4',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW5',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW6',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW34',on_enter='update_states',ignore_invalid_triggers = True),
            State(name='AW56',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW3456',on_enter='update_states',ignore_invalid_triggers=True),
            Timeout(name='TimeOut',on_enter='update_states',ignore_invalid_triggers=True,
                    timeout = timeoutdur, on_timeout = 'start')
            ]

        transitions = [
        # stop trigger
        {'trigger':'stop','source':'*','dest':'AW0'},
        # start striger
        {'trigger':'start','source':'*','dest':'AW1'},
        # valid global transitions
        {'trigger':'D1','source':'AW1','dest':'AW2','before':'rewardDelivered1'},
        {'trigger':'D3','source':['AW3','AW34','AW3456'],'dest':'AW1','before':['correctTrial','rewardDelivered3']},
        {'trigger':'D4','source':['AW4','AW34','AW3456'],'dest':'AW1','before':['correctTrial','rewardDelivered4']},
        {'trigger':'D5','source':['AW5','AW56','AW3456'],'dest':'AW1','before':['correctTrial','rewardDelivered5']},
        {'trigger':'D6','source':['AW6','AW56','AW3456'],'dest':'AW1','before':['correctTrial','rewardDelivered6']},
        # dummy transition
        {'trigger':'D0','source':'*','dest':'='}
        ]

        if not (protocol in ['T2','T3a','T3b','T3c','T3d','T3e','T3f','T3g','T3h','T3i','T3j','T4a','T4b','T4c','T4d','T5Ra','T5Rb','T5Rc','T5La','T5Lb','T5Lc']):
            print('Undefined protocol. Defaulting to T2.')
            protocol = 'T2'

        if protocol=='T2':
            """T2 refers to training regime 2. In this regime the animal can obtain reward at all the goals. Note that there is only one rewarded goal location. """
            transitions = transitions + [
                {'trigger':'D2','source':'AW2','dest':'AW3456', 'conditions':'G3456','after':['deactivate_cue','rewardDelivered2']}]
            ValidCues = []

        elif protocol in ['T3a','T3d']:
            """T3 refers to training regime 3. In this regime the animal can obtain reward at the left or right goals depending on the cue with goal well LED ON.
                On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4.
                Note that there is only one rewarded goal location. """

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':['deactivate_cue','rewardDelivered2']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':['deactivate_cue','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':'AW56','dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D4','source':'AW56','dest':'TimeOut','before':'incorrectT3'},

                {'trigger':'D5','source':'AW34','dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D6','source':'AW34','dest':'TimeOut','before':'incorrectT3'}]
            ValidCues = [5,6]

        elif protocol in ['T3b','T3c']:
            """T3 refers to training regime 3. In this regime the animal can obtain reward at the left \
              or right goals depending on the cue with goal without LEDs on the wells.
              On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4.
              Note that there is only one rewarded goal location. """

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':['deactivate_cue','rewardDelivered2']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':['deactivate_cue','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':'AW56','dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D4','source':'AW56','dest':'TimeOut','before':'incorrectT3'},

                {'trigger':'D5','source':'AW34','dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D6','source':'AW34','dest':'TimeOut','before':'incorrectT3'}]
            ValidCues = [5,6]

        elif protocol in ['T3e']:
            """T3 refers to training regime 3. In this regime the animal can obtain a reward at random left
               or right goals depending on the cue with goal without LEDs on the wells.
               On left trials, the animal can receive reward at either goal well 5 or 6.
               On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','rewardDelivered2']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT3'},

                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT3'}]
            ValidCues = [5,6]

        elif protocol in ['T3f']:
            """T3 refers to training regime 3. In this regime the animal can obtain a reward at random left or right goals
               depending on the cue with goal without LEDs on the wells with the cue staying ON. On left trials, the animal can
               receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one
               rewarded goal location. """

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['rewardDelivered2']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT3','after':'deactivate_cue'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT3','after':'deactivate_cue'},

                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT3','after':'deactivate_cue'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT3','after':'deactivate_cue'}]
            ValidCues = [5,6]

        elif protocol in ['T3g','T3h']:
            """T3g same as f with Cues having different flashing frequencies. Colors stayed the same.
               T3h same as g with LEDs presented on the wells. """

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['rewardDelivered2']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT3','after':'deactivate_cue'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT3','after':'deactivate_cue'},

                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT3','after':'deactivate_cue'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT3','after':'deactivate_cue'}]
            ValidCues = [1,4]

        elif protocol in ['T3i','T3j']:
            """T3i same as g cues go off after well 2.
               T3j same as i, but LEDs on goal wells go ON."""

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','rewardDelivered2']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT3'},

                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT3'}]

            ValidCues = [1,4]

        elif protocol in ['T4a','T4d']:
            """T4 class refers to training regime 4. In this regime the animal can obtain reward at alternating goal
               wells on any arm without LEDs. On left trials, the animal can receive reward at either goal well 5 or 6.
               On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

            transitions = transitions + [
                ## right goals
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','LED_ON','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## left goals
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','LED_ON','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':'AW4','dest':'=','before':'incorrectT4_goal'},
                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT4_arm'},

                {'trigger':'D4','source':'AW3','dest':'=','before':'incorrectT4_goal'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT4_arm'},

                {'trigger':'D5','source':'AW6','dest':'=','before':'incorrectT4_goal'},
                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT4_arm'},

                {'trigger':'D6','source':'AW5','dest':'=','before':'incorrectT4_goal'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT4_arm'},
                ]
            ValidCues = [1,3]

        elif protocol in ['T4b','T4c']:
            """T4 class refers to training regime 4. In this regime the animal can obtain reward at alternating goal wells
               on any arm with LEDs. On left trials, the animal can receive reward at either goal well 5 or 6.
               On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

            transitions = transitions + [

                ## right goals
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','rewardDelivered2']},

                ## left goals
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':'AW4','dest':'=','before':'incorrectT4_goal'},
                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT4_arm'},

                {'trigger':'D4','source':'AW3','dest':'=','before':'incorrectT4_goal'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT4_arm'},

                {'trigger':'D5','source':'AW6','dest':'=','before':'incorrectT4_goal'},
                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT4_arm'},

                {'trigger':'D6','source':'AW5','dest':'=','before':'incorrectT4_goal'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT4_arm'},
                ]

            ValidCues = [1,3]
        elif protocol == 'T5Ra':
            """ T5Ra. Combination of T4 and T3 with lights on the wells. The memory component is on the right arm, with left being foraging."""
            transitions = transitions + [
                ## right  memory
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','LED_ON','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## left foraging w lights on
                {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':'AW4','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D3','source':['AW56'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D4','source':'AW3','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D4','source':['AW56'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT5_arm'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT5_arm'},
            ]
            ValidCues = [1,6]
        elif protocol == 'T5Rb':
            """ T5Rb. Same as TR5a but lights don't turn on the memory wells."""
            transitions = transitions + [
                ## right  memory
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','rewardDelivered2']},

                ## left foraging w lights on
                {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':'AW4','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D3','source':['AW56'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D4','source':'AW3','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D4','source':['AW56'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT5_arm'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT5_arm'},
            ]
            ValidCues = [1,6]
        elif protocol == 'T5Rc':
            """ T5Rc. Same as TR5b but lights don't turn on the foraging wells."""
            transitions = transitions + [
                ## right  memory
                {'trigger':'D2','source':'AW2','dest':'AW3', 'conditions':'G3','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW4', 'conditions':'G4','after':['deactivate_cue','rewardDelivered2']},

                ## left foraging w lights on
                {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':['deactivate_cue','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':'AW4','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D3','source':['AW56'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D4','source':'AW3','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D4','source':['AW56'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D5','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT5_arm'},
                {'trigger':'D6','source':['AW3','AW4'],'dest':'TimeOut','before':'incorrectT5_arm'},
            ]
            ValidCues = [1,6]
        elif protocol == 'T5La':
            """ T5La. Well LEDs On. The memory component is on the LEFT arm, with right being foraging."""
            transitions = transitions + [
                ## left  memory w lights
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','LED_ON','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## right foraging w lights on
                {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D5','source':'AW6','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D5','source':['AW34'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D6','source':'AW5','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D6','source':['AW34'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT5_arm'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT5_arm'},
            ]
            ValidCues = [3,5]
        elif protocol == 'T5Lb':
            """ T5Lb. T5La but no lights on memory wells."""
            transitions = transitions + [
                ## left  memory w lights
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','rewardDelivered2']},

                ## right foraging w lights on
                {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D5','source':'AW6','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D5','source':['AW34'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D6','source':'AW5','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D6','source':['AW34'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT5_arm'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT5_arm'},
            ]
            ValidCues = [3,5]
        elif protocol == 'T5Lc':
            """ T5Lc. T5Lb but no lights on foraging wells."""
            transitions = transitions + [
                ## left  memory w lights
                {'trigger':'D2','source':'AW2','dest':'AW5', 'conditions':'G5','after':['deactivate_cue','rewardDelivered2']},
                {'trigger':'D2','source':'AW2','dest':'AW6', 'conditions':'G6','after':['deactivate_cue','rewardDelivered2']},

                ## right foraging w lights on
                {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D5','source':'AW6','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D5','source':['AW34'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D6','source':'AW5','dest':'=','before':'incorrectT5_goal'},
                {'trigger':'D6','source':['AW34'],'dest':'TimeOut','before':'incorrectT5_arm'},

                {'trigger':'D3','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT5_arm'},
                {'trigger':'D4','source':['AW5','AW6'],'dest':'TimeOut','before':'incorrectT5_arm'},
            ]
            ValidCues = [3,5]
    except:
        print("Error on defining states")
        print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

    return states,transitions, ValidCues
