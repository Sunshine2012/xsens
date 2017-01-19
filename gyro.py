import logging
import time
import serial
import binascii
from logging.handlers import TimedRotatingFileHandler
from binascii import *
from struct import *

#gp = "\x55\x55\x47\x50\x02\x41\x32\xB4\xC5" #Data poll request packet

class crcException(Exception):
    pass

class unitErrorException(Exception):
    pass

def checkCrc(data):
    #print len(data),hexlify(data),'b'*(len(data)-2)
    payl = unpack('b'*(len(data)-2),data[1:-1])
    # csum = 0
    # for a in payl:
    #     csum += a
    #     csum %= 127

    #refcrc = -((sum(payl) & (0xFF)))
    refcrc = -(sum(payl) % 256)
    if(refcrc < -128):
        refcrc += 256
    #refcrc = 0-refcrc
    #refcrc = refcrc % 256
    # refcrc = (csum)*(-1)
    gotcrc = unpack("b",data[len(data)-1])[0]
    crcOk = (refcrc==gotcrc)
    #print refcrc, gotcrc, crcOk
    if crcOk:
        return data
    #else:
        #return data
    else:
        #check double messages
        splitlist = hexlify(data).split("faff")
        if len(splitlist) > 2:
            print "Got two messages."
            print "Checking first message:"
            print "faff"+splitlist[1]
            return checkCrc(unhexlify("faff"+splitlist[1]))
        else:
            raise crcException("CRC recv mismatch.")

def read(ser, dlen):
    raw = ser.read(dlen)
    print hexlify(raw)
    data = checkCrc(raw)
    mid = hexlify(data[2:3])
    if(mid == "42"):
        errorCode = hexlify(data[4:5])
        #print errorCode
        if(errorCode == "03"):
            raise unitErrorException("Not in range");
        elif(errorCode == "04"):
            raise unitErrorException("Message sent is invalid");
        elif(errorCode == "1e"):
            raise unitErrorException("Timer overflow");
        elif(errorCode == "20"):
            raise unitErrorException("Baud rate not in range");
        elif(errorCode == "21"):
            raise unitErrorException("Parameter invalid or not in range");
        elif(errorCode == "28"):
            raise unitErrorException("Device error");
    else:
        return data

def addCrc(data):
    unpackStr = "b"*(len(data)-1)
    payl = unpack(unpackStr,data[1:])
    crc = sum(payl)*(-1)
    return data+chr(crc & 0xFF)

def write(ser, data):
    dsend = addCrc(data)
    print "Sending: ",hexlify(dsend),
    ser.write(dsend)

def create_timed_rotating_log(path):
    """"""
    # logger = logging.getLogger("Rotating Log")
    # logger.setLevel(logging.INFO)

    # handler = TimedRotatingFileHandler(path,
    #                                    when="D",
    #                                    interval=1,
    #                                    backupCount=87600) #10 years of sampling
    # logger.addHandler(handler)

    #Enter config mod

    CM_SET = "\xFA\xFF\x30\x00\xD1" #Go to config mode
    OM_SET = "\xFA\xFF\xD0\x02\x00\x06" #Set output mode 0xD0
    QUAT_SET = "\xFA\xFF\xD2\x04\x00\x00\x00\x01" #Set output settings
    OUTPUT_SKIP = "\xFA\xFF\xD4\x02\x00\x00" #Set output skip factor
    MM_SET = "\xFA\xFF\x10\x00" #Goto measurement mode
    poll = "\xFA\xFF\x34\x00"
    POLL_CONF_SET = "\xFA\xFF\x2C\x0C\x08\x06\x01\x00\x00\x00\x00\x00\x00\x0A\x00\x00"

    CM_SET_ACK = "\xFA\xFF\x31\x00\xD0"
    MM_SET_ACK = "\xFA\xFF\x11\x00\xF0" #Goto measurement mode
    #setpermcf = "\xFA\xFF\x48\x08\x00\x00\x00\x02\x00\x00\x00\x00"
    print "Opening /dev/tty.usbserial-XST00EIX"
    with serial.Serial('/dev/tty.usbserial-XST00EIX', 115200, timeout=5) as ser:

        print "Goto config mode."
        write(ser,CM_SET) #Poll data
        try:
            rdata = read(ser, 5);
            print "Resp: ",hexlify(rdata)
            if rdata == CM_SET_ACK:
                print "Entered config mode."
            else:
                print "Error. Config mode not entered upon request. Now exiting."
                exit(0)
        except:
            raise

        # print "Setting sync settings"
        # write(ser,POLL_CONF_SET) #Poll data
        # try:
        #     rdata = read(ser, 1);
        #     print "Resp: ",hexlify(rdata)
        # except:
        #     raise

        # print "Setting outputmode"
        # write(ser,OM_SET)
        # try:
        #     rdata = read(ser, 5);
        #     print "  Resp: ",hexlify(rdata)
        # except:
        #     raise

        # print "Setting quaternions."
        # write(ser,QUAT_SET)
        # try:
        #     rdata = read(ser, 5);
        #     print "  Resp: ",hexlify(rdata)
        # except:
        #     raise

        print "Goto measurement mode."
        write(ser,MM_SET)
        try:
            rdata = read(ser, 5);
            print "  Resp: ",hexlify(rdata)
            if rdata == MM_SET_ACK:
                print "Entered measurement mode."
            else:
                print "Error. Measurement mode not entered upon request. Now exiting."
                exit(0)
        except:
            raise


        # while True:
        #     rdata = read(ser, 37)
        #     print hexlify(rdata)

        print "Making polls:"
        while True:
            write(ser,poll)
            try:
                rdata = read(ser, 63);
                print "  Resp: ",hexlify(rdata)
            except:
                raise

        # print "Setting quaternions"
        # write(ser,om)
        # try:
        #     rdata = read(ser, 5);
        #     print hexlify(rdata)
        # except:
        #     raise

        # out = unpack("bbb",read[1:-1])
        # print sum(out)*(-1)
        # ans = hexlify(read)
        # print ans,out

        return

        while True:
            try:
                #t_ = time.time() #Store beginning time
                ser.write(poll) #Poll data
                out = ser.read(63) #Read 37 data bytes
                ahex = binascii.hexlify(out) #Convert to hex ascii

                time.sleep(0.1);
                #t2_ = time.time()
                #sleeptime =  0.1 - (t2_ - t_) #Calculate nominal sleeping time
                #time.sleep(sleeptime)
                #logger.info('\t'.join([str(time.time()),ahex]))
                #print ahex
            except KeyboardInterrupt:
                raise
            except:
                pass

#----------------------------------------------------------------------
if __name__ == "__main__":
    log_file = "/data/gyro/gyro.log"
    create_timed_rotating_log(log_file)
