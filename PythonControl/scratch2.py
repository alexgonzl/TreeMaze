from MazeHeader_PyCMD import ArdComm
import time
Comm = ArdComm(115200,verbose=True)
Comm.ReceiveData()
Comm.ActivateAllWells()
Comm.ReceiveData()
Comm.Reset()
Comm.ReceiveData()
# for ii in [0,1,2,3,4,5]:
#     if 0:
#         Comm.ActivateWell(ii)
#         x=Comm.ReceiveData()
#         print(x)
#         time.sleep(0.1)
#
#         Comm.DeActivateWell(ii)
#         x=Comm.ReceiveData()
#         print(x)
#         time.sleep(0.1)
#
#         Comm.ToggleLED(ii)
#         Comm.ReceiveData()
#         time.sleep(0.1)
#         Comm.ToggleLED(ii)
#         Comm.ReceiveData()
#         time.sleep(0.1)
#
#         Comm.LED_ON(ii)
#         Comm.ReceiveData()
#         time.sleep(0.1)
#         Comm.LED_OFF(ii)
#         Comm.ReceiveData()
#         time.sleep(0.1)

    # Comm.DeliverReward(ii)
    # print(Comm.ReceiveData())
    # Comm.DeliverSpecifiedReward(ii,40*ii+10)
    # time.sleep(0.12)
    # print(Comm.ReceiveData())

    # Comm.ChangeReward(ii,10+ii)
    # Comm.ReceiveData()

Comm.getArdStatus()
Comm.ReceiveData()
Comm.GetStateVec()

x,y=Comm.ReceiveData()
print(x,y)
Comm.ActivateAllWells()
Comm.GetStateVec()
x,y=Comm.ReceiveData()

cnt = 0
print(x,y)
for xx in x:
    if xx == '2':
        print(xx,y[cnt][0:2],y[cnt][2])
    elif xx== '4':
        print(xx,y[cnt])
    cnt +=1
Comm.close()

quit()
# temp = 'NONE'
# while temp != 'NONE':
#     temp = Comm.ReceiveData()
#
# Comm.getArdStatus()
# while temp != 'NONE':
#     temp = Comm.ReceiveData()
