from concurrent.futures import process
import matplotlib
import socket
import datetime
import select
import random
import time
import matplotlib.pyplot as plt
import matplotlib.image as mpimage
from matplotlib.artist import Artist
from PIL import Image, ImageOps
import numpy as np
import threading
import queue
import qrcode
import ppa6
import twitter
from google.cloud import storage
import serial
import requests
from pynput import keyboard
import io
import brother_ql
from brother_ql.raster import BrotherQLRaster
from brother_ql.backends.helpers import send
import logging
import berrytwitter # berrytwitter contains class with Twitter credentials:
#class TwitterConfiguration():
#    consumer_key=''
#    consumer_secret=''
#    access_token_key=''
#    access_token_secret=''

from scipy.interpolate import interp1d
from matplotlib.offsetbox import TextArea, DrawingArea, OffsetImage, AnnotationBbox

import os
# Set on Raspberry or Linux
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="/home/pi/Desktop/BerryMetrePythonReceiver/freitaglab.json"

# logging.basicConfig(level=logging.DEBUG)

# Change directory to script directory
os.chdir(os.path.dirname(os.path.realpath(__file__)))

# ToDo:
# - Remove interpolation line?
# - Keyboard interaction for output (Twitter, Print, etc)
# - Fix serial in multithreaded application
# - Make configuration and code more modular
# - Autoscale axis, or at least some calibration step for scaling

# mode is either 'serial' or 'udp'
mode = 'udp'
fullscreen = True
printrendertime = False
printSticker = False
uploadToGoogle = False
tweetResult = False
# printIVcurve = False
USEMOVINGAVERAGE = False
MAVALUES = 3                # How many values to consider for moving average
UDPTIMEOUT = 10.0          # 0.5 for silicon cell, 2 for dye cell, depends on dwell time
SERIALTIMEOUT = 0.5
UDPBUFFERSIZE = 256
currentCell = 1
forwardUdp = True
scaleWidth = 576          # scalewidth for print 576 for PeriPage, 696 for QL-810W
printerType = 'brother'        # peripage or brother

# TODO: Rename variables for proper order!
if printerType == 'brother':
    scaleWidth = 732
    # Read other logos, no need to resize
    summerScienceLogo = Image.open('res/NewcastleUniversityLogoBR732.png')
    berrySolarLogo = Image.open('res/BerrySolarLogo732.png')
    nclBottomLogo = Image.open('res/150YearsSageLogo732.png')
    qrberry = Image.open('res/qrberryred.png')

if printerType == 'peripage':
    scaleWidth = 576
    # Read other logos, no need to resize
    summerScienceLogo = Image.open('res/SummerScienceLogo576.png')
    berrySolarLogo = Image.open('res/BerrySolarLogo576.png')
    nclBottomLogo = Image.open('res/NCLRoyalSocietyBottomLogo576.png')
    qrberry = Image.open('res/qrberryblack.png')


# Compensate for lower AREF from low voltage power supply
VIN = 4.9
AREF = 4.0
AREFFACTOR = VIN/AREF

SAVETIME = 5            # Seconds after which to save figure
FONTSIZE = 36

printerMac = '20:20:08:1b:3a:1a'    # PeriPage
PRINTER_IDENTIFIER = 'tcp://192.168.1.176' # Brother Network Print

def sendToBrotherPrinter(path):
    brotherprinter = BrotherQLRaster('QL-810W')
    filename = path
    print_data = brother_ql.brother_ql_create.convert(brotherprinter, [filename], '62red', dither=True, red=True, rotate=90)
    print("Brother printing...")
    send(print_data, PRINTER_IDENTIFIER)

gridcolor = 'green'
powerlinecolor = '#7a04eb' #blue
powerpointcolor = '#7a04eb'
mppcolor = '#7a04eb'

currentlinecolor = '#ebb104'
currentpointcolor = '#ebb104'
powerfillcolor = '#ebb104'

INTERPOLATIONTYPE = "linear"

# zero value compensation
RCOMP = 50

# res = [89.8+RCOMP,117.4,258.8,324.6,443.1,594.5,678.3,758.5,802,817.1,880.1,990,1128.9,1294.5,1488,2154,2892.0,3244,3978.7,4677,5258.1,5502,21760.3,26650,118600,100000000]
res = [91.3+RCOMP,120,262.4,330.2,448.5,589.1,682.9,764.4,820,823.9,884.2,1000.0,1135.7,1310.9,1500,2200,2696.5,3000,3995.4,4700,5256.2,5000,18557.6,22000,82000,100000000]

