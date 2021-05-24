#include "pcdrv.h"
void wait(){
    for(u_int wait = 0; wait < 60; wait++){
        wait = wait;
    }
};
/*
static char sio_read(){
    char c;
    c = getchar();
    return c;
};
u_int strLen( const char * str){
  u_int l = 0;
  while ( * str++ ){
      l++;
  }
  return l;
};
*/
// Hashing algorythm from @nicolasnoble : https://github.com/grumpycoders/pcsx-redux/blob/main/src/mips/common/util/djbhash.h
static inline uint32_t djbProcess(uint32_t hash, const char str[], unsigned n) {
    return n ? djbProcess ( ( ( hash << 5 ) + hash ) ^ str[0], str + 1, n - 1) : hash;
}
static inline uint32_t djbHash( const char* str, unsigned n ){
     return djbProcess( 5381, str, n);
};
/*
uint32_t charsToU32 ( char * byte ) {
  unsigned int packet = (byte[0] << 24) | (byte[1] << 16) | (byte[2] << 8) | (byte[3]);
  return packet;
};
u_char U32ToChars(  u_int memoryAddress, u_int byteNbr){
    // This one I found on my own )'u'(
    u_char byte = { 0 };
    byte = ( (u_int) memoryAddress >> ( 24 - (byteNbr << 3) ) ) & 0xFF;
    return byte;
};
void sendU32(uint32_t data) {
  putchar(data & 0xff);
  data >>= 8;
  putchar(data & 0xff);
  data >>= 8;
  putchar(data & 0xff);
  data >>= 8;
  putchar(data & 0xff);
};
void sendRU32(uint32_t data) {
  putchar((data >> 24) & 0xff);
  putchar((data >> 16) & 0xff);
  putchar((data >> 8) & 0xff);
  putchar(data & 0xff);
};
*/
int waitForSIODone( const char * answer, volatile char * bufferAddress){
    // This watches the buffer at &bufferAddress and waits for it to contain the first two chars of answer,
    // which is sent by the server when PC->PSX data upload is over.
    // If answer is OK, act as ACK. If answer is DT, the next 2 chars contains data.
    // Returns 1 if ok, 0 else.
    // Return value
    int SIOdone = 0;
    // Error code sent by the PC
    const char * error = "-1";
    // Mini buffer for the data when two first chars are DT
    char returnValue[BUFFER_LEN] = {0};
    // Counter to avoid infinite loop
    int i = 0;
    while(1){
        // Continually get the content at &bufferAddress
        const char * buffer = ( const char * )bufferAddress;
        // Rolling buffer
        if( strlen( buffer ) > BUFFER_LEN){
            memmove( ( char * ) buffer, buffer + 1, strlen(buffer));
        }
        // Check inBuffer for answer
        // If buffer does not contain "-1"
        if ( buffer[0] != error[0] && buffer[1] != error[1] ){
            // If two first chars == answer
            if( (buffer[0] == answer[0]) &&
                (buffer[1] == answer[1]) ){                                 // "DT369000"
                memmove( ( char * ) buffer, buffer + 2, strlen(buffer));    // "36900000"
                //~ returnValue[0] = buffer[0];
                //~ returnValue[1] = buffer[1];
                for(short i = 0; i < BUFFER_LEN; i++){                      // "00000000" > 
                    returnValue[i] = buffer[i];
                }
                //~ returnValue[0] = buffer[2];
                //~ returnValue[1] = buffer[3];
                //~ returnValue[2] = buffer[4];
                // Get data as int
                SIOdone = atoi(returnValue);
                // Empty buffer
                for (short i; i < BUFFER_LEN; i++ ){ bufferAddress[i] = 0; }
                // Return data
                return SIOdone;
            }
        } else {
            return -1;
        }
        i++;
        // Avoid infinite loop
        if ( i > 3000 ){
            // empty buffer
            for ( short i; i < BUFFER_LEN;i++ ){ bufferAddress[i] = 0; }
            // Get out of function after X iterations
            return 0;
        }
    }
    // Should never be reached, but just to be sure
    return 0;
};
u_short PCload( u_long * loadAddress, volatile u_char * bufferAddress, u_char * overlayFileID ) {
  // Send filename , load address, and flag address
  // Returns 1 if ok, 0 else
  // E.G : 00 01 06 04 80010000 08 80010001 01 + 0000000000 <- cmd checksum
  //       00 01 06 08 8003edf8 08 8001f0f0 00   2439964735 -> 38 Bytes
    // Expected answer
    const char * answer = "OK";
    // Using hardcoded length of 28 B 
    char commandBuffer[28];
    // pointer is 4 B, but represented here by 8 B / chars. 
    u_short addLenInChar = sizeof(loadAddress) * 2;
    sprintf(commandBuffer, "%02u%02u%02u%02u%08x%02u%08x%02u", ESCAPE, PROTOCOL, LOAD, addLenInChar, loadAddress, addLenInChar, bufferAddress, *overlayFileID);
    u_int cmdChecksum = djbHash(commandBuffer, 28);
    printf("%s%*u", commandBuffer, CHECKSUM_LEN, cmdChecksum);
    // Need delay ?
    wait();
    return waitForSIODone( answer , bufferAddress );
};
int PCinit( volatile u_char * bufferAddress ){
    // Close all the files on the PC.
    // Returns OK if success, -1 if fail
    // E.G : 00 01 07 + 00 00 00 00 00
    const char * answer = "OK";
    u_int bufferLen = 16;
    char commandBuffer[ bufferLen ];
    sprintf(commandBuffer, "%02u%02u%02u08%08x", ESCAPE, PROTOCOL, INIT, bufferAddress);
    u_int cmdChecksum = djbHash( commandBuffer, bufferLen);
    printf("%s%*u", commandBuffer, CHECKSUM_LEN, cmdChecksum);
    wait();
    return waitForSIODone( answer, bufferAddress );
};
int PCclose( int fileDesc, volatile u_char * bufferAddress ){
    // Close file corresponding to fileDesc  
    // Returns OK if success, -1 if fail
    // E.G : 00 01 01 16 + 00 00 00 00 00
    const char * answer = "OK";
    u_int bufferLen = 8;
    char commandBuffer[ bufferLen ];
    sprintf(commandBuffer, "%02u%02u%02u%02u", ESCAPE, PROTOCOL, CLOSE, fileDesc);
    u_int cmdChecksum = djbHash( commandBuffer, bufferLen);
    printf("%s%*u", commandBuffer, CHECKSUM_LEN, cmdChecksum);
    wait();
    return waitForSIODone( answer, bufferAddress );
};
int PCopen( const char * filename, u_char mode, volatile u_char * bufferAddress ){
    // Open filename in mode 
    // Returns file descriptor or -1 if fail
    // Mode can be 00 (RO), 01(WO), 02 (RW) (see pcdrv.h, l.52)
    // E.G : 00 01 00 08 48454C4F 00 + 0000000000 <- cmd checksum 18 + CHECKSUM_LEN B
    // Expected answer DaTa + 2 chars of data
    const char * answer = "DT";
    // Should we allow names > 8 chars ? If so, use strlen() to determine buffer length
    u_int bufferLen = 20 + strlen( filename ); // else use a length of 28
    u_short addLenInChar = sizeof(bufferAddress) * 2;
    char commandBuffer[ bufferLen ];
    sprintf(commandBuffer, "%02u%02u%02u%02u%*s%02u%08x%02u", ESCAPE, PROTOCOL, OPEN, strlen( filename ), strlen( filename ), filename, addLenInChar, bufferAddress, mode);
    u_int cmdChecksum = djbHash( commandBuffer, bufferLen);
    printf("%s%*u", commandBuffer, CHECKSUM_LEN, cmdChecksum);
    wait();
    return waitForSIODone( answer, bufferAddress );
};
int PCcreate( const char * filename, u_char mode, volatile u_char * bufferAddress ){
    // Create and open file with filename in mode 
    // Returns file descriptor or -1 if fail
    // Mode can be 00 (RO), 01(WO), 02 (RW) (see pcdrv.h, l.52)
    // E.G : 00 01 00 08 48454C4F 00 + 0000000000 <- cmd checksum 18 + CHECKSUM_LEN B
    // Expected answer DaTa + 2 chars of data
    const char * answer = "DT";
    u_int bufferLen = 20 + strlen( filename ); 
    u_short addLenInChar = sizeof(bufferAddress) * 2;
    char commandBuffer[ bufferLen ];
    sprintf(commandBuffer, "%02u%02u%02u%02u%*s%02u%08x%02u", ESCAPE, PROTOCOL, CREATE, strlen( filename ), strlen( filename ), filename, addLenInChar, bufferAddress, mode);
    u_int cmdChecksum = djbHash( commandBuffer, bufferLen);
    printf("%s%*u", commandBuffer, CHECKSUM_LEN, cmdChecksum);
    wait();
    return waitForSIODone( answer, bufferAddress );
};
int PCseek( int fd, int curPos, int offset, int accessMode, volatile u_char * bufferAddress ){
    // Seek offset in file
    // Return new position or -1 if fail
    // accessMode can be relative to start : 0 , relative to current pos : 1 , relative to end of file : 2
    // E.G : 00 01 02 02 09 08 00000000 08 00000369 08 80025808 01 1907502951
    const char * answer = "DT";
    u_int bufferLen = 42; // Will we need file desc > 99 ?
    char commandBuffer[ bufferLen ];
    sprintf(commandBuffer, "%02u%02u%02u02%02u08%08d08%08d08%08x%02u", ESCAPE, PROTOCOL, SEEK, fd, curPos, offset, bufferAddress, accessMode);
    u_int cmdChecksum = djbHash( commandBuffer, bufferLen);
    printf("%s%*u", commandBuffer, CHECKSUM_LEN, cmdChecksum);
    wait();
    return waitForSIODone( answer, bufferAddress );
};
int PCread( int fd, int pos, int len, volatile char * dataBuffer, volatile char * bufferAddress ){
    // Read and returns len bytes at pos on file fd 
    // Send read bytes to dataBuffer
    // Return OK or -1 if fail
    // E.G : 00 01 03 02 88 08 00000369 08 00000016 08 80025808 08 80025848 1841163114
    const char * answer = "OK";
    u_int bufferLen = 50;
    char commandBuffer[ bufferLen ];
    sprintf(commandBuffer, "%02u%02u%02u02%02u08%08d08%08d08%08x08%08x", ESCAPE, PROTOCOL, READ, fd, pos, len, dataBuffer, bufferAddress);
    u_int cmdChecksum = djbHash( commandBuffer, bufferLen);
    printf("%s%*u", commandBuffer, CHECKSUM_LEN, cmdChecksum);
    wait();
    return waitForSIODone( answer, bufferAddress );
};
int PCwrite( int fd, int pos, int len, volatile u_char * dataBuffer, volatile u_char * bufferAddress ){
    // Send len bytes from dataBuffer to be written in file fd at pos
    // Return OK or -1 if fail
    // E.G : 00 01 04 02 88 08 00000000 08 00000016 16 ALLEZONYVALESENF 08 80025808 4060903934
    const char * answer = "OK";
    // Add space for null terminator
    u_char tempBuffer[len + 1];
    // Fill tempBuffer with data at dataBuffer
    for( int b = 0; b < len; b++ ){
        tempBuffer[b] = dataBuffer[b];
    }
    // Set null terminator
    tempBuffer[len] = 0;
    u_int bufferLen = 42 + len;
    char commandBuffer[ bufferLen ];
    sprintf(commandBuffer, "%02u%02u%02u02%02u08%08d08%08d%02u%*s08%08x", ESCAPE, PROTOCOL, WRITE, fd, pos, len, len, len, tempBuffer, bufferAddress);
    u_int cmdChecksum = djbHash( commandBuffer, bufferLen);
    printf("%s%*u", commandBuffer, CHECKSUM_LEN, cmdChecksum);
    wait();
    return waitForSIODone( answer, bufferAddress );
};
// WIP : Build command for use with putchar instead of printf
/*
void BuildCmd(){
    // Build command in the buffer
    u_char escape   = 0x00;     // Hypothetical Escape char for unirom
    u_char protocol = 0x01;     // Hypothetical protocol indicator for unirom
    // Command is 18 B data + 10 B checksum
    char commandBuffer[28] = {0};
    u_char checkSumLen = 10;
    short i = 0;
    u_long * loadAddress;
    u_char * flagAddress;
    // FntPrint("%x\n", loadAddress);
    while( i < sizeof( commandBuffer) - checkSumLen ){
        if( i == 0 ){
            commandBuffer[0] = escape;
            commandBuffer[1] = protocol;
            i = 2;
        }
        if( i == 2 ){
            commandBuffer[i] = LOAD;
            i ++;
        }
        commandBuffer[i] = sizeof(&loadAddress);
        i ++;
        for( u_int b = 0; b < sizeof(&loadAddress); b++ ){
            commandBuffer[i] = U32ToChars( ( u_int ) loadAddress, b );
            // FntPrint("i: %d b: %d, %02x\n", i, b, commandBuffer[i]);
            i++;
        }
        commandBuffer[i] = sizeof(&flagAddress);
        i ++;
        for( u_int b = 0; b < sizeof(&flagAddress); b++ ){
            commandBuffer[i] = U32ToChars( ( u_int ) flagAddress, b );
            // FntPrint("i: %d b: %d, %02x\n", i, b, commandBuffer[i]);
            i++;
        }
        // commandBuffer[i] = overlayFileID;
        i++;
        for(short c = 0; c < sizeof(commandBuffer) - checkSumLen; c++){
            // FntPrint("%x", commandBuffer[c]);
        }
        // FntPrint("\n%d, %d", i, sizeof(commandBuffer) );
    }
    for(u_int b = 0; b < sizeof(commandBuffer)-3; b+=4 ){
        u_char bytes[4] = {0};
        bytes[0] = commandBuffer[b + 0];
        bytes[1] = commandBuffer[b + 1];
        bytes[2] = commandBuffer[b + 2];
        bytes[3] = commandBuffer[b + 3];
        sendU32( charsToU32(bytes) );
    }
    // u_int cmdChecksum = djbHash((const char * )commandBuffer, sizeof(commandBuffer) - checkSumLen);
    // FntPrint("\n%d\n", cmdChecksum);
}
*/
