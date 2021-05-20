#!/usr/bin/env python

# ovl-upload.c, by ABelliqueux, 04-2021 license GNU General Public License v3.0

# This working version corrected with the help of sickle : 
# https://discord.com/channels/642647820683444236/663664210525290507/836029253593858060
# Corrected script by Sickle : http://psx.arthus.net/code/rawdog.py

# Sickle - 26/04/2021 :
# " Ooh, you were like frustratingly close dude! Few tiny issues:
# - first of your 3 rolling buffers was bugged (other 2 were spot on)
# - waiting too long between commands at points, unirom timed out
# - var i was missing the i += chunkSize so we were stuck in a loop there (e.g. tried to send a second chonk)
# - exit was gummed up with the main logic being in a while True: "

# As suggested: 
# - Removed while True: loop
# - moved rolling buffer loops to WaitForResponse()
# - reduced sleeps
# - inc var i with chunkSize

import sys
import os
import serial
import time
import calendar
import math

DEBUG = 1

SERIAL_DEVICE = '/dev/ttyUSB0'

SERIAL_SPEED  = 115200

# pcdrv

pcdrvEscape   = '00'

pcdrvProtocol = '01'

# Commands 

OPEN  = '00'
CLOSE = '01'
SEEK  = '02'
READ  = '03'
WRITE = '04'
CREAT = '05'
LOAD  = '06'
INIT  = '07'

# Param sets

loadParams  = {'memAddr':-1, 'loadFile':-1, 'bufferAddr':-1}

creatParams = {'fileName':-1, 'bufferAddr':-1, 'mode':-1}

openParams  = {'fileName':-1, 'bufferAddr':-1,'mode':-1 }

closeParams = {'fileDesc':-1, 'bufferAddr':-1}

seekParams  = {'fileDesc':-1,'curPos': -1,'offset':-1, 'bufferAddr':-1, 'accessMode':-1}

readParams  = {'fileDesc':-1,'pos': -1, 'length':-1, 'dataAddr':-1, 'bufferAddr':-1}

writeParams = {'fileDesc':-1,'pos': -1, 'length':-1, 'data':-1, 'bufferAddr':-1}

paramBuffer = {}

# Names of the overlay files to load.
# See l.550

overlayFiles = {'00':"Overlay.ovl0", '01':"Overlay.ovl1" }

# Serial connection setup

ser = serial.Serial(SERIAL_DEVICE)

# Unirom can do 115200 and 510000 ( https://github.com/JonathanDotCel/NOTPSXSerial/blob/bce29e87cb858769fe60eb34d8eb123f9f36c8db/NOTPSXSERIAL.CS#L842 )

ser.baudrate = SERIAL_SPEED

# Working directory

cwd = os.getcwd()

dataFolder = cwd + os.sep

# Should we listen for commands on serial ?

Listen    = 1 

# Will be set once unirom is in debug mode

uniDebugMode = 0

# Will hold the commands received from the psx

Command = ""

loadFile = -1

# One byte

data = 0

# checkSum is the checkSum for the full data

checkSum = 0

checkSumLen = 10 # Corresponding value in pcdrv.h, l.54

# If set, it means the data transfer has been initiated 

Transfer = 0

# Delay between write operations. These seem to be needed for the connection not to hang.

sleepTime = 0.08    # Seems like safe minimum

# https://www.tutorialspoint.com/How-to-close-all-the-opened-files-using-Python

class openFiles():
    
    def __init__(self):
    
        self.files = []
    
    def open(self, file_name, mode):
    
        f = os.open(file_name, mode)
    
        self.files.append(f)
    
        return f
    
    def close(self):
    
        list( map( lambda f : os.close(f), self.files ) )

def setDEBG():
    
    global sleepTime, ser, uniDebugMode
    
    if DEBUG:
        
        print("Sending DEBG command...")
    
    ser.write( bytes( 'DEBG' , 'ascii' ) )
    
    time.sleep(sleepTime)
                
    # Empty in waiting buffer
    
    ser.reset_input_buffer()
    
    time.sleep(sleepTime)
    
    uniDebugMode = 1

