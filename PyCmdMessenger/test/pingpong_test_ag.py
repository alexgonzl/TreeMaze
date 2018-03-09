#!/usr/bin/env python3
import PyCmdMessenger
import time, string, sys, struct, random

BAUD_RATE = 115200

TYPE_LIST = ["kBool",
             "kInt16",
             "kChar",
             "kString",
             "kString2",]

class ArdCom2(object):
    COMMANDS = [["kAcknowledge","s"],
                ["kError","s"],
                ["kAreYouReady","s"],
                ["kYouAreReady","s"],
                ["kValuePing","gg"],
                ["kValuePong","g"],
                ["kValuePong2",""]]

    def __init__(self,port="\dev\ttyUSB0",baud=115200):
        try:
            self.ard = PyCmdMessenger.ArduinoBoard(port,baud_rate=baud,timeout=0.1)
        except:
            print("Couldn't connect to arduino board.")
            print( sys.exc_info())

        self.con = PyCmdMessenger.CmdMessenger(board_instance= self.ard, commands= self.COMMANDS, warnings= False)
        # Check connection
        self.con.send("kAreYouReady")
        # Clear welcome message etc. from buffer
        i = 0
        success = False
        while i < 3:
            value = self.con.receive()
            time.sleep(0.15)
            if value != None:
                success = True
            i += 1

        # Make sure we're connected
        if not success:
            err = "Could not connect."
            raise Exception(err)
    def SendNum(self,num):
        if (isinstance(num,int)):
            try:
                self.con.send("kValuePing",1,num, arg_formats="gs")
            except:
                print("Could not send the number")
        else:
            print("Tried to send an int, but input is not a int.")

    def SendChar(self,ch):
        if (isinstance(ch,str)):
            try:
                self.con.send("kValuePing",2,ch, arg_formats="gc")
            except:
                print("Could not send the char")
        else:
            print("Tried to send a char, but input is not a char.")
    def SendString(self,chs):
        if (isinstance(chs,str)):
            try:
                self.con.send("kValuePing",4,chs, arg_formats="gs")
            except:
                print("Could not send the char")
        else:
            print("Tried to send a char, but input is not a char.")

    def Receive(self,typeSingleIn=True):
        try:
            if typeSingleIn:
                x = self.con.receive()
                if x[0]=='kValuePong':
                    print (x[1])
                return ""
            else:
                x = self.con.receive()
                if x[0]=='kValuePong2':
                    x = self.con.receive(arg_formats="s*")
                    for chs in x[1] :
                        print (chs)
                    return ""
        except:
            print ("Error receiving data.")
            print( sys.exc_info())
