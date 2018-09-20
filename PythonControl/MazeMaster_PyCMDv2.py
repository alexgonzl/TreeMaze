#!/usr/bin/python3

###
#  Master controller for the TreeMaze. It communicates with the arduino through serial port.
#  Receives data through GPIO inputs and serial.
###

import threading
from MazeHeader_PyCMDv2 import *
PythonControlSet = ['T2','T3a','T3b','T3c','T3d','T3e','T3f','T3g','T3h','T3i','T3j',
                    'T4a','T4b','T4c','T4d', 'T5Ra','T5Rb','T5Rc','T5La','T5Lb','T5Lc']

# Main Threads:
def readArduino(arduinoEv, interruptEv):
    global MS
    time.sleep(2)
    while True:
        if not interruptEv.is_set():
            # reduce cpu load by reading arduino slower
            time.sleep(0.01)
            try:
                if MS.PythonControlFlag:
                    if MS.IncongruencyFlag and (time.time()-MS.IncongruencyTimer)>1:
                        MS.Comm.GetStateVec()
                    if MS.CueTimerFlag:
                        if MS.CueTimer>0 and (time.time()-MS.CueTimer>MS.CueDeactivateTime):
                            MS.deactivate_cue()
                            MS.CueTimerFlag=False
                            MS.CueTimer=-1
                    
                ardsigs,data = MS.Comm.ReceiveData()
                cnt = -1
                for sig in ardsigs:
                    cnt +=1
                    if sig>0:
                        if MS.PythonControlFlag:
                            if sig==2:
                                try:
                                    if data[cnt][0:2]=="DE":
                                        wellnum = int(data[cnt][2])
                                        MS.Ard_Act_Well_State[wellnum-1]=False
                                        if MS.PythonControlFlag:
                                            MS.DETECT(wellnum)
                                            print("Detection on Well #", wellnum)

                                    elif data[cnt][0:2]=="AW":
                                        wellnum = int(data[cnt][2])-1
                                        MS.Ard_Act_Well_State[wellnum]=True
                                        print("Activated Well #", wellnum+1)

                                        if MS.Act_Well[wellnum]==False:
                                            print('wrong activation')
                                            MS.InconguencyFlag=True
                                            MS.IncongruencyTimer=time.time()

                                    elif data[cnt][0:2]=="DW":
                                        wellnum = int(data[cnt][2])-1
                                        MS.Ard_Act_Well_State[wellnum]=False
                                        MS.Ard_LED_State[wellnum]=False
                                        print("Deactivated Well #", wellnum+1)
                                        if MS.Act_Well[wellnum]==True:
                                            MS.InconguencyFlag=True
                                            MS.IncongruencyTimer=time.time()

                                    elif data[cnt][0:2]=="AL":
                                        wellnum = int(data[cnt][2])-1
                                        MS.Ard_LED_State[wellnum]=True
                                        print("LED ON Well #", wellnum+1)
                                        if MS.LED_State[wellnum]==False:
                                            print('wrong led activation')
                                            MS.InconguencyFlag=True
                                            MS.IncongruencyTimer=time.time()

                                    elif data[cnt][0:2]=="DL":
                                        wellnum = int(data[cnt][2])-1
                                        MS.Ard_LED_State[wellnum]=False
                                        if MS.LED_State[wellnum]==True:
                                            MS.InconguencyFlag=True
                                            MS.IncongruencyTimer=time.time()
                                        print("LED OFF Well #", wellnum+1)
                                    elif data[cnt][0:2]=="RE":
                                        print("Reward Delivered to ", wellnum+1)

                                    if MS.saveFlag:
                                        logEvent(data[cnt],MS)
                                except:
                                    print("Error Processing Arduino Event.", sys.exc_info())

                            elif sig == 4:
                                try:
                                    #print("Updating arduino states.")
                                    MS.UpdateArdStates(data[cnt])
                                    #print(data[cnt])
                                    MS.InnerStateCheck(int(data[cnt][0]))
                                except:
                                    print("Error updating states",sys.exc_info())
                        else:
                            if MS.Comm.verbose:# no python control
                                print('e',ardsigs,data)
            
            except: # try to read data
                print ("Error Processing Incoming Data", sys.exc_info())
        else: # if there is an interrupt
            break


def PrintInstructions():
    print()
    print ("Enter 'Auto', to start automatic goal sequencing.")
    print ("Enter 'C#', to queue a cue for the next trial.")
    print ("Enter 'S', to check state machine status")
    print ("Enter 'N', to start a new trial.")
    print ("Enter 'M#', to manually detect a well.")
    print ("Enter 'P%', to change switch probability.")
    print ("Enter 'Stop', to stop automation of well sequencing.")
    print("------------------------------------------------------")
    print ("Enter 'a','r' activate / reset all")
    print ("Enter 's' to check status")
    print ("Enter 'w#','d#', to activate/deactivate a well (e.g 'w1')")
    print ("Enter 'p#', to turn on pump (e.g 'p3') ")
    print ("Enter 'l#', to toggle LED (e.g 'l1') ")
    print ("Enter 'z#=dur' to change pump duration ('z4=20') ")
    print ("Enter 'c#','y' to turn on/off cues ('c1')")
    print ("Enter 'q' to exit")