# stole it here : https://gist.github.com/amakukha/7854a3e910cb5866b53bf4b2af1af968

def hash_djb2(s):

    hash = 5381

    for x in s:

        hash = ((( hash << 5) + hash) ^ x) & 0xFFFFFFFF

    return hash

def WaitForResponse( expectedAnswer ):

    # Get incoming data from the serial port in a rolling buffer 
    # when the content of the buffer corresponds to 'expectedAnswer', returns True
    
    global DEBUG
    
    responseBuffer = ""
    
    success = False
    
    while True:
        
        if DEBUG > 3:
            
            print("Waiting for data in serial input buffer.")
        
        # If data in serial's incoming buffer
        
        if ser.in_waiting:
        
            if DEBUG > 1:
            
                print("Brace yourself, data is coming...")
            
            # Read 1 byte
        
            byteValue = ser.read(1)
            
            # Make sure byte value is < 128 so that it can be decoded to ascii
            
            if byteValue[0] < 128:
            
                responseBuffer += byteValue.decode('ascii')  
            
            else:
                
                responseBuffer += '.'
            
            # Always keep response buffer 4 chars long
            
            if len( responseBuffer ) > 4:
                
                # Remove first char in buffer
                
                responseBuffer = responseBuffer[1:]
            
            
            # If response is ERR!, checksum check does not check, so check it again
            
            if responseBuffer == "ERR!":
                
                if DEBUG > 1:
            
                    print("Checksum error !")
                
                success = False
                
                break
                
            # When expected response shows up, break from the while loop
            
            if responseBuffer == expectedAnswer:
                
                success = True
                
                break
    if DEBUG  > 1:
    
        print( "Got : " + responseBuffer )
    
    responseBuffer = ""
    
    return success
    
def CalculateChecksum( inBytes, skipFirstSector = False):
    
    returnVal = 0;
    
    i = 0
    
    if skipFirstSector:
        
         i = 2048
    
    while i < len( inBytes ):

        returnVal += inBytes[i];
        
        i += 1
    
    return returnVal;

def getData(dataInBuffer):
    
    dataLen = 0

    parsedData = ""

    # Get data length byte

    # If only 2 bytes left, dont't bother

    if len(dataInBuffer) == 2:
                                            
        parsedData = dataInBuffer
        
        dataInBuffer = ""
        
        return [dataInBuffer, parsedData]

    dataLen = int( dataInBuffer[:2] )

    dataInBuffer = dataInBuffer[2:]

    # Get actual data

    for b in dataInBuffer :
        
        if len(parsedData) < dataLen : 
            
            parsedData += b

    # Remove data from buffer

    dataInBuffer = dataInBuffer[dataLen:]

    if DEBUG:

        print( "Data in buffer 1: " + dataInBuffer )

    return [dataInBuffer, parsedData]

def WriteBytes( inData ):
    
    if DEBUG:
        
        print("Preparing to write bytes...")
        
    # The data needs to be split in 2K chunks 
    
    chunkSize = 2048
    
    # BEGIN WHILE DATA
    
    i = 0
    
    while i < len( inData ):
        
        # BEGIN WHILE TRUE
        
        while True:
            
            # BEGIN TRY/EXCEPT
            
            try:
                    
                # Calculate number of 2K chunks we're about to send
                
                numChunk = math.ceil( len( inData ) / chunkSize )
                
                # Calculate current chunk
                
                currentChunk = math.ceil( (i + 1) / chunkSize)                
                
                if DEBUG:
                    
                    print( str ( numChunk + 1 - currentChunk ) + " chunks of " + str ( chunkSize) + " bytes to send " )
                
                # Avoid going out of range
                
                if ( i + chunkSize ) > len( inData ):
                    
                    chunkSize = len( inData ) - i
                    
                print("Writing chunk " + str( currentChunk ) + " of " + str( numChunk ) )
                                
                # ~ ser.write(inData)

                chunkChecksum = 0
                
                # Send inData in 2048B chunks
                
                for byte in range( chunkSize ):
                    
                    # Send byte
                    
                    if DEBUG > 1:
                        
                        print("Writing " + str( inData[ i + byte ].to_bytes(1, byteorder='little', signed=False) ) + " to serial..." )
                    
                    ser.write( inData[ i + byte ].to_bytes(1, byteorder='little', signed=False) )
                    
                    # Calculate chunk checksum
                    
                    chunkChecksum += inData[ i + byte ]
                                            
                time.sleep(sleepTime)
                
                if DEBUG:                        
                
                    print( "Chunk cheksum : " + str( chunkChecksum ) ) 
                
                # Wait for output buffer to be empty
                # REMOVE ? Is this needed ?
                
                while ser.out_waiting:
                    
                    print("*")
                    
                    wait += 1
                
                time.sleep(sleepTime)
                
                # Wait for unirom to request the checksum
                
                if DEBUG > 1:
                
                    print( "Chunk " + str( currentChunk ) + " waiting for unirom to request checksum (CHEK)..." )
                
                WaitForResponse( "CHEK" )
                
                # Send checksum
                
                if DEBUG:
                
                    print( "Sending checksum to unirom..." );
                
                # ~ chunkChecksum = 170
                
                bytesChunkChecksum = chunkChecksum.to_bytes( 4, byteorder='little', signed = False )
                
                ser.write( bytesChunkChecksum )
                
                # ~ time.sleep( sleepTime )
            
                if DEBUG > 1:
                    
                    print( "Waiting for unirom to request more data (MORE)..." )
            
                # Wait for unirom to request MORE inData ( next chunk )
            
                if not WaitForResponse("MORE"):
                    
                    if DEBUG:
                        
                        print("ERROR ! Retrying...")

                        # ~ ser.write(b'ERR!')

                    raise Exception()
            
                if DEBUG:
                    
                    print( str( currentChunk ) + " chunk sent with correct checksum.")
        
                # Increment i from chunkSize
        
                i += chunkSize
                
            except Exception:
                
                continue
            
            # END TRY/EXCEPT
            
            # ~ ser.write(b'OKAY');
            
            if DEBUG:
                
                print("Sending OKAY")
            
            break
        
        # END WHILE TRUE
    
        numChunk = 0
    
    return True
    
    # END WHILE DATA

def SendBin( inData, memAddr ):
    
    global sleepTime 
    
    dataSize = len( inData )
    
    if DEBUG:
        
        print("Data size : " + str( dataSize ) )
    
    # Prepare unirom for data reception - sent "SBIN" - received : "OKV2"
    
    if DEBUG > 1:
        
        print("Sending SBIN command...")
    
    ser.write( bytes( 'SBIN' , 'ascii' ) )
    
    time.sleep(sleepTime)
    
    # We're using unirom in debug mode, which means protocol version 2 is available
    # Upgrade protocol  - sent "UPV2" - received : "OKAY"
    
    ser.write( bytes( 'UPV2' , 'ascii' ) )

    time.sleep(sleepTime)

    # Initialisation done, set flag
    
    # ~ Init = 1
    
    # From now on, we're using the rolling buffer
    if DEBUG  > 1:
        
        print("Waiting for OKAY...")
    
    WaitForResponse("OKAY")
    
    # Calculate data checkSum

    checkSum = CalculateChecksum( inData )

    if DEBUG :
        
        print("Data checkSum : " + str(checkSum) )
    
    # Send memory address to load data to, size of data and checkSum
    # Unirom expects unsigned longs ( 32bits ), byte endianness little
    
    # Convert address from string to integer, then to ulong 32b
    
    bytesAddr = int( memAddr, 16 ).to_bytes( 4, byteorder='little', signed=False )
    
    # Write address to serial
    
    ser.write( bytesAddr )
    
    time.sleep(sleepTime)
    
    # Convert and write int size to serial
    
    bytesSize = dataSize.to_bytes( 4, byteorder='little', signed = False )
    
    ser.write( bytesSize )
    
    time.sleep(sleepTime)
    
    # Convert and write int chekSum to serial
    
    bytesChk = checkSum.to_bytes( 4, byteorder='little', signed = False )
    
    ser.write( bytesChk )
    
    time.sleep(sleepTime)

    # Send dat data
    
    return WriteBytes( inData )

