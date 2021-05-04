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

pcdrvCommand  = '06'

# Names of the overlay files to load.
# See l.550

overlayFile0 = "Overlay.ovl0" 

overlayFile1 = "Overlay.ovl1"

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

memAddr = ""

flagAddr = ""

loadFile = -1

levelId  = ""

# One byte

#uno = int(1).to_bytes(1, byteorder='little', signed=False)

data = 0

# checkSum is the checkSum for the full data

checkSum = 0

# If set, it means the data transfer has been initiated 

Transfer = 0

# Delay between write operations. These seem to be needed for the connection not to hang.

sleepTime = 0.08    # Seems like safe minimum

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
# TODO : fixit to have the same results as https://github.com/grumpycoders/pcsx-redux/blob/main/src/mips/common/util/djbhash.h

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
        
        if DEBUG > 1:
            
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
    
    WriteBytes( inData )

def resetListener():
    
    global checkSum, data, Listen, Transfer, dataSize, memAddr, loadFile, flagAddr, levelId
    
    memAddr = ""

    flagAddr = ""
    
    loadFile = ""
    
    checkSum = 0
    
    data = 0
    
    dataSize = 0
    
    Transfer = 0
    
    levelId  = 0
    
    Listen = 1

    ser.reset_input_buffer()
    
    ser.reset_output_buffer()
    
def main(args):
    
    while True:
    
        global checkSum, data, Listen, Transfer, dataSize, memAddr, loadFile, flagAddr, levelId
        
        # Flush serial buffers to avoid residual data
        
        ser.reset_input_buffer()
        
        ser.reset_output_buffer()
        
        inputBuffer = ""
            
        # Listen to incomming connections on serial
        
        if Listen:

            print("Listening for incoming data...")
            
            if DEBUG  > 1:
            
                print("memAddr : " + str(memAddr) + " - loadFile" + loadFile )
            
            while True:

                # If data on serial, fill buffer
                
                while ser.in_waiting:
                    
                    inputBuffer += ser.read().decode('ascii')

                    if DEBUG > 2:
                            
                        print( "Raw data : " + inputBuffer )
                
                if inputBuffer:
                
                    # We're expecting the command with format : 00 01 06 08 xx xx xx xx 08 xx xx xx xx 01 xx xx (16 bytes) 
                        
                    if len(inputBuffer) == 38:
                    
                        if DEBUG:
                            
                            print( "Incoming data : " + inputBuffer )
                    
                        # Get the checksum and remove it from the buffer
                    
                        CmdCheckSum = inputBuffer[-10:]
                        
                        if DEBUG:
                                    
                            print( "Received ChkSm: " + CmdCheckSum )
                            
                        # Remove checksum from data

                        inputBuffer = inputBuffer[:28]

                        dataCheckSum = hash_djb2(bytes(inputBuffer, 'ascii'))

                        if DEBUG:
                                    
                            print( "Computed ChkSm: " + str(dataCheckSum) )
                        
                        # Not using the checksum for now
                        
                        # ~ dataCheckSum = 0
                        
                        # ~ CmdCheckSum = 0
                        
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
                                    
                                    if inputBuffer[:2] == pcdrvCommand:
                                                                    
                                        if DEBUG:
                                        
                                            print( "Received Cmd: " + inputBuffer[:2] )

                                        # Command byte is valid (06), remove it from buffer and continue
                                        
                                        inputBuffer = inputBuffer[2:]
                                        
                                        dataInBuffer = inputBuffer
                                        
                                        if DEBUG:
                                        
                                            print( "Data in buffer: " + dataInBuffer )
                                        
                                            dataLen = 0
                                            
                                            # Get data length byte
                                            
                                            dataLen = dataInBuffer[:2]
                                            
                                            dataInBuffer = dataInBuffer[2:]
                                            
                                            # Get actual data
                                            
                                            for b in dataInBuffer :
                                            
                                                if len(memAddr) < int(dataLen) :
                                                    
                                                    memAddr += b
                                            
                                            # Remove data from buffer
                                            
                                            dataInBuffer = dataInBuffer[int(dataLen):]
                                            
                                            if DEBUG > 1:
                                        
                                                print( "Data in buffer 1: " + dataInBuffer )
                                            
                                            dataLen = 0
                                            
                                            dataLen = dataInBuffer[:2]
                                            
                                            dataInBuffer = dataInBuffer[2:]
                                            
                                            # Get actual data
                                            
                                            for b in dataInBuffer :
                                            
                                                if len(flagAddr) < int(dataLen) :
                                                    
                                                    flagAddr += b
                                            
                                            # Remove data from buffer
                                            
                                            dataInBuffer = dataInBuffer[int(dataLen):]
                                            
                                            if DEBUG > 1:
                                        
                                                print( "Data in buffer 2: " + dataInBuffer )
                                            
                                            # We should only have two bytes remaining
                                            
                                            if len(dataInBuffer) == 2:
                                                
                                                loadFile = int(dataInBuffer)
                                            
                                            if DEBUG:
                                        
                                                print( memAddr + " - " + flagAddr + " - " + str(loadFile) )

                                            ser.reset_input_buffer()
                                
                                            inputBuffer = ""
                                            
                                            Listen = 0
                                            
                                            break
                        else:
                            
                            print("Command checksum not matching ! Aborting...")
                            
                            ser.reset_input_buffer()
                        
                            inputBuffer = ""
                            
                            break
                                                            
                    else:
                        
                        ser.reset_input_buffer()
                        
                        inputBuffer = ""
                        
                        break
        
        if memAddr and flagAddr:
        
            # Remove separator and ';1' at end of the string
        
            # ~ fileClean = loadFile.split(';')[0][1:]
            fileID = loadFile

            print("Received addresses and file ID : " + memAddr + " - " + flagAddr + " - " + str(fileID))
            
            # TODO : replace with a proper level naming scheme
            # right now, we're receiving currently loaded file
            # so we have to switch manually here.
            
            binFileName = ""
            
            if fileID == 0:
            
                binFileName = overlayFile1
            
                levelId     = 1
            
            if fileID == 1:
                
                binFileName = overlayFile0
            
                levelId     = 0
            
            if DEBUG:

                print(
                
                    "Load Data to : " + memAddr + "\n" +
                    
                    "Reset flag at: " + flagAddr + "\n" +
                    
                    "FileID   : " + str(loadFile) + "\n" +
                    
                    "Bin    : " + binFileName + " - ID : " + str(levelId)
            
                     )
            
            # Open file as binary if bin filename is defined
            
            if binFileName:

                binFile = open( dataFolder + binFileName, 'rb' )
            
                data = binFile.read()
            
                Transfer = 1
            
            else:
                
                print(" No filename provided, doing nothing ")
                
                resetListener()
        
        # If Init was set, initialize transfer and send data
        
        if Transfer:
            
            print("Initializing data transfer...")
            
            if not uniDebugMode:
            
                # Set unirom to debugmode - sent : "DEBG" - received : "DEBGOKAY"
            
                setDEBG()
            
            # Send level data
            
            SendBin( data, memAddr )

            # Set level changed flag 
            
            if DEBUG:
                
                print("Sending value " + str( levelId.to_bytes(1, byteorder='little', signed=False) ) + " to " + flagAddr )
            
            time.sleep( sleepTime )
            
            SendBin( levelId.to_bytes(1, byteorder='little', signed=False) , flagAddr)
            
            # Reset everything 
            
            resetListener()
            
            print("DONE!")
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