def getCmdLineInput(arduinoEv,interruptEv):
    global MS
    ArdWellInstSet = ['w','d','p','l','z'] # instructions for individual well control
    ArdGlobalInstSet = ['a','s','r','y'] # instructions for global changes

    time.sleep(1)
    while True:
        if not interruptEv.is_set():
            # wait 1 second for arduino information to come in
            #arduinoEv.wait(0.2)
            try:
                print('To print available commands press ?')
                CL_in = input()
                if CL_in == '?':
                    PrintInstructions()
                    CL_in = input()
                else:
                    pass

                if (isinstance(CL_in,str) and len(CL_in)>0):
                    # Automation
                    if (CL_in=='Auto'):
                        if not MS.PythonControlFlag:
                            try:
                                while True:
                                    print('')
                                    if MS.Protocol[:3] in ['T3a','T3b']:
                                        cueinput = int(input('Enter cue to enable [5,6]: '))
                                        if cueinput in [5,6]:
                                            MS.Act_Cue = cueinput
                                            break
                                        else:
                                            print("Invalid Cue")
                                    elif MS.Protocol[:3] == ['T4a','T4b']:
                                        cueinput = int(input('Enter cue to enable [1,3]: '))
                                        if cueinput in [1,3]:
                                            MS.Act_Cue = cueinput
                                            break
                                        else:
                                            print("Invalid Cue")
                                    else:
                                       cueinput = 0
                                       break

                                if cueinput>=0 and cueinput<=9:
                                    MS.Act_Cue = cueinput
                                MS.START()
                            except:
                                print('Unable to start automation. Talk to Alex about it.')
                                print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)
                                MS.STOP()

                    # Automation Specific Commands
                    if MS.PythonControlFlag:
                        if (CL_in[0]=='C'):
                            MS.Queued_Cue = int(CL_in[1])
                            print("Cue queued for the next trial.")
                        elif (CL_in=='S'):
                            print("Auto Control Enabled = ", MS.PythonControlFlag)
                            MS.STATUS()
                            print("Arduino Variables Status")
                            print(MS.Ard_Act_Well_State)
                        elif (CL_in=='N'):
                            print("Starting a new trial.")
                            MS.NEW_TRIAL()
                        elif (CL_in[0]=='M'):
                            w = int(CL_in[1])
                            if w>=1 and w<=6:
                                MS.DETECT(w)
                        elif (CL_in[0]=='P'):
                            pr = int(CL_in[1:])
                            if pr>=0 and pr<=100:
                                MS.SwitchProb = float(pr)/100.0
                        elif (CL_in=='Stop'):
                            MS.STOP()

                    # individual instructions
                    ins = CL_in[0]
                    # quit instruction
                    if (ins == 'q'):
                        print('Terminating Arduino Communication')
                        MS.STOP()
                        interruptEv.set()
                        time.sleep(0.2)
                        close(MS)
                        break

                    # global instructions: a,s,r,y
                    elif ins in ArdGlobalInstSet:
                        if ins == 'a':
                            MS.Comm.ActivateAllWells()
                        elif ins == 's':
                            MS.Comm.getArdStatus()
                        elif ins == 'r':
                            MS.Comm.Reset()
                        elif ins == 'y':
                            MS.Comm.DeActivateCue()

                    # actions on individual wells
                    elif ins in ArdWellInstSet:
                        try:
                            well = int(CL_in[1])-1 # zero indexing the wells
                            if well>=0 and well <=5:
                                if ins=='w' and not MS.PythonControlFlag :
                                    MS.Comm.ActivateWell(well)
                                elif ins=='d' and not MS.PythonControlFlag :
                                    MS.Comm.DeActivateWell(well)
                                elif ins=='p':
                                    MS.Comm.DeliverReward(well)
                                    if MS.PythonControlFlag:
                                        MS.rewardDelivered(well)

                                elif ins=='l':
                                    MS.Comm.ToggleLED(well)
                                elif ins=='z':
                                    try:
                                        dur = int(CL_in[3:])
                                        if dur>0 and dur<=1000:
                                            MS.Comm.ChangeReward(well,dur)
                                    except:
                                        print('Invalid duration for reward.')
                        except:
                            print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)
                            print('Incorrect Instruction Format, Try again')
                            pass

                    # cue control
                    elif ins=='c' and not MS.PythonControlFlag :
                        try:
                            cuenum = int(CL_in[1])
                            if cuenum>=1 & cuenum<=6:
                                MS.Comm.ActivateCue(cuenum)
                            else:
                                print('Invalid Cue Number')
                        except:
                            print('Invalid Cue Number')
                            pass
            except:
                print ("error", sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)
            #arduinoEv.clear()
        else:
            break

# Parse Input:
expt, baud, verbose, headFile, datFile, saveFlag, npyfile = ParseArguments()
# Set serial comm with arduino
Comm = ArdComm(baud,verbose=verbose)

# Creat Maze object
if expt in PythonControlSet:
    MS = Maze(Comm,protocol=expt,datFile=datFile,headFile=headFile,npyFile=npyfile,saveFlag=saveFlag)
else:
    MS = Maze(Comm)

# leave some time
time.sleep(0.2)

# Main
arduinoEv = threading.Event()
interruptEv = threading.Event()

# Declare threads
readArdThr = threading.Thread(target = readArduino, args = (arduinoEv, interruptEv))
cmdLine = threading.Thread(target = getCmdLineInput, args = (arduinoEv,interruptEv))

try:
    # Start threads
    readArdThr.start()
    cmdLine.start()

except KeyboardInterrupt:
    print ("Keyboard Interrupt. Arduino Comm closed.")
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    close(MS)
    quit()

except:
    print ("error", sys.exc_info()[0])
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    close(MS)
    quit()
