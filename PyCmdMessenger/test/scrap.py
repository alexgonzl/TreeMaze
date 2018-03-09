import pingpong_test_ag as p
import numpy as n

c = p.ArdCom2(port="\\.\COM3")

c.SendChar('a')
c.Receive()
c.SendNum(13242)
c.Receive()
c.SendString('asdqwugdqwufgdwqda')
c.Receive(typeSingleIn=False)

def SC(x):
    c.SendChar(x)
    y = c.Receive()
    return y[1]==x
    #print(c.Receive())

def SBC(x):
    c.SendBChar(x)
    y = c.Receive()
    return y[1]==x

def SN(x):
    c.SendNum(x)
    y = c.Receive()
    return y[1]==x
    #print(c.Receive())

def SBN(x):
    c.SendBNum(x)
    y = c.Receive()
    return y[1]==x


# if __name__ == '__main__':
#     import timeit
#     x = timeit.repeat("SC('a')",repeat=100,number=1,setup="from __main__ import SC")
#     print (n.average(x))
#     x = timeit.repeat("SBC('a')",repeat=100,number=1,setup="from __main__ import SBC")
#     print(n.average(x))
#     x = timeit.repeat("SN(123)",repeat=100,number=1,setup="from __main__ import SN")
#     print (n.average(x))
#     x = timeit.repeat("SBN(321)",repeat=100,number=1,setup="from __main__ import SBN")
#     print(n.average(x))
