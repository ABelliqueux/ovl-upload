// https://discord.com/channels/642647820683444236/646765703143227394/837416216640618558

// So like we'd have, say,

//    00            01           00            03 58 58 58                    01           xx     for pcdrv' file open to open the file name "XXX" and attribute 1

// (escape) (pcdrv command) (pcdrv open) (filename with length as prefix) (attributes) (checksum)


#pragma once

#include <sys/types.h>
#include <stdio.h>


//pcdrv commands

#define OPEN   0
#define CLOSE  1 
#define SEEK   2
#define READ   3
#define WRITE  4
#define CREATE 5
#define LOAD   6

int ptrChecksum( u_long * pointer );

int waitForSIODone( int * flag );

void PCload( u_long * loadAddress, volatile u_char * flagAddress, u_char overlayFileID );

int PCopen(const char * filename, int attributes );

int PCcreate(const char * filename, int attributes );

int PCclose( int fd );

int PCseek( int fd, int offset, int accessMode );

int PCread( int fd, int len, char * buffer );