msr = 26 # number of measurements
# Silicon Cell
# MAGICVA = 1/30
# RSERIES = 0

# High End Dye Cell
MAGICVA = 0
RSERIES = 0

nullinfo = ""
for i in range(msr+1):
    nullinfo = nullinfo+"0,"
nullinfo = nullinfo[:-1]

# Scale power axis on right
POWERSCALE = 0.5

xmax = 2.5
ymax = 2.0

# xmax = 0.5
# ymax = 0.5


COMPORT = 'COM5'
UDP_IP = "192.168.15.2"  # Local IP
UDP_FIP = "192.168.15.9" # Forward IP
UDP_PORT = 6819
prevCount = 0

saveImageNow = False
tweetImageNow = False
processNewPackage = False
processSocialAction = False
printQueue = queue.Queue()

# drawPowerArea = False

def moving_average(x, w):
    return np.convolve(x, np.ones(w), 'valid') / w

# concatenate images
def get_concat_v(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (0, im1.height))
    return dst

def get_concat_h(im1, im2):
    dst = Image.new('RGB', (im1.width + im2.width, im1.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (im1.width, 0))
    return dst

# c = threading.Condition()

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    # print(
    #     "File {} uploaded to {}.".format(
    #         source_file_name, destination_blob_name
    #     )
    # )

class ProcessSerial(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global info
        global stimeout

        arduino = serial.Serial(COMPORT, 115200, timeout=SERIALTIMEOUT)
        print(arduino.name)

        # global flag
        # global val     #made global here
        while True:
            try:
                line = arduino.readline()
                info = line.decode()
                stimeout = False
            except:
                info = nullinfo
                # print("Socket timeout")
                stimeout = True
            # print("Info: ", info)

def SocialActionFunction(fileTimeStamp, cellNumber):
    print("Process social actions: " + fileTimeStamp + ", cell number: " + str(cellNumber))

    imagePngOut = "out/mycell-" + fileTimeStamp + ".png"
    imagePngFileName = "mycell-" + fileTimeStamp + ".png"

    stickerFileOut = "out/mycell-" + fileTimeStamp + "-sticker.png"
    stickerFileName = "mycell-" + fileTimeStamp + "-sticker.png"

    qrFileOut = "out/mycell-" + fileTimeStamp + "-qr.png"
    qrFileName = "mycell-" + fileTimeStamp + "-qr.png"

    htmlFileOut = "out/mycell-" + fileTimeStamp + ".html"
    htmlFileName = "mycell-" + fileTimeStamp + ".html"

    if tweetResult == True:
        print('Tweet the result!')
        media_id = twitterApi.UploadMediaSimple(imagePngOut)
        status = twitterApi.PostUpdate(status='We love dye cells!', media=media_id)
        qrString = status.media[0].url
        print(qrString)
        print(status.text)
    if uploadToGoogle == True and tweetResult == False:
        print('Point QR code to google, not tweet!')
        qrString = 'www.berrycells.com/' + htmlFileName
        print(qrString)
    if uploadToGoogle == False and tweetResult == False:
        print('Point QR Code to freitaglab.com!')
        qrString = 'https://www.freitaglab.com'

    print(qrberry.size)
    qr_big = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    qr_big.add_data(qrString)
    qr_big.make()
    img_qr_big = qr_big.make_image().convert('RGB')

    pos = ((img_qr_big.size[0] - qrberry.size[0]) // 2, (img_qr_big.size[1] - qrberry.size[1]) // 2)

    img_qr_big.paste(qrberry, pos)
    img_qr_big = img_qr_big.resize((scaleWidth,scaleWidth))
    img_qr_big.save(qrFileOut)


    # Concatenate what we just created in right order

    final = get_concat_v(berrySolarLogo, img_qr_big)
    final = get_concat_v(final, summerScienceLogo)
    # final = get_concat_v(final, berrySolarLogo)
    # if printIVcurve == True:
    #     final = get_concat_v(final, im_res)
    final = get_concat_v(final, nclBottomLogo)

    # black border around image
    final = ImageOps.expand(final,border=24,fill='black')

    # Resize again. Can be avoided by making the template images 2*border pixels smaller
    # Scale figure
    newheight = int(final.size[1]/(final.size[0]/scaleWidth))
    final = final.resize((scaleWidth,newheight))

    final.save(stickerFileOut)
    # print("Saving figure...")

    with open ("res/mycelltemplate.html", "r") as myfile:
        data=myfile.read()
        data = data.replace("$IMAGE$",imagePngFileName)
        htmlOut = open(htmlFileOut, "w")
        n = htmlOut.write(data)
        htmlOut.close()
        print("Saved html file!")


    if uploadToGoogle == True:
        upload_blob("www.berrycells.com", imagePngOut, imagePngFileName)
        upload_blob("www.berrycells.com", htmlFileOut, htmlFileName)
        upload_blob("www.berrycells.com", stickerFileOut, stickerFileName)

    if printSticker == True:
        printQueue.put((stickerFileOut, cellNumber))
        # printer = ppa6.Printer(printerMac, ppa6.PrinterType.A6p)
        # printer.connect()
        # printer.reset()
        # printer.setConcentration(2)
        # printer.printBreak(25)
        # printer.printImage(final)
        # printer.printBreak(25)
        # printer.disconnect()
    else:
        final.show()


# class ProcessSocialAction(threading.Thread):
#     def __init__(self, name):
#         threading.Thread.__init__(self)
#         self.name = name

#     def run(self):
#         global processSocialAction

#         # global flag
#         # global val     #made global here
#         while True:
#             # print("Process print job")
#             if processSocialAction == True:
#                 print("Process social action now")
#                 processSocialAction = False



class ProcessUDP(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        global info
        global stimeout
        # global acquisitionstarttime
        # packageReceived = False
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(0)
        sock.settimeout(UDPTIMEOUT)
        sock.bind((UDP_IP, UDP_PORT))

        sockf = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        MESSAGE = b"Hello from receiver!"
        sockf.sendto(MESSAGE, (UDP_FIP, UDP_PORT))

        # global flag
        # global val     #made global here
        while True:
            try:
                # print("Try...")
                data, addr = sock.recvfrom(UDPBUFFERSIZE)
                info = data.decode()
                stimeout = False
                
                # Forward UDP
                if forwardUdp == True:
                    sockf.sendto(data, (UDP_FIP, UDP_PORT))

                # if packageReceived == False:
                #     acquisitionstarttime = datetime.datetime.now()
                #     packageReceived = True
                if info != nullinfo and info.count(',') != msr and info != "":
                    print("Udp Info: ", info)
                # print("Thread data: ", info, " ", datetime.datetime.now())
                # print("Try done...")
            except:
                info = nullinfo
                # print("Socket timeout")
                stimeout = True

def on_press(key):
    global saveImageNow
    global tweetImageNow
    global toggleFullscreen
    # global drawPowerArea
    try:
        # print('Alphanumeric key pressed: {0} '.format(
        #     key.char))
        if key.char == 'n':
            print("Prepare for new save!")
            # drawPowerArea = not drawPowerArea
        if key.char == 's':
            print("Save image!")
            saveImageNow = True
        if key.char == 'p':
            print("Print sticker!")
        if key.char == 't':
            print("Tweet the image!")
        if key.char == 'g':
            print("Upload image to google!")
    except:
        nothing = 0
        # print('special key pressed: {0}'.format(
        #     key))

class ProcessKeyboard(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
    def run(self):
        # Collect events until released
        with keyboard.Listener(
                on_press=on_press) as listener:
            listener.join()

starttime = datetime.datetime.now()
endtime = datetime.datetime.now()
runtime = endtime - starttime

info = nullinfo

# plt.ion()
plt.style.use('dark_background')
logo = mpimage.imread('res\\ncl3.png')

imagebox = OffsetImage(logo, zoom=1.5)

fig, (ax, axQ) = plt.subplots(2, gridspec_kw={'height_ratios': [8, 1]})

plt.xticks(fontsize=FONTSIZE)
plt.yticks(fontsize=FONTSIZE)


fig.canvas.toolbar.pack_forget()

if fullscreen == True:
    manager = plt.get_current_fig_manager()
    manager.full_screen_toggle()

x = [0] * msr
py = [0] * msr
iy = [0] * msr

voltage = [0] * msr
current = [0] * msr
power = [0] * msr

ax.set_xlim([0, xmax])
ax.set_ylim([0, ymax])

axQ.set_xlim([0, 1])
axQ.set_ylim([0, 1])

lw = 5.0

for axis in ['top','bottom','left','right']:
    ax.spines[axis].set_linewidth(4)

# ax.spines['left'].set_color(powerlinecolor)

c = 10
r = msr
xm = [ [0.001] * c for i in range(r) ]
pym = [ [0.001] * c for i in range(r) ]
iym = [ [0.001] * c for i in range(r) ]

powerline, = ax.plot(x,py, animated=True, color =  powerlinecolor)
powermeasure, = ax.plot(x,py, marker = 'o', animated=True, color = powerpointcolor, markerfacecolor='none', linewidth=lw, markersize=(lw*2))

currentline, = ax.plot(x,iy, animated=True, color = currentlinecolor)
currentmeasure, = ax.plot(x,iy, marker = 's', animated=True, color = currentpointcolor, markerfacecolor='none', linewidth=lw, markersize=(lw*2) )
mpp, = ax.plot(1,1, color= mppcolor, marker='o', animated = True)

filler = ax.fill_between(x, py, color = 'black')

maxPowerAnnotation = ax.annotate(
    'Max. Power', xy=(10,10), xytext=(10,10),
    arrowprops = {'arrowstyle': "->"}, size=FONTSIZE
)

# at = ax.annotate(
#     'Please start measurement', xy=(1,1), xytext=(1,1),
#     arrowprops = {'arrowstyle': "->"}
# )


# Placeholder annotation for cell measurement counter
cellInfoAnnotation = axQ.annotate(
    '', xy=(0,0), xytext=(0.5,0.25), size=FONTSIZE, ha='center'
)

# at = AnchoredText(
#     "Please start measurement", prop=dict(size=15), frameon=True, loc='upper left')
# at.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
# ax.add_artist(at)


fig.set_size_inches(17,13)
ax.set_xlabel('Voltage (V)', size=FONTSIZE)
ax.set_ylabel('Current (mA)', size=FONTSIZE)
ax.set_title('Berry Solar Power', size=FONTSIZE+4)
ax.grid(color = gridcolor, linestyle = '--', linewidth = 0.3)

ax2 = ax.twinx()
ax2.set_ylabel('Power (mW)', size=FONTSIZE)
ax2.set_ylim([0, ymax*POWERSCALE])

axQ.set_xticks([])
axQ.set_yticks([])

for label in ax2.yaxis.get_majorticklabels():
        label.set_fontsize(FONTSIZE)

# ax.imshow(logo, extent=[0,1,0,1])

plt.show(block=False)
plt.pause(0.1)

bg = fig.canvas.copy_from_bbox(fig.bbox)

# ax = fig.add_subplot(111)

ax.draw_artist(powerline)
ax.draw_artist(currentline)
fig.canvas.blit(fig.bbox)

if mode == 'serial':
    a = ProcessSerial("SerialThread")
    a.start()
if mode == 'udp':
    a = ProcessUDP("UdpThread")
    a.start()
# a.join()

kbd = ProcessKeyboard("KbdThread")
kbd.start()

def printQueueWorker():
    global brotherprinter
    while True:
        item = printQueue.get()
        filename = item[0]
        count = item[1]
        print(f'Printing  {filename}, cell number {count}, sending to {printerType}')

        if printerType == 'peripage':
            final = Image.open(filename)
            ppa6printer = ppa6.Printer(printerMac, ppa6.PrinterType.A6p)
            ppa6printer.connect()
            ppa6printer.reset()
            ppa6printer.setConcentration(1)
            ppa6printer.printBreak(25)
            ppa6printer.printImage(final)
            text = " Berry Cell #{}\n".format(count) 
            ppa6printer.printBreak(10)
            ppa6printer.printASCII(text)
            ppa6printer.printBreak(25)
            ppa6printer.disconnect()

            print(f'Done printing {filename}, you have 5 seconds to cut the paper')
            time.sleep(5)
        
        elif printerType == 'brother':
            sendToBrotherPrinter(filename)
            print(f'{filename} sent to {PRINTER_IDENTIFIER}')
        printQueue.task_done()

# turn-on the worker thread
threading.Thread(target=printQueueWorker, daemon=True).start()

# sclJob = ProcessSocialAction("SocialActionJob")
# sclJob.start()

stimeout = True
dataprocessed = False
# absruntime = datetime.datetime.now() - datetime.datetime.now()

tw = berrytwitter.TwitterConfiguration

twitterApi = twitter.Api(consumer_key=tw.consumer_key,
                  consumer_secret=tw.consumer_secret,
                  access_token_key=tw.access_token_key,
                  access_token_secret=tw.access_token_secret,
                  sleep_on_rate_limit=True)

while (True):
    # render = True
    skipped = False
    starttime = datetime.datetime.now()

    if stimeout == True:
        # print("Timeout...")
        # Placeholder for please start measurement
        infoAnnotation = ax.annotate(
            '', xy=(10,10), xytext=(10,10), size=FONTSIZE
        )

        if dataprocessed == True:
            infoAnnotation.set_text("Please restart measurement!")
            saveImageNow = False
        infoAnnotation.set_position((xmax/2 - 0.15*xmax , ymax/2))
        infoAnnotation.xy = (1,1)
        ax.draw_artist(infoAnnotation)
        fig.canvas.blit(fig.bbox)
        fig.canvas.flush_events()
        infoAnnotation.remove()
            

    # if info == "0,0,0,0,0,0,0,0,0,0":
    #     at.set_position((xmax/2 - 0.15*xmax , ymax/2))
    #     at.xy = (1,1)
    #     ax.draw_artist(at)
    #     fig.canvas.blit(fig.bbox)
    #     fig.canvas.flush_events()
    #     print("Empty values...")

    if info.count(',') == msr and stimeout == False:
        # print(info)
        dataprocessed = True
        # print("Process new Package...")
        # render = False
        # s1, s2, s3, s4, s5, s6, s7, s8, s9, count = info.split(",")
        s = info.split(",")
        # set info to empty string to prevent double processing
        info = ""

        count = s[msr] # last one is count
        # print("Count: ", count)
        # print("Values: ", s)
        if count != prevCount:

            for i in range(msr):
                # Compensate for power supply reference voltage
                voltage[i] = (float(s[i])+0.00001*(msr+1))/AREFFACTOR
                current[i] = (voltage[i]*1000/(res[i]+RSERIES)) / (1 + MAGICVA/voltage[i])

                #current[i] = (voltage[i]*1000/(res[i]+RSERIES))
                power[i] = voltage[i]*current[i]*POWERSCALE

            # print("Voltage:\t", voltage)
            # print("Current:\t", current)
            # print("Power:\t", power)

            icount = int(count)
 
            for i in range(msr):
                xm[i][icount] = voltage[i]
                pym[i][icount] = power[i]
                iym[i][icount] = current[i]

            newx = np.empty([msr])
            newpy = np.empty([msr])
            newiy = np.empty([msr])

            for i in range(msr):
                # use moving average for fast changing measurements. E.g., silicon cell
                if USEMOVINGAVERAGE == True:
                    newx[i] = moving_average(xm[i], MAVALUES)[0]+0.00001*i*random.random()
                    newpy[i] = moving_average(pym[i], MAVALUES)[0]
                    newiy[i] = moving_average(iym[i], MAVALUES)[0]
                else:
                    newx[i] = voltage[i]+0.00001*i*random.random()
                    newpy[i] = power[i]
                    newiy[i] = current[i]


            # print("Vmax: ", newx.max())
            # print("Vmin: ", newx.min())
            # print("Imax: ", newiy.max())
            # print("Imin: ", newiy.min())
            # print("Pmax: ", newpy.max())
            # print("Pmin: ", newpy.min())
            # print("\n")

            # Set first values so they intersect with y-axis
            newx[0] = 0
            newpy[0] = 0

            # print("new x: ", newx)
            # print("new py: ", newpy)
            # print("new iy: ", newiy)

            fig.canvas.restore_region(bg)

            # x = np.empty(zeros)
            # py = np.empty(zeros)
            # iy = np.empty(zeros)

            # for i in range(msr):
            #     np.array.append(x, voltageaverage[i][0])
            #     np.array.append(py, poweraverage[i][0])
            #     np.array.append(iy, currentaverage[i][0])

            # print("x: ", x)
            # print("py: ", py)
            # print("iy: ", iy)
            # Adding small random values to x to prevent interpolation problem "ValueError: Expect x to not have duplicates"
            # x = np.array([v9a[0]+0.00001*random.random(),v8a[0]+0.00001*random.random(),v7a[0]+0.00001*random.random(),v6a[0]+0.00001*random.random(),v5a[0]+0.00001*random.random(),v4a[0]+0.00001*random.random(),v3a[0]+0.00001*random.random(),v2a[0]+0.00001*random.random(),v1a[0]+0.00001*random.random(),v0a[0]+0.00001*random.random()])
            # py = np.array([p9a[0],p8a[0],p7a[0],p6a[0],p5a[0],p4a[0],p3a[0],p2a[0],p1a[0],p0a[0]])
            # iy = np.array([i9a[0],i8a[0],i7a[0],i6a[0],i5a[0],i4a[0],i3a[0],i2a[0],i1a[0],i0a[0]*1.015])

            # x = np.array([0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0])
            # py = np.array([0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0])
            # iy = np.array([0.2,0.4,0.6,0.8,1.0,1.2,1.4,1.6,1.8,2.0])

            # print("npx: ", x)

            # x = np.array([v9,v8,v7,v6,v5,v4,v3,v2,v1])
            # y = np.array([p9,p8,p7,p6,p5,p4,p3,p2,p1])
            
            powermeasure.set_xdata(newx)
            powermeasure.set_ydata(newpy)

            currentmeasure.set_xdata(newx)
            currentmeasure.set_ydata(newiy)

            power_interpolation = interp1d(newx, newpy, kind = INTERPOLATIONTYPE)
            current_interpolation = interp1d(newx, newiy, kind = INTERPOLATIONTYPE)

            X_=np.linspace(newx.min(), newx.max(), 1000)
            PY_=power_interpolation(X_)
            IY_=current_interpolation(X_)

            powerline.set_xdata(X_)
            powerline.set_ydata(PY_)

            currentline.set_xdata(X_)
            currentline.set_ydata(IY_)

            maxindexvalues = np.where( newpy == newpy.max())
            maxindex = int(maxindexvalues[0][0])

            xpos = newx[maxindex]
            maxpower = newpy.max()
            maxcurrent = newiy[maxindex]

            mpp.set_xdata(xpos)
            mpp.set_ydata(maxpower)

            # if maxpower > 1.5:
            #     ax.set_ylim([0, maxpower+1.0])
            # else:
            #     ax.set_ylim([0, 1.7])

            maxPowerAnnotation.set_position((xpos,maxpower+0.1*ymax))
            maxPowerAnnotation.xy = (xpos,maxpower)

            # print("Max power: ", maxpower)

            # fill power area in IV-Curve

            # if imagesaved == False:
            #     filler = ax.fill_between((0,xpos),(maxcurrent,maxcurrent), color = powerfillcolor, alpha = 0)
            # else:
            # old else begin
            # filler = ax.fill_between((0,xpos),(maxcurrent,maxcurrent), color = powerfillcolor, alpha = 0.15)
            
            if saveImageNow == False:
                ab = AnnotationBbox(imagebox, (xmax/2,ymax*0.76), bboxprops =dict(alpha=0.0))
                ax.add_artist(ab)
                ax.draw_artist(ab)
                ab.remove()

            # if drawPowerArea == True:
            #     print("Draw MPP Area!")
            #     filler = ax.fill_between((0,xpos),(maxcurrent,maxcurrent), color = powerfillcolor, alpha = 0.15)
            #     ax.draw_artist(filler)
            #     filler.remove()

            filler = ax.fill_between((0,xpos),(maxcurrent,maxcurrent), color = powerfillcolor, alpha = 0.15)
            ax.draw_artist(filler)
            filler.remove()

            # old else end

            ax.margins(0.05)
            # ax.draw_artist(filler)
            #ax.draw_artist(powerline)
            ax.draw_artist(powermeasure)
            ax.draw_artist(mpp)
            ax.draw_artist(maxPowerAnnotation)

            #ax2.draw_artist(currentline)
            ax2.draw_artist(currentmeasure)

            cellInfoAnnotation.set_text('Berry Cell: {}'.format(currentCell))
            axQ.draw_artist(cellInfoAnnotation)

            fig.canvas.blit(fig.bbox)
            fig.canvas.flush_events()
            # render = True
            # print("Rendering done")
            # time.sleep(0.1)
            # fig.canvas.draw()
            # fig.canvas.flush_events()
            # plt.pause(0.2)
        else:
            skipped = True
            # print('Skip duplicate')
        
        prevCount = count
        endtime = datetime.datetime.now()
        runtime = endtime - starttime
        # absruntime = endtime - acquisitionstarttime
        if skipped == False and printrendertime == True:
            print (runtime.microseconds/1000)

        if saveImageNow == True:
            # print("Save image now")

            # Draw annotation box once for printing
            ab = AnnotationBbox(imagebox, (xmax/2,ymax*0.76), bboxprops =dict(alpha=0.0))
            ax.add_artist(ab)
            ax.draw_artist(ab)

            # Draw filler once for printing
            filler = ax.fill_between((0,xpos),(maxcurrent,maxcurrent), color = powerfillcolor, alpha = 0.15)
            ax.draw_artist(filler)
            fileTimeStamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") 

            imagePngOut = "out/mycell-" + fileTimeStamp + ".png"
            stickerFileOut = "out/mycell-" + fileTimeStamp + "-sticker.png"

            fig.canvas.flush_events()
            plt.savefig(imagePngOut)

            # Remove annotation box and filler again
            ab.remove()
            filler.remove()


            th = threading.Thread(target=SocialActionFunction, args=(fileTimeStamp,currentCell))
            # Start the thread
            th.start()

            currentCell=currentCell+1
            saveImageNow = False
            # processSocialAction = True

            # sclAction = threading.Thread(target=SocialActionFunction, args=('testfilename'))
            # sclAction.start()


            # if tweetResult == True:
            #     print('Tweet the result!')
            #     media_id = twitterApi.UploadMediaSimple(imagePngOut)
            #     status = twitterApi.PostUpdate(status='We love dye cells!', media=media_id)
            #     qrString = status.media[0].url
            #     print(qrString)
            #     print(status.text)
            # if uploadToGoogle == True and tweetResult == False:
            #     print('Point QR code to google, not tweet!')
            #     qrString = 'www.berrycells.com/' + htmlFileName
            #     print(qrString)
            # if uploadToGoogle == False and tweetResult == False:
            #     print('Point QR Code to freitaglab.com!')
            #     qrString = 'https://www.freitaglab.com'

            # qrberry = Image.open('res/qrberry.png')
            # print(qrberry.size)
            # qr_big = qrcode.QRCode(
            #     error_correction=qrcode.constants.ERROR_CORRECT_H
            # )
            # qr_big.add_data(qrString)
            # qr_big.make()
            # img_qr_big = qr_big.make_image().convert('RGB')

            # pos = ((img_qr_big.size[0] - qrberry.size[0]) // 2, (img_qr_big.size[1] - qrberry.size[1]) // 2)

            # img_qr_big.paste(qrberry, pos)
            # img_qr_big = img_qr_big.resize((scaleWidth,scaleWidth))
            # img_qr_big.save(qrFileOut)

            # # Read other logos, no need to resize
            # summerScienceLogo = Image.open('res/SummerScienceLogo.png')
            # berrySolarLogo = Image.open('res/BerrySolarLogo.png')
            # nclBottomLogo = Image.open('res/NCLRoyalSocietyBottomLogo.png')

            # # Concatenate what we just created in right order

            # final = get_concat_v(berrySolarLogo, img_qr_big)
            # final = get_concat_v(final, summerScienceLogo)
            # # final = get_concat_v(final, berrySolarLogo)
            # # if printIVcurve == True:
            # #     final = get_concat_v(final, im_res)
            # final = get_concat_v(final, nclBottomLogo)

            # # black border around image
            # final = ImageOps.expand(final,border=24,fill='black')

            # # Resize again. Can be avoided by making the template images 2*border pixels smaller
            # # Scale figure
            # newheight = int(final.size[1]/(final.size[0]/scaleWidth))
            # final = final.resize((scaleWidth,newheight))

            # final.save(stickerFileOut)
            # print("Saving figure...")

            # with open ("res/mycelltemplate.html", "r") as myfile:
            #     data=myfile.read()
            #     data = data.replace("$IMAGE$",imagePngFileName)
            #     htmlOut = open(htmlFileOut, "w")
            #     n = htmlOut.write(data)
            #     htmlOut.close()
            #     print("Saved html file!")


            # if uploadToGoogle == True:
            #     upload_blob("www.berrycells.com", imagePngOut, imagePngFileName)
            #     upload_blob("www.berrycells.com", htmlFileOut, htmlFileName)
            #     upload_blob("www.berrycells.com", stickerFileOut, stickerFileName)

            # if printSticker == True:
            #     printer = ppa6.Printer(printerMac, ppa6.PrinterType.A6p)
            #     printer.connect()
            #     printer.reset()
            #     printer.setConcentration(2)
            #     printer.printBreak(25)
            #     printer.printImage(final)
            #     printer.printBreak(25)
            #     printer.disconnect()
            # else:
            #     final.show()

    elif info == "SAVE" and stimeout == False:
        print("Network save request!")
        info = ""
        saveImageNow = True
        dataprocessed = True

    # elif info != nullinfo and info != "":
    #     print("Other: " + info)
    #     dataprocessed = True

# ToDo: Move this to own functions
        # if imagesaved == True:
        # #     imagesaved = True
        #     at.set_text("")
        #     filler = ax.fill_between((0,xpos),(maxcurrent,maxcurrent), color = powerfillcolor, alpha = 0)

        #     ax.draw_artist(filler)

        #     fig.canvas.blit(fig.bbox)
        #     fig.canvas.flush_events()

        #     imagePng = "figure.png"
        #     printFile = "print.png"
        #     finalFile = "final.png"
        #     plt.savefig(imagePng)

        #     # Read figure and transform to one color b/w
        #     im = Image.open(imagePng)
        #     im_res = ImageOps.invert(im.convert('RGB'))
        #     im_res = ImageOps.grayscale(im_res)
        #     im_res = ImageOps.colorize(im_res,  'black', 'white', blackpoint=253, whitepoint=254)
        #     print(im_res.size[1])
        #     # im_res.show()

        #     twitterLeft = Image.open('TwitterLeft.png')
        #     im_res = get_concat_h(twitterLeft, im_res)


        #     im_res.save(printFile, quality=100)
        #     scaleWidth = 576
        #     # Scale figure
        #     newheight = int(im_res.size[1]/(im_res.size[0]/scaleWidth))
        #     im_res = im_res.resize((scaleWidth,newheight))

        #     # print("Figure size:", im_res.size)
        #     # width = im_res.size[0]

        #     if tweetResult == True:
        #         print('Tweet the result!')
        #         media_id = twitterApi.UploadMediaSimple(imagePng)
        #         status = twitterApi.PostUpdate(status='We love dye cells!', media=media_id)
        #         qrString = status.media[0].url
        #         print(qrString)
        #         print(status.text)
        #     if uploadToGoogle == True:
        #         print('Upload to google!')
        #         fileTimeStamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") 
        #         blobName = fileTimeStamp + ".png"
        #         blobNameSticker = fileTimeStamp + "-sticker.png"
        #     if uploadToGoogle == True and tweetResult == False:
        #         print('Point QR code to google, not tweet!')
        #         qrString = 'www.berrycells.com/' + blobName
        #         print(qrString)
        #     if uploadToGoogle == False and tweetResult == False:
        #         print('Point QR Code to freitaglab.com!')
        #         qrString = 'https://www.freitaglab.com'

        #     # qrimg = qrcode.make(qrString)
        #     # qrimg = qrimg.resize((width,width))
        #     # qrimg.save("qr.png")

        #     qrberry = Image.open('qrberry.png')
        #     print(qrberry.size)
        #     qr_big = qrcode.QRCode(
        #         error_correction=qrcode.constants.ERROR_CORRECT_H
        #     )
        #     qr_big.add_data(qrString)
        #     qr_big.make()
        #     img_qr_big = qr_big.make_image().convert('RGB')

        #     pos = ((img_qr_big.size[0] - qrberry.size[0]) // 2, (img_qr_big.size[1] - qrberry.size[1]) // 2)

        #     img_qr_big.paste(qrberry, pos)
        #     img_qr_big = img_qr_big.resize((scaleWidth,scaleWidth))
        #     img_qr_big.save('qr.png')

        #     # Read other logos, no need to resize
        #     summerScienceLogo = Image.open('SummerScienceLogo.png')
        #     berrySolarLogo = Image.open('BerrySolarLogo.png')
        #     nclBottomLogo = Image.open('NCLRoyalSocietyBottomLogo.png')

        #     # Concatenate what we just created in right order

        #     final = get_concat_v(berrySolarLogo, img_qr_big)
        #     final = get_concat_v(final, summerScienceLogo)
        #     # final = get_concat_v(final, berrySolarLogo)
        #     if printIVcurve == True:
        #         final = get_concat_v(final, im_res)
        #     final = get_concat_v(final, nclBottomLogo)

        #     # black border around image
        #     final = ImageOps.expand(final,border=24,fill='black')

        #     # Resize again. Can be avoided by making the template images 2*border pixels smaller
        #     # Scale figure
        #     newheight = int(final.size[1]/(final.size[0]/scaleWidth))
        #     final = final.resize((scaleWidth,newheight))

        #     final.save(finalFile)
        #     print("Saving figure...")

        #     if uploadToGoogle == True:
        #         upload_blob("www.berrycells.com", "figure.png", blobName)
        #         upload_blob("www.berrycells.com", "final.png", blobNameSticker)

        #     if printSticker == True:
        #         printer = ppa6.Printer(printerMac, ppa6.PrinterType.A6p)
        #         printer.connect()
        #         printer.reset()
        #         printer.setConcentration(2)
        #         printer.printBreak(25)
        #         printer.printImage(final)
        #         printer.printBreak(25)
        #     else:
        #         final.show()

# End move this to functions!
            # for axis in ['top','bottom','left','right']:
            #     ax.spines[axis].set_linewidth(16)

            # bg = fig.canvas.copy_from_bbox(fig.bbox)


        # input("Press Enter to continue...")

        # clear out pending datagrams to speed up processing
        # if ready[0]:
        #     data, addr = sock.recvfrom(64)
        #     fig.canvas.flush_events()


        #     print("Skipped datagram")        

    # else:
    #     print("Skip processing...")