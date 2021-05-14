#include "pcdrv.h"

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

// Hashing algorythm from @nicolasnoble : https://github.com/grumpycoders/pcsx-redux/blob/main/src/mips/common/util/djbhash.h

static inline uint32_t djbProcess(uint32_t hash, const char str[], unsigned n) {
    
    return n ? djbProcess ( ( ( hash << 5 ) + hash ) ^ str[0], str + 1, n - 1) : hash;
}

static inline uint32_t djbHash( const char* str, unsigned n ){
    
     return djbProcess( 5381, str, n);
     
};

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

u_short waitForSIODone( volatile u_char * bufferAddress){
    
    // This should wait for a signal from the SIO to tell when it's done 
    // Returns 1 if ok, 0 else
    
    const char * OKYA = "OKYA";
    
    u_char SIOdone = 0;
    
    int i = 0;
    
    while(1){
    
        const u_char * buffer = ( const u_char * )bufferAddress;
    
        // Rolling buffer

        if( strlen( buffer ) > 4){

            memmove( ( u_char * ) buffer, buffer + 1, strlen(buffer));

        }

        // Check inBuffer for answer

        if( strcmp(buffer, OKYA) == 0 ){
            
            FntPrint("WORX!\n\n");
            
            SIOdone = 1;
        
            break;
            
        }
            
        i++;
        
        // Avoid infinite loop
        
        if ( i > 10000 ){
        
            break;
            
        }
        
    }
    
    return SIOdone;

};

u_short PCload( u_long * loadAddress, volatile u_char * bufferAddress, u_char * overlayFileID ) {
    
  // Send filename , load address, and flag address
  // E.G : 00 01 06 04 8001000 04 80010001 01 + 0000000000 <- cmd checksum
  
    char commandBuffer[28];

    sprintf(commandBuffer, "%02u%02u%02u08%08x08%08x%02u", ESCAPE, PROTOCOL, LOAD, loadAddress, bufferAddress, *overlayFileID);

    u_int cmdChecksum = djbHash(commandBuffer, 28);

    printf("%s%10u", commandBuffer, cmdChecksum);

    // Need delay ?

    for(u_int wait = 0; wait < 100; wait++){
        
        wait = wait;
        
    }

    if( waitForSIODone(bufferAddress) ) {

        *overlayFileID = !*overlayFileID;
        
    };

};


int PCopen( const char * filename, u_char mode ){

  // Open filename in mode 
  // Returns file descriptor or -1 if fail
  // E.G : 00 01 00 04 48454C4F 00 + 0000000000 <- cmd checksum

  u_int bufferLen = 10 + strLen( filename );
  
  char commandBuffer[ bufferLen ];

  sprintf(commandBuffer, "%02u%02u%02u%02u%s%02u", ESCAPE, PROTOCOL, OPEN, bufferLen, filename, mode);

  u_int cmdChecksum = djbHash( commandBuffer, bufferLen);
  
  printf("%s%10u", commandBuffer, cmdChecksum);

}


// WIP : Build command for use with putchar instead of printf

void BuildCmd(){
    //~ // Build command in the buffer

    u_char escape   = 0;     // Hypothetical Escape char for unirom

    u_char protocol = 1;     // Hypothetical protocol indicator for unirom

    //~ // Command is 14 B data  + 5 B checksum

    u_char commandBuffer[19] = {0};

    u_char checkSumLen = 5;

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
        
        //~ commandBuffer[i] = overlayFileID;
        
        i++;
        
        for(short c = 0; c < sizeof(commandBuffer) - checkSumLen; c++){
            
            //~ FntPrint("%x", commandBuffer[c]);
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
