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

extern SVECTOR modelTri_mesh[8];

extern SVECTOR modelTri_normal[36];

extern SVECTOR modelTri_uv[144];

extern CVECTOR modelTri_color[144];

extern int modelTri_index[];

extern TMESH modelTri;

extern MESH Tri;