def resetListener():
    
    global checkSum, data, Listen, Transfer, dataSize, loadFile
    
    loadFile = -1
    
    checkSum = 0
    
    data = 0
    
    dataSize = 0
    
    Transfer = 0
    
    Listen = 1

    ser.reset_input_buffer()
    
    ser.reset_output_buffer()
    
def main(args):
    
    files = openFiles()

    while True:
    
        global checkSum, checkSumLen,  data, Listen, Transfer, dataSize, loadFile, paramBuffer

        # Flush serial buffers to avoid residual data
        
        ser.reset_input_buffer()
        
        ser.reset_output_buffer()
        
        inputBuffer = ""
            
        # Listen to incomming connections on serial
        
        if Listen:

            print("Listening for incoming data...")
            
            while True:

                # If data on serial, fill buffer
                
                while ser.in_waiting:
                    
                    inputBuffer += ser.read().decode('ascii')

                    if DEBUG > 2:
                            
                        print( "Raw data : " + inputBuffer )
                                
                if inputBuffer:
                
                    print( "Incoming data : " + inputBuffer )
                
                    # LOAD command format : 00 01 06 04 xx xx xx xx 04 xx xx xx xx 01 xx xx xx xx (37 Bytes) 
                        
                    # ~ if len(inputBuffer) == 37:
                    
                    if DEBUG:
                        
                        print( "Incoming data : " + inputBuffer )
                
                    # Get the checksum and remove it from the buffer
                
                    CmdCheckSum = inputBuffer[-checkSumLen:]
                    
                    if CmdCheckSum.islower() or CmdCheckSum.isupper() :
                        
                        print("Checksum sould not contain letters ! Aborting.")
                        
                        break
                    
                    if DEBUG:
                                
                        print( "Received ChkSm: " + CmdCheckSum)
                        
                    # Remove checksum from data

                    inputBuffer = inputBuffer[:-checkSumLen]

                    dataCheckSum = hash_djb2(bytes(inputBuffer, 'ascii'))

                    if DEBUG:
                                
                        print( "Computed ChkSm: " + str(dataCheckSum) )
                    
                    # Check 

                    if int(dataCheckSum) == int(CmdCheckSum):
                        
                        # Parse command
                        
                        if inputBuffer[:2] == pcdrvEscape:
                            
                            if DEBUG:
                            
                                print( "Received Escape : " + inputBuffer[:2] )
                            
                            # Escape byte received, remove it from buffer and continue
                            
                            inputBuffer = inputBuffer[2:]
                            
                            if inputBuffer[:2] == pcdrvProtocol:
                                
                                if DEBUG:
                            
                                    print( "Received Proto: " + inputBuffer[:2] )
                                
                                # Protocol byte is pcdrv (01), remove it from buffer and continue
                                
                                inputBuffer = inputBuffer[2:]
                                
                                if DEBUG:
                                    
                                    print( "Received Cmd: " + inputBuffer[:2] )
                                

                                # Command butes are OPEN == 00
                                
                                if inputBuffer[:2] == INIT:

                                    paramTmp = {}
                                
                                    Command = INIT

                                # Command bytes are LOAD == 06 
                                
                                elif inputBuffer[:2] == LOAD:
                                                           
                                    # Set corresponding parameters and mode
                                                                
                                    paramTmp = loadParams
                                    
                                    Command = LOAD
                                
                                # Command butes are OPEN == 00
                                
                                elif inputBuffer[:2] == OPEN:

                                    paramTmp = openParams
                                
                                    Command = OPEN
                                    
                                # Command butes are OPEN == 00
                                
                                elif inputBuffer[:2] == CLOSE:

                                    paramTmp = closeParams
                                
                                    Command = CLOSE
                                    
                                # Command butes are OPEN == 00
                                
                                elif inputBuffer[:2] == SEEK:

                                    paramTmp = seekParams
                                
                                    Command = SEEK
                                    
                                # Command butes are OPEN == 00
                                
                                elif inputBuffer[:2] == READ:

                                    paramTmp = readParams
                                
                                    Command = READ
                                    
                                # Command butes are OPEN == 00
                                
                                elif inputBuffer[:2] == WRITE:

                                    paramTmp = writeParams
                                
                                    Command = WRITE
                                    
                                # Command butes are OPEN == 00
                                
                                elif inputBuffer[:2] == CREAT:

                                    paramTmp = creatParams
                                
                                    Command = CREAT
                                    
                                else:
                                    
                                    print("Command not recognized : got " + inputBuffer[:2] )
                                    
                                    break

                                # Command byte is valid , remove it from buffer and continue
                                
                                inputBuffer = inputBuffer[2:]
                                
                                dataInBuffer = inputBuffer
                                
                                # For each parameter, populate corresponding data
                                
                                for param in paramTmp:
                                    
                                    dataInBuffer, paramTmp[param] = getData(dataInBuffer)
                                
                                if DEBUG:
                                    
                                    for param in paramTmp:
                                        
                                        print(param + ":" + paramTmp[param] + " - ")

                                # Commit parsed data to param buffer
                                
                                paramBuffer = paramTmp

                                ser.reset_input_buffer()
                    
                                inputBuffer = ""

                                Listen = 0
                                
                                break
                    else:
                        
                        print("Command checksum not matching ! Aborting...")
                        
                        ser.reset_input_buffer()
                    
                        inputBuffer = ""
                        
                        break
        
        if len(paramBuffer):
        
            # Check that no param is undefined ( != -1 ) 
        
            for param in paramBuffer:
                
                if paramBuffer[param] == -1:
                    
                    print("Error : parameter " + param + " is undefined.")
                    
                    break
        
            if Command == INIT:
                
                # Close all opened files
                
                files.close()
                
                # Send OK
                
                SendBin( b'OKYA' , paramBuffer['bufferAddr'])
            
            if Command == CLOSE:
                
                fileDesc = paramBuffer['fileDesc']
                
                # Close all opened files
                
                try:
                    
                    os.close(fileDesc)
                
                except OSError as errMsg:
                                
                    SendBin( b'-1', paramBuffer['bufferAddr'])
                
                    print(errMsg)
                    
                    return 0
                
                # Send OK
                
                SendBin( b'OKYA' , paramBuffer['bufferAddr'])
        
            if Command == LOAD:
                                
                # Load file
                
                print("Received LOAD.")
        
                if DEBUG > 1:
                    
                    print("Received addresses and file ID : " + paramBuffer['memAddr'] + " - " + paramBuffer['bufferAddr'] + " - " + paramBuffer['loadFile'] )
                
                binFileName = overlayFiles[ paramBuffer['loadFile'] ]
                
                if DEBUG:

                    print(
                    
                        "Load Data to : " + paramBuffer['memAddr'] + "\n" +
                        
                        "Reset flag at: " + paramBuffer['bufferAddr'] + "\n" +
                        
                        "LoadFile     : " + paramBuffer['loadFile'] + "\n" +
                        
                        "Bin          : " + binFileName
                                        
                        )
            
                # Open file as binary if bin filename is defined
                
                # ~ if binFileName:

                binFile = open( dataFolder + binFileName, 'rb' )
            
                data = binFile.read()
            
                print("Initializing data transfer...")
                
                if not uniDebugMode:
                
                    # Set unirom to debugmode - sent : "DEBG" - received : "DEBGOKAY"
                
                    setDEBG()
                
                # Send data
                
                if SendBin( data, paramBuffer['memAddr'] ):
                
                    time.sleep( sleepTime )
                    
                    # Send ACK
                    
                    SendBin( b'OKYA' , paramBuffer['bufferAddr'])
     
                # Reset everything 
                
                resetListener()
                
                print("DONE!")
                                
            if Command == OPEN:
                
                # Open file
                
                print("Received OPEN.")
                
                # paramBuffer['mode'] can be 0 (RO), 1(WO), 2 (RW). See `pcdrv.h` l.52
                
                osMode = os.O_RDONLY
                
                if int(paramBuffer['mode']) == 1:
                    
                    osMode = os.O_WRONLY
                
                else:
                    
                    osMode = os.O_RDWR
                
                # ~ if os.path.isfile( 'work/' + paramBuffer['fileName']):
                
                try:
                    # Open file in osMode.
                
                    localFile = files.open( 'work/' + paramBuffer['fileName'], osMode )

                    if DEBUG:
                        
                        print("File opened. FD : " + str(localFile))

                    # Return fd.
                    
                    SendBin( b'DT' + bytes( str(localFile), 'ascii' ), paramBuffer['bufferAddr'])
                    
                # ~ else:
                except OSError as errMsg:
                    
                    SendBin( b'-1', paramBuffer['bufferAddr'])

                    print(errMsg + " - Try using PCcreate()")
                    
                    return 0
                
                resetListener()
                
                print("DONE!")
                
            if Command == CREAT:
                
                # Create and open file
                
                print("Received CREAT.")
                
                # Should we return an error if file exists ? 
                
                if not os.path.isfile( 'work/' + paramBuffer['fileName']):

                    # paramBuffer['mode'] can be 0 (RO), 1(WO), 2 (RW)
                    
                    osMode = os.O_RDONLY 
                    
                    if int(paramBuffer['mode']) == 1:
                        
                        osMode = os.O_WRONLY
                    
                    else:
                        
                        osMode = os.O_RDWR
                    
                    # We're using osMode | os.O_CREAT as open mode here.
                    
                    localFile = files.open( 'work/' + paramBuffer['fileName'], osMode | os.O_CREAT )
                    
                    if DEBUG:
                        
                        print("File created. FD : " + str(localFile))
                    
                    # Return fd.
                    
                    SendBin( b'DT' + bytes( str(localFile), 'ascii' ), paramBuffer['bufferAddr'])
                    
                else:
                
                    SendBin( b'-1', paramBuffer['bufferAddr'])

                    print("File exists ! Use PCopen.")
                
                resetListener()
                
                print("DONE!")
                
            if Command == SEEK:
                
                # Seek pos in open file
                
                print("Received SEEK.")
                
                # mode can be 0 (rel to start), 1(rel to cur pos), 2 (rel to end)
                
                # ~ fd = int( paramBuffer['fileDesc'] )
                
                fd = files.open("work/" + 'HELO.WLD', os.O_RDWR)
                
                mode = int( paramBuffer['accessMode'] )
                
                offset = int( paramBuffer['offset'] )
                
                curPos = int( paramBuffer['curPos'] )
                
                # get filesize in bytes
                
                try:

                    # fileEnd corresponds to file size in bytes
                    
                    fileEnd = os.stat(fd).st_size

                except OSError as errMsg:
                    
                    SendBin( b'-1', paramBuffer['bufferAddr'])
                    
                    print( errMsg )
                    
                    resetListener()
                    
                    return 0
                    
                # by default, use mode 0
                
                pos = offset
                
                if mode == 1:
                                    
                    pos = curPos + offset
                                
                if mode == 2:
                    
                    pos = fileEnd - offset

                # avoid overflow
                
                if pos > fileEnd:
                        
                        pos = fileEnd
                    
                if pos < 0:
                        
                        pos = 0
                
                if DEBUG :
                    
                    print( "Fd   : " + str(fd) + "\n" +
                    
                           "Mode : " + str(mode) + "\n" +
                    
                           "Ofst : " + str(offset) + "\n" +
                    
                           "curPos: "+ str(curPos) + "\n" +
                    
                           "Pos  : " + str(pos)
                    
                        )
                
                try:
                    
                    # TODO : replace os.lseek() with file.lseek
                    
                    curPos = os.lseek( fd, pos, mode )
                    
                    if DEBUG:
                        
                        print( "File seeked. CP : " + str(curPos) )
                    
                    # Return fd.
                    
                    SendBin( b'DT' + bytes( str(curPos), 'ascii' ), paramBuffer['bufferAddr'])
                
                except OSError as errMsg:
                    
                    SendBin( b'-1', paramBuffer['bufferAddr'])
                
                    print( errMsg )
                
                    resetListener()
                    
                    return 0
                    
                resetListener()
                
                print("DONE!")
                
            if Command == READ:
                
                # Read from pos in open file
                
                print("Received READ.")
                
                # ~ fd = int( paramBuffer['fileDesc'] )
                
                fd = files.open("work/" + 'HELO.WLD', os.O_RDWR)
                
                length = int( paramBuffer['length'] )
                                
                pos = int( paramBuffer['pos'] )
                
                # get filesize in bytes
                
                try:

                    # fileEnd corresponds to file size in bytes
                    
                    fileEnd = os.stat(fd).st_size

                except OSError as errMsg:
                    
                    SendBin( b'-1', paramBuffer['bufferAddr'])
                    
                    print( errMsg )
                    
                    resetListener()
                    
                    return 0
                
                if DEBUG :
                    
                    print( "Fd   : " + str(fd) + "\n" +
                    
                           "Length : " + str(length) + "\n" +
                    
                           "Pos  : " + str(pos) + "\n" +

                           "dataBuffer : " + paramBuffer['dataAddr']
                        )
                
                # Avoid overflow
                
                if pos + length > fileEnd:
                    
                    length = fileEnd - pos
                
                if pos == fileEnd:
                    
                    print("End of file reached. Doing nothing")
                    
                    SendBin( b'OKYA', paramBuffer['bufferAddr'])
                    
                    resetListener()
                    
                    return 0
                
                try:
                    
                    # TODO : replace os.pread() with file.pread
                    
                    readBytes = os.pread( fd, length, pos )
                    
                    if DEBUG:
                        
                        print( "File read. Bytes : " + str( readBytes ) )
                    
                    # Send data to data buffer
                    
                    dataSent = SendBin( readBytes, paramBuffer['dataAddr'])

                    # ~ time.sleep(sleepTime)

                    # Send OK if all went well 
                    
                    if dataSent:
                        
                        SendBin( b'OKYA', paramBuffer['bufferAddr'])
                
                except OSError as errMsg:
                    
                    SendBin( b'-1', paramBuffer['bufferAddr'])
                
                    print( errMsg )
                
                    resetListener()
                    
                    return 0
                    
                resetListener()
                
                print("DONE!")
                
            if Command == WRITE:
                
                # Write to pos in open file
                
                print("Received WRITE.")
                
                                # ~ fd = int( paramBuffer['fileDesc'] )
                
                fd = files.open("work/" + 'HELO.WLD', os.O_RDWR)
                                
                length = int( paramBuffer['length'] )
                                
                pos = int( paramBuffer['pos'] )
                
                data = paramBuffer['data']
                
                # ~ # Avoid overflow
                
                # ~ if pos + length > bufferLength:
                    
                    # ~ length = bufferLength - pos
                
                # ~ if pos == bufferLength:
                    
                    # ~ print("End of buffer reached. Doing nothing")
                    
                    # ~ SendBin( b'OKYA', paramBuffer['bufferAddr'])
                    
                    # ~ resetListener()
                    
                    # ~ return 0
                
                if DEBUG :
                    
                    print( "Fd   : " + str(fd) + "\n" +
                    
                           "Length : " + str(length) + "\n" +
                    
                           "Pos  : " + str(pos) + "\n" +

                           "data : " + data
                    
                        )
                
                try:
                    
                    # TODO : replace os.pread() with file.pread
                    
                    writeBytes = os.pwrite( fd, bytes( data, 'ascii' ), pos )
                    
                    if DEBUG:
                        
                        print( "Buffer write. Bytes : " + str( writeBytes ) )
                    
                    # Send OK if all went well 
                    
                    if writeBytes == length:
                        
                        SendBin( b'OKYA', paramBuffer['bufferAddr'])
                
                except OSError as errMsg:
                    
                    SendBin( b'-1', paramBuffer['bufferAddr'])
                
                    print( errMsg )
                
                    resetListener()
                    
                    return 0
                    
                resetListener()
                
                print("DONE!")
                
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
