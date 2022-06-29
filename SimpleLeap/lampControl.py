import sys
import socket
import os
import lampconfig # berrytwitter contains class with Twitter credentials:
#class LampConfiguration():
#    IP =''
#    Port =''

config = lampconfig.LampConfiguration()

UDP_IP = config.ip
UDP_PORT = config.port

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))

LIRCCMD = "irsend SEND_ONCE lamp "
COMMANDS = ['ON','OFF','BPLUS','BMINUS','B30','B60','B80','TPLUS','TMINUS','T3200','T4400','T5600']

while True:
    data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
    info = data.decode()
    print("received message: %s" % data)
    if info in COMMANDS:
        cmd = LIRCCMD  +info
        print(cmd)
        os.system(cmd)
