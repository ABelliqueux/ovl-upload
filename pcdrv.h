// https://discord.com/channels/642647820683444236/646765703143227394/836663602718048297
// 28-04-2021 - @nicolasnoble:
//
// step 0  : have a protocol that can handle open / close / seek / read / write
//
// step 1  : have an unhandled exception handler installed in the kernel to capture the pcdrv functions; that sounds scary, but it's extremely straightforward (I think @sickle currently has one for his debugger)
//
// step 1.5: implement the pcopen / pcclose / pcread / pcwrite / pcseek functions, which are basically the same model as my syscalls.h file
//
// step 2  : implement the unhandler exception handler in a way that properly redirects the calls to the step 0 protocol, and returns gracefully to the caller when done - that can be a bit tricky, but it's totally doable
//   this step requires understanding the ReturnFromException mechanism basically which, to be fair, is sort of understandable from this one file: 
//   https://github.com/grumpycoders/pcsx-redux/blob/main/src/mips/openbios/handlers/syscall.c
//   you can see the syscall_unresolvedException() call at the bottom , this just needs to follow the same pattern
//   and break down the caller, modify the current thread's registers, and return to the caller
//   at this point, we have a working basic pcdrv feature, using pcopen / pcclose / pcread / pcwrite / pcseek
//
// step 3  : add a kernel driver for "pcdrv:" that just piggy backs on pc* functions so that people can simply do a int file = open("pcdrv:blah.txt", O_RDONLY);
//   (and thus support things like CSOTN technically)
//
// https://discord.com/channels/642647820683444236/646765703143227394/837416216640618558
// So like we'd have, say,
//    00            01           00            03 58 58 58                    01           xx     for pcdrv' file open to open the file name "XXX" and attribute 1
// (escape) (pcdrv command) (pcdrv open) (filename with length as prefix) (attributes) (checksum)
#pragma once
#include <sys/types.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
//~ #include <libsio.h>
#include <string.h>
#define BUFFER_LEN 8
#define ESCAPE 0x00     // Hypothetical Escape char for unirom
#define PROTOCOL 0x01
//pcdrv commands
#define OPEN   0x00
#define CLOSE  0x01
#define SEEK   0x02
#define READ   0x03
#define WRITE  0x04
#define CREATE 0x05
#define LOAD   0x06
#define INIT   0x07
// flags parameters
#define O_RDONLY 0x00
#define O_WRONLY 0x01
#define O_RDWR   0x02
#define CHECKSUM_LEN 10
//~ static char sio_read();
int waitForSIODone( const char * answer, volatile char * bufferAddress);
static inline uint32_t djbHash( const char* str, unsigned n );
static inline uint32_t djbProcess(uint32_t hash, const char str[], unsigned n);
//~ uint32_t charsToU32 ( char * byte );
//~ u_char U32ToChars( u_int memoryAddress, u_int byteNbr);
//~ void sendU32(uint32_t data);
//~ void sendRU32(uint32_t data);
u_short PCload( u_long * loadAddress, volatile u_char * bufferAddress, u_char * overlayFileID );
int PCinit( volatile u_char * bufferAddress );
int PCclose( int fileDesc, volatile u_char * bufferAddress );
int PCopen( const char * filename, u_char mode, volatile u_char * bufferAddress );
int PCcreate( const char * filename, u_char mode, volatile u_char * bufferAddress );
int PCseek( int fd, int curPos, int offset, int accessMode, volatile u_char * bufferAddress );
int PCread( int fd,  int pos, int len, volatile char * dataBuffer, volatile char * bufferAddress );
int PCwrite( int fd,  int pos, int len, volatile u_char * dataBuffer, volatile u_char * bufferAddress );
