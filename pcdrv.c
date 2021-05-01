#include "pcdrv.h"

int doChecksum( u_long * pointer ){

    u_int checksum = 0;
    
    u_long work;

    work = ( u_long ) pointer - 0x80000000 ;

    while( work != 0 ){

        checksum += work % 10;

        work /= 10;
    }
    
    return checksum;

};

// Hashing algorythm from @nicolasnoble : https://github.com/grumpycoders/pcsx-redux/blob/main/src/mips/common/util/djbhash.h

static inline uint32_t djbProcess(uint32_t hash, const char str[], unsigned n) {
    
    return n ? djbProcess ( ( ( hash << 5 ) + hash ) ^ str[0], str + 1, n - 1) : hash;
}

static inline uint32_t djbHash( const char* str, unsigned n ){
    
     return djbProcess( 5381, str, n);
     
};

int waitForSIODone( int * flag ){
    
    // This should wait for a signal from the SIO to tell when it's done 
    // Returns val < 0 if wrong
    
    uint16_t timeOut = 1000;
    
    char result  = 0;
    
    for ( uint t = 0; t < timeOut; t ++){
        
        if ( * flag == 1 ){
     
            result = * flag;
            
            break;
        }
        
    }
    
    return result;

};

void PCload( u_long * loadAddress, volatile u_char * flagAddress, u_char overlayFileID ) {
    
  // Send filename , load address, and flag address
  
  u_char escape   = 0;     // Hypothetical Escape char for unirom

  u_char protocol = 1;     // Hypothetical protocol indicator for unirom
  
  //~ u_char cmdChecksum = 0; // Not using that yet, ideally, should allow to check that the received command on the pc is the same as the one sent by the psx

  char commandBuffer[28];

  sprintf(commandBuffer, "%02u%02u%02u08%08x08%08x%02u", escape, protocol, LOAD, loadAddress, flagAddress, overlayFileID);

  u_int cmdChecksum = djbHash(commandBuffer, 28);
  
  printf("%s%10u", commandBuffer, cmdChecksum);
  
};
