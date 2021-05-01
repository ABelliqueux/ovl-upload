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
#include <stdio.h>


//pcdrv commands

#define OPEN   0
#define CLOSE  1 
#define SEEK   2
#define READ   3
#define WRITE  4
#define CREATE 5
#define LOAD   6

static inline uint32_t djbHash( const char* str, unsigned n );

static inline uint32_t djbProcess(uint32_t hash, const char str[], unsigned n);

int doChecksum( u_long * pointer );

int waitForSIODone( int * flag );

void PCload( u_long * loadAddress, volatile u_char * flagAddress, u_char overlayFileID );

int PCopen(const char * filename, int attributes );

int PCcreate(const char * filename, int attributes );

int PCclose( int fd );

int PCseek( int fd, int offset, int accessMode );

int PCread( int fd, int len, char * buffer );

