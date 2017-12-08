
import os, sys, argparse
import serial, datetime, time
from transitions import Machine, State
from transitions.extensions.states import add_state_feature, Timeout
import random, copy
import numpy as np
from collections import Counter

# #gpio.setmode(gpio.BOARD)
# GPIOChans = [33,35,36,37,38,40]
# IRD_GPIOChan_Map = {1:33, 2:35, 3:36, 4:37, 5:38, 6:40}
@add_state_feature(Timeout)
class Machine2(Machine):
    pass

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

def close(MS):
    if MS.datFile:
        if hasattr(MS.datFile,'close'):
            MS.datFile.close()
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
        datFile =[]

    return expt, baud, headFile, datFile, saveFlag

def logEvent(code,MS):
    MS.datFile.write("%s,%f\n" % (code,time.time()-MS.time_ref) )

# function for sending automatic commands to arduino without comand line input.
class ArdComm(object):
    """Spetialized functions for arduino communication."""
    def __init__(self,baud):
        self.ard = serial.Serial('/dev/ttyUSB0',baud,timeout=0.1)
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

class Maze(object):
    def __init__(self, Comm, protocol="null",headFile=[],datFile =[],saveFlag=False):
        try:
            self.Comm = Comm
            self.Protocol = protocol
            self.headFile = headFile
            self.datFile = datFile
            self.saveFlag = saveFlag

            self.PythonControlFlag = False
            self.time_ref = time.time()

            if protocol!="null":
                # Settings
                self.nWells = 6
                self.Wells = np.arange(self.nWells)
                self.GoalWells = [2,3,4,5]
                self.LeftGoals = [4,5]
                self.RightGoals = [2,3]
                self.nCues = 6

                self.Act_Well = np.zeros(self.nWells,dtype=bool)
                self.PrevAct_Well = np.zeros(self.nWells,dtype=bool)
                self.Act_Cue  = 0
                self.Act_Cue_State = False
                self.Queued_Cue = 0
                self.DetectedGoalWell = -1
                self.PrevDetectGoalWell = -1
                self.WellDetectSeq = []
                self.ValidWellDetectSeq = []
                self.SwitchProb = 0.25
                self.TimeOutDuration = 15
                self.SwitchFlag = False

                states,trans, self.ValidCues = MS_Setup(protocol,self.TimeOutDuration)

                # Reward Tracking
                self.DefaultRewardDurations = np.array([8,10,15,15,15,15])
                self.RewardDurations = np.array([8,10,15,15,15,15])
                self.ChangeRewardDur = 5
                self.NumRewardsToEachWell = np.zeros(6)
                self.CumulativeRewardDurPerWell = np.zeros(6)
                self.TotalRewardDur = 0
                self.ChangedRewardFlag = False
                self.ResetRewardFlag = False
                self.ChangedRewardWell = -1
                self.ConsecutiveWellRewardThr = 4

                # Trial Tracking
                self.TrialCounter = 0
                self.CorrectTrialFlag = False
                self.IncorrectTrialFlag = False
                self.NumCorrectTrials = 0
                self.NumConsecutiveCorrectTrials = 0
                self.IncorrectArm = 0
                self.IncorrectGoal = 0
                self.CorrectAfterSwitch = 0
                self.NumSwitchTrials = 0
                self.DetectionTracker = np.zeros(self.nWells)
                self.CorrectWellsTracker = np.zeros(self.nWells)
                self.ConsecutiveCorrectWellTracker = np.zeros(self.nWells)

                StateMachine = Machine2(self,states=states,transitions=trans,
                    ignore_invalid_triggers=True , initial='AW0')

                self.TRIGGER = []
                # dummy first append tr
                self.TRIGGER.append(getattr(self,'D0'))
                for well in (self.Wells+1):
                    self.TRIGGER.append(getattr(self,'D'+str(well)))

                self.PrevDetectedGoalWell = np.random.choice(self.GoalWells)
                self.PrevDetectedRightGoalWell = np.random.choice(self.RightGoals)
                self.PrevDetectedLeftGoalWell = np.random.choice(self.LeftGoals)

        except:
            print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

    ############################################################################
    ############# Main Control Functions #######################################
    def START(self):
        # reset all previous states on Arduino
        self.Comm.Reset()
        time.sleep(0.2)
        self.PythonControlFlag = True
        self.start()

    def STOP(self):
        if self.PythonControlFlag:
            print('Automatic control disabled.')
            print('Total Number of Trials = ', self.TrialCounter)
            print('Total Correct Number of Trials = ', self.NumCorrectTrials)
            print('Total Reward Duration = ', self.TotalRewardDur)
            print('# of Rewards Per Well = ', self.NumRewardsToEachWell)
            self.stop()
            self.Act_Well.fill(False)
            self.Act_Cue_State = False
            self.Act_Cue = 0
            self.printSummary()

        self.PythonControlFlag=False
        self.Comm.Reset()

    def DETECT(self,well):
        #well = event.kwargs.get('well',0)
        try:
            self.WellDetectSeq.append(well)
            well = well-1 # zero indexing the wells
            self.DetectionTracker[well] += 1

            if self.Act_Well[well] == True:
                self.ValidWellDetectSeq.append(well+1)
                self.CorrectWellsTracker[well] += 1
                # Goal Wells
                if well in self.GoalWells:
                    # increase counter for consecuitve correct detections on the same well
                    self.ConsecutiveCorrectWellTracker[well] += 1

                    # update goal detection trackers
                    #print(self.RightGoals)
                    #print(self.ConsecutiveCorrectWellTracker[self.RightGoals])
                    #print(self.LeftGoals)
                    #print(self.ConsecutiveCorrectWellTracker[self.LeftGoals])

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

            self.TRIGGER[well+1]()
        except:
            print("Error on registering the detection")
            print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

    def NEW_TRIAL(self):
        self.CorrectTrialFlag = False
        self.IncorrectTrialFlag = False
        self.NumConsecutiveCorrectTrials = 0
        self.ConsecutiveCorrectWellTracker[self.GoalWells] = 0
        self.ResetRewards()
        self.start()

    def STATUS(self):
        print()
        print('======= State Machine Status =========')
        print('Protocol = ',self.Protocol)
        print('Active Cue = ', self.Act_Cue)
        print('Queued Cue = ', self.Queued_Cue)
        print('Current State = ', self.state)
        print('SM Act. Wells = ', self.Act_Well)
        print('Previous Goal = ', self.PrevDetectedGoalWell)
        print('Trial Number = ', self.TrialCounter)
        print('# of Correct Trials = ', self.NumCorrectTrials)
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

        self.headFile.close()

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

    ############# Well Functions ###############################################
    def activate_well(self,well):
        try:
            if self.Act_Well[well]:
              #print('activated well', well+1)
              self.Comm.ActivateWell(well)
        except:
            print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

    def LED_ON(self):
        for well in self.Wells:
            if self.Act_Well[well]:
                self.Comm.ToggleLED(well)

    def deactivate_well(self,well):
        if not self.Act_Well[well]:
            self.Comm.DeActivateWell(well)

    ############# State Machine Callbacks ######################################
    def update_states(self):
        try:
            time.sleep(0.1)
            if self.is_Timeout() or self.is_AW0():
                state = 0
            else
                state = int(self.state[2:])

            #### trial specific updates (when activating home well)
            if state == 1:
                self.CorrectTrialFlag = False
                self.IncorrectTrialFlag = False

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

            ### activate/deactivate wells based on current state
            self.PrevAct_Well = np.array(self.Act_Well)
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
                else:
                    self.Act_Well[well] = False

            temp = np.logical_and(self.PrevAct_Well==False, self.Act_Well==True)
            wells2activate = self.Wells[temp]
            temp = np.logical_and(self.PrevAct_Well==True, self.Act_Well==False)
            wells2deactivate = self.Wells[temp]
            #print('wells to activate ', wells2activate+1)
            #print('wells to inactivate ', wells2deactivate+1)
            if len(wells2deactivate)>0:
                for well in wells2deactivate:
                    self.deactivate_well(well)
            if len(wells2activate)>0:
                for well in wells2activate:
                    self.activate_well(well)

        except:
            print ('Error updating states')
            print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

    def G3456(self):
        return True

    ## right goals
    def G34(self):
        if self.Protocol[:2] == 'T3':
            if self.Act_Cue==5:
                return True
        return False


    def G3(self):
        if self.Act_Cue==1 or self.Act_Cue==2 or self.Act_Cue==5:
            if self.Protocol[:2] == 'T4':
                if self.PrevDetectedRightGoalWell==3:
                    return True
                else:
                    return False
            else:
                return True
        return False

    def G4(self):
        if self.Act_Cue==1 or self.Act_Cue==2 or self.Act_Cue==5:
            if self.Protocol[:2] == 'T4':
                if self.PrevDetectedRightGoalWell==2:
                    return True
                else:
                    return False
            else:
                return True
        return False

    ## left goals
    def G56(self):
        if self.Protocol[:2] == 'T3':
            if self.Act_Cue==6:
              return True
        return False

    def G5(self):
        if self.Act_Cue==3 or self.Act_Cue==4 or self.Act_Cue==6:
            if self.Protocol[:2] == 'T4':
                if self.PrevDetectedLeftGoalWell==5:
                    return True
                else:
                    return False
            else:
                return True
        return False

    def G6(self):
        if self.Act_Cue==3 or self.Act_Cue==4 or self.Act_Cue==6:
            if self.Protocol[:2] == 'T4':
                if self.PrevDetectedLeftGoalWell==4:
                    return True
                else:
                    return False
            else:
                return True
        return False

    def D0(self):
        pass

    # Reward processing
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

    def updateRewardCount(self):
        self.CumulativeRewardDurPerWell = np.multiply(self.RewardDurations,self.NumRewardsToEachWell)
        self.TotalRewardDur = np.sum(self.CumulativeRewardDurPerWell)

    # Trial Processing
    def next_trial(self):
        self.TrialCounter +=1
        if self.Protocol in ['T3c','T3d','T4c','T4d'] and self.CorrectTrialFlag:
            if random.random() < self.SwitchProb: ## switch cue
                if self.Act_Cue==self.ValidCues[0]:
                    self.Queued_Cue = copy.copy(self.ValidCues[1])
                else:
                    self.Queued_Cue = copy.copy(self.ValidCues[0])
            else:
                self.SwitchFlag = False

    def correctTrial(self):
        if not self.IncorrectTrialFlag:
            self.CorrectTrialFlag = True
            self.NumCorrectTrials += 1
            self.NumConsecutiveCorrectTrials += 1

            if self.SwitchFlag:
                self.CorrectAfterSwitch += 1

    def incorrectT3(self):
        self.IncorrectTrialFlag = True
        self.CorrectTrialFlag = False
        self.NumConsecutiveCorrectTrials = 0
        self.IncorrectArm += 1
        print('Incorrect arm. Time-Out')

    def incorrectT4_goal(self):
        self.CorrectTrialFlag = False
        self.IncorrectTrialFlag = True
        self.NumConsecutiveCorrectTrials = 0
        self.IncorrectGoal += 1

        # reduce reward for correct choice
        well = int(self.state[2:])-1
        if well>=2 and well<=5:
            self.ChangedRewardFlag = True
            self.ChangedRewardWell = copy.copy(well)
            self.Comm.ChangeReward(well,self.ChangeRewardDur)
            self.ResetRewardFlag = True # reset for next trial
            print('Reduced Reward.')

    def incorrectT4_arm(self):
        self.CorrectTrialFlag = False
        self.IncorrectTrialFlag = True
        self.NumConsecutiveCorrectTrials = 0
        self.IncorrectArm += 1
        print('Incorrect arm. Time-Out.')

