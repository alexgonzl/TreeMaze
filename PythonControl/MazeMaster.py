#!/usr/bin/python3

###
#  Master controller for the TreeMaze. It communicates with the arduino through serial port.
#  Receives data through GPIO inputs and serial.
###

import threading
from MazeHeader import *
PythonControlSet = ['T2','T3a','T3b','T3c','T4d','T4a','T4b','T4c','T4d']

# Main Threads:
def readArduino(arduinoEv, interruptEv):
    global MS
    while True:
        if not interruptEv.is_set():
            # reduce cpu load by reading arduino slower
            time.sleep(0.001)
            data = MS.Comm.ReadLine()
            try:
                if data:
                    try:
                        if isinstance(data,bytes):
                            x = data.decode('utf-8')
                            if (x[0]=='<'):
                                if (x[1:4]=="EC_"):
                                    try:
                                        code = x[4:]
                                        if MS.PythonControlFlag and code[0:2]=="DE":
                                            detectNum = int(code[2])
                                            MS.DETECT(detectNum)
                                            print (code)
                                        if MS.saveFlag:
                                            logEvent(code,MS)
                                    except:
                                        print ("error", sys.exc_info()[0])
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
                                pass
                                #print (data)
                    except:
                        #print ("error", sys.exc_info()[0])
                        pass
            except:
                #print ("error", sys.exc_info()[0])
                pass
        else:
            break

def getCmdLineInput(arduinoEv,interruptEv):
    global MS
    ArdWellInstSet = ['w','d','p','l','z'] # instructions for individual well control
    ArdGlobalInstSet = ['a','s','r','y'] # instructions for global changes

    time.sleep(1)
    while True:
        if not interruptEv.is_set():
            # wait 1 second for arduino information to come in
            arduinoEv.wait(0.5)
            try:
                print()
                print ("Enter 'Auto', to start automatic goal sequencing.")
                print ("Enter 'C#', to queue a cue for the next trial.")
                print ("Enter 'S', to check state machine status")
                print ("Enter 'N', to start a new trial.")
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
                CL_in = input()
                if (isinstance(CL_in,str) and len(CL_in)>0):
                    # Automation
                    if (CL_in=='Auto'):
                        if not MS.PythonControlFlag:
                            try:
                                while True:
                                    print('')
                                    if MS.Protocol[:2] == 'T3':
                                        cueinput = int(input('Enter cue to enable [5,6]: '))
                                        if cueinput in [5,6]:
                                            MS.Act_Cue = cueinput
                                            break
                                        else:
                                            print("Invalid Cue")
                                    elif MS.Protocol[:2] == 'T4':
                                        cueinput = int(input('Enter cue to enable [1,3]: '))
                                        if cueinput in [1,3]:
                                            MS.Act_Cue = cueinput
                                            break
                                        else:
                                            print("Invalid Cue")
                                    elif MS.Protocol == 'T2':
                                       cueinput = 0
                                       break

                                    if cueinput>=1 and cueinput<=9:
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
                        elif (CL_in=='N'):
                            print("Starting a new trial.")
                            MS.NEW_TRIAL()
                        elif (CL_in=='Stop'):
                            MS.STOP()

                    # individual instructions
                    ins = CL_in[0]
                    # quit instruction
                    if (ins == 'q'):
                        print('Terminating Arduino Communication')
                        MS.STOP()
                        close(MS)
                        interruptEv.set()
                        break

                    # global instructions: a,s,r,y
                    elif ins in ArdGlobalInstSet:
                        MS.Comm.SendChar(ins)

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
            arduinoEv.clear()
        else:
            break

# Parse Input:
expt, baud, headFile, datFile, saveFlag = ParseArguments()
# Set serial comm with arduino
Comm = ArdComm(baud)

# Creat Maze object
if expt in PythonControlSet:
    MS = Maze(Comm,protocol=expt,datFile=datFile,headFile=headFile,saveFlag=saveFlag)
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
    close(MS)
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    quit()

except:
    print ("error", sys.exc_info()[0])
    close(MS)
    interruptEv.set()
    readArdThr.join()
    cmdLine.join()
    quit()
