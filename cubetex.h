#pragma once

#include <sys/types.h>
#include <libgte.h>
#include <libgpu.h>

#ifndef custom_types

typedef struct MESH {
    
    TMESH * tmesh;
    
    int * index;
    
    } MESH;

#define custom_types

#endif


extern SVECTOR modelCube_mesh[8];

extern SVECTOR modelCube_normal[36];

extern SVECTOR modelCube_uv[144];

extern CVECTOR modelCube_color[144];

extern int modelCube_index[];

extern TMESH modelCube;

extern MESH Cube;
