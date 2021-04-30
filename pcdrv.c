#include "pcdrv.h"

int ptrChecksum( u_long * pointer ){

    u_int checksum = 0;
    
    u_long work;

    work = ( u_long ) pointer - 0x80000000 ;

    while( work != 0 ){    

        checksum += work % 10;

        work /= 10;
    }
    
    return checksum;

};

int waitForSIODone( int * flag ){
    
    // This should wait for a signal from the SIO to tell when it's done 
    // Returns val < 0 if wrong
    
    uint timeOut = 1000;
    
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
  
  u_char cmdChecksum = 0; // Not using that yet, ideally, should allow to check that the received command on the pc is the same as the one sent by the psx

  printf("%02u%02u%02u08%08x08%08x%02u%04u", escape, protocol, LOAD, loadAddress, flagAddress, overlayFileID, cmdChecksum);
  
};