def MS_Setup(protocol,timeoutdur):
        conditions = ['G3','G4','G5','G6','G34','G56','G3456']
        states =  [
            State(name='AW0', on_enter=['disable_cue','update_states'], ignore_invalid_triggers=True),
            State(name='AW1',on_enter=['next_trial','update_states','LED_ON','deactivate_cue','enable_cue'],on_exit=['activate_cue'], ignore_invalid_triggers=True),
            State(name='AW2',on_enter=['update_states','LED_ON'],ignore_invalid_triggers=True),
            State(name='AW3',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW4',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW5',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW6',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW34',on_enter='update_states',ignore_invalid_triggers = True),
            State(name='AW56',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='AW3456',on_enter='update_states',ignore_invalid_triggers=True),
            State(name='TimeOut',ignore_invalid_triggers=True, 'timeout':timeoutdur, 'on_timeout':'start')
            ]

        transitions = [
        # stop trigger
        {'trigger':'stop','source':'*','dest':'AW0'},
        # start striger
        {'trigger':'start','source':'*','dest':'AW1'},
        # valid global transitions
        {'trigger':'D1','source':'AW1','dest':'AW2','after':'rewardDelivered1'},
        {'trigger':'D3','source':['AW3','AW34','AW3456'],'dest':'AW1','after':['correctTrial','rewardDelivered3']},
        {'trigger':'D4','source':['AW4','AW34','AW3456'],'dest':'AW1','after':['correctTrial','rewardDelivered4']},
        {'trigger':'D5','source':['AW5','AW56','AW3456'],'dest':'AW1','after':['correctTrial','rewardDelivered5']},
        {'trigger':'D6','source':['AW6','AW56','AW3456'],'dest':'AW1','after':['correctTrial','rewardDelivered6']},
        # dummy transition
        {'trigger':'D0','source':'*','dest':'='}
        ]

        if not (protocol in ['T2','T3a','T3b','T3c','T3d','T4a','T4b','T4c','T4d']):
            print('Undefined protocol. Defaulting to T2.')
            protocol = 'T2'


        if protocol=='T2':
            """T2 refers to training regime 2. In this regime the animal can obtain reward at all the goals. Note that there is only one rewarded goal location. """
            transitions = transitions + [
                {'trigger':'D2','source':'AW2','dest':'AW3456', 'conditions':'G3456','after':['deactivate_cue','LED_ON','rewardDelivered2']}]
            ValidCues = []

        elif protocol in ['T3a','T3d']:
            """T3 refers to training regime 3. In this regime the animal can obtain reward at the left or right goals depending on the cue with goal well LED ON. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

            transitions = transitions + [
                ## goals on the right
                {'trigger':'D2','source':'AW2','dest':'AW34', 'conditions':'G34','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## goals on the left
                {'trigger':'D2','source':'AW2','dest':'AW56', 'conditions':'G56','after':['deactivate_cue','LED_ON','rewardDelivered2']},

                ## incorrect choices
                {'trigger':'D3','source':'AW56','dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D4','source':'AW56','dest':'TimeOut','before':'incorrectT3'},

                {'trigger':'D5','source':'AW34','dest':'TimeOut','before':'incorrectT3'},
                {'trigger':'D6','source':'AW34','dest':'TimeOut','before':'incorrectT3'}]
            ValidCues = [5,6]

        elif protocol in ['T3b','T3c']:
            """T3 refers to training regime 3. In this regime the animal can obtain reward at the left or right goals depending on the cue with goal without LEDs on the wells. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

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

        elif protocol in ['T4a','T4d']:
            """T4 class refers to training regime 4. In this regime the animal can obtain reward at alternating goal wells on any arm without LEDs. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

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
            """T4 class refers to training regime 4. In this regime the animal can obtain reward at alternating goal wells on any arm with LEDs. On left trials, the animal can receive reward at either goal well 5 or 6. On right trials, goal 3 or 4. Note that there is only one rewarded goal location. """

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

        return states,transitions, ValidCues
