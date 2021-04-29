
/*  ovl-upload.c, by ABelliqueux, 04-2021 license GNU General Public License v3.0
    
    This example code demonstrates how to use the companion 'ovl-upload.py' script that should be provided with this file.
    
    Once the code is loaded on a unirom enabled PSX via a serial/USB cable, 'ovl-upload.py' listens for a specific command
    
    to load an overlay file on demand. 
    
    For an explanation about overlays, see http://psx.arthus.net/sdk/Psy-Q/DOCS/TRAINING/FALL96/overlay.pdf

    For a basic example see @JaberwockySeamonstah's https://github.com/JaberwockySeamonstah/PSXOverlayExample
    
    Unirom can be found here : https://github.com/JonathanDotCel/unirom8_bootdisc_and_firmware_for_ps1
    
    with it's companion pc side software : https://github.com/JonathanDotCel/NOTPSXSerial

    Thanks to @JaberwockySeamonstah, @JonathanDotCel, @nicolasnoble, @Lameguy64 for their help and patience.
    
    Demonstrates:
    
        * Using overlays to store different data and loading them in memory as needed.
    
    Controls:
        Select                          - Load alternative overlay
*/

#include <sys/types.h>
#include <libgte.h>
#include <libgpu.h>
#include <libetc.h>
#include <stdio.h>

// If USECD is defined, files will be loaded from the CD. Use this method for testing in an emulator.
// Additionaly, generate the bin/cue with mkpsxiso.

//~ #define USECD

#ifdef USECD
    
    #include <libcd.h>

#endif

// Sample vector models

#include "tritex.h"

#include "cubetex.h"

#define VMODE       0

#define SCREENXRES 320

#define SCREENYRES 240

#define CENTERX     SCREENXRES/2

#define CENTERY     SCREENYRES/2

#define OTLEN       2048        // Maximum number of OT entries

#define PRIMBUFFLEN 32768       // Maximum number of POLY_GT3 primitives

// Display and draw environments, double buffered

DISPENV disp[2];

DRAWENV draw[2];

u_long      ot[2][OTLEN];                   // Ordering table (contains addresses to primitives)

char    primbuff[2][PRIMBUFFLEN] = {0}; // Primitive list // That's our prim buffer

//~ int         primcnt=0;                      // Primitive counter

char * nextpri = primbuff[0];                       // Primitive counter

short           db  = 0;                        // Current buffer counter

// Texture image 

extern unsigned long _binary_TIM_cubetex_tim_start[];

extern unsigned long _binary_TIM_cubetex_tim_end[];

extern unsigned long _binary_TIM_cubetex_tim_length;

TIM_IMAGE tim_cube;

// OVERLAYS CONFIG

// These symbols name are defined in 'overlay.ld', l.8, l.24 and l.41
// Use &load_all_overlays_here to get the memory adress where the overlay files are loaded.
// Those adresses you can check in the generated .map file at compile time.

extern u_long load_all_overlays_here; 

extern u_long __lvl0_end;               // Use &__lvl0_end to get end address of corresponding overlay.

extern u_long __lvl1_end;

//~ u_long overlaySize = 0;

static char* overlayFile;               // Will hold the name of the file to load.

u_char overlayFileID, loadFileIDwas, loadFileID = 0;                  // Will hold an ID that's unique for each file.

// Timer for the pad

u_short timer = 0;

// Prototypes

void init(void);

void display(void);

void LoadTexture(u_long * tim, TIM_IMAGE * tparam);

void init(){
    
    // Reset the GPU before doing anything and the controller
    PadInit(0);
    ResetGraph(0);
    
    // Initialize and setup the GTE
    InitGeom();
    SetGeomOffset(CENTERX, CENTERY);        // x, y offset
    SetGeomScreen(CENTERX);                 // Distance between eye and screen  
    
        // Set the display and draw environments
    SetDefDispEnv(&disp[0], 0, 0         , SCREENXRES, SCREENYRES);
    SetDefDispEnv(&disp[1], 0, SCREENYRES, SCREENXRES, SCREENYRES);
    
    SetDefDrawEnv(&draw[0], 0, SCREENYRES, SCREENXRES, SCREENYRES);
    SetDefDrawEnv(&draw[1], 0, 0, SCREENXRES, SCREENYRES);
    
    if (VMODE)
    {
        SetVideoMode(MODE_PAL);
        disp[0].screen.y += 8;
        disp[1].screen.y += 8;
    }
    
    setRGB0(&draw[0], 0, 0, 255);
    setRGB0(&draw[1], 0, 0, 255);

    draw[0].isbg = 1;
    draw[1].isbg = 1;

    PutDispEnv(&disp[db]);
    PutDrawEnv(&draw[db]);
        
    // Init font system
    FntLoad(960, 0);
    FntOpen(16, 16, 196, 64, 0, 256);
    
    }

void display(void){
    
    DrawSync(0);
    VSync(0);

    PutDispEnv(&disp[db]);
    PutDrawEnv(&draw[db]);

    SetDispMask(1);
    
    DrawOTag(ot[db] + OTLEN - 1);
    
    db = !db;

    nextpri = primbuff[db];
    
        
    }

void LoadTexture(u_long * tim, TIM_IMAGE * tparam){     // This part is from Lameguy64's tutorial series : lameguy64.net/svn/pstutorials/chapter1/3-textures.html login/pw: annoyingmous
        OpenTIM(tim);                                   // Open the tim binary data, feed it the address of the data in memory
        ReadTIM(tparam);                                // This read the header of the TIM data and sets the corresponding members of the TIM_IMAGE structure
        
        LoadImage(tparam->prect, tparam->paddr);        // Transfer the data from memory to VRAM at position prect.x, prect.y
        DrawSync(0);                                    // Wait for the drawing to end
        
        if (tparam->mode & 0x8){ // check 4th bit       // If 4th bit == 1, TIM has a CLUT
            LoadImage(tparam->crect, tparam->caddr);    // Load it to VRAM at position crect.x, crect.y
            DrawSync(0);                                // Wait for drawing to end
    }

}

int main() {
    
    // Update this value to avoid trigger at launch
    
    loadFileIDwas = overlayFileID = loadFileID;
    
    if ( loadFileID == 0 ){
        
        overlayFile = "\\cube.bin;1";
        
    } else if ( loadFileID == 1) {

        overlayFile = "\\tri.bin;1";
        
    }
    
    // Load overlay from CD if definde

    #ifdef USECD
    
        CdInit();
    
        int cdread = 0, cdsync = 1;
        
        cdread = CdReadFile( (char *)(overlayFile), &load_all_overlays_here, 0);
    
        cdsync = CdReadSync(0, 0);
    
    #endif
    
    int     i;

    int     PadStatus;

    int     TPressed=0;

    int     AutoRotate=1;
    
    long    t, p, OTz, Flag;                // t == vertex count, p == depth cueing interpolation value, OTz ==  value to create Z-ordered OT, Flag == see LibOver47.pdf, p.143
    
    MESH * model = &Tri;
    
    POLY_GT3 *poly = {0};                           // pointer to a POLY_GT3
    
    SVECTOR Rotate={ 0 };                   // Rotation coordinates
    VECTOR  Trans={ 0, 0, CENTERX, 0 };     // Translation coordinates
    VECTOR  Scale={ ONE, ONE, ONE, 0 };     // ONE == 4096
    MATRIX  Matrix={0};                     // Matrix data for the GTE
    
    // Texture window
    
    DR_MODE * dr_mode;                        // Pointer to dr_mode prim
    
    RECT tws = {0, 0, 32, 32};                // Texture window coordinates : x, y, w, h
                
    init();
    
    LoadTexture(_binary_TIM_cubetex_tim_start, &tim_cube);
    
    // Main loop
    while (1) {
        
        // Overlay switch
        
        if ( loadFileID != loadFileIDwas ){
            
            // Update previous file value
                         
            loadFileIDwas = loadFileID;
            
            // Change file to load
            
            switch ( loadFileID ){
    
                case 0:
                    
                    overlayFile = "\\cube.bin;1";
                    
                    overlayFileID = 0;
                    
                    break;

                case 1:

                    overlayFile = "\\tri.bin;1";
                    
                    overlayFileID = 1;
                    
                    break;
            
                default:
                
                    overlayFile = "\\cube.bin;1";
                    
                    overlayFileID = 0;
                    
                    break;
            
            }
            
            #ifdef USECD
            
                cdread = CdReadFile( (char *)(overlayFile), &load_all_overlays_here, 0);
    
                CdReadSync(0, 0);
            
            #endif
                        
        }
        
        // Pad button timer
        
        while ( timer > 0 ) { 
            
            timer --;
        
        }
        
        // Read pad status
        
        PadStatus = PadRead(0);
        
        // If select is pressed, change overlay 
        
        if (PadStatus & PADselect && !timer) {
        
            // We send the memory address where the file should be loaded, the memory address of the loadFileID, so that the screen is updated when it changes, and the file id.
        
            printf("load:%p:%08x:%d", &load_all_overlays_here, &loadFileID, overlayFileID);
        
            #ifdef USECD
            
              // We can do that because we only have two files
            
              loadFileID = !loadFileID;
            
            #endif
            
            timer = 30;

        }

        if (AutoRotate) {

            Rotate.vy += 8; // Pan

            Rotate.vx += 8; // Tilt
        }
        
        
        // Clear the current OT
        
        ClearOTagR(ot[db], OTLEN);
        
        // Convert and set the matrixes
        
        RotMatrix(&Rotate, &Matrix);
        
        TransMatrix(&Matrix, &Trans);
        
        ScaleMatrix(&Matrix, &Scale);
        
        SetRotMatrix(&Matrix);
        
        SetTransMatrix(&Matrix);
        
        
        // Render the sample vector model
        t=0;
        
        // modelCube is a TMESH, len member == # vertices, but here it's # of triangle... So, for each tri * 3 vertices ...
        
        for (i = 0; i < (model->tmesh->len*3); i += 3) {               
            
            poly = (POLY_GT3 *)nextpri;
            
            // Initialize the primitive and set its color values
            
            SetPolyGT3(poly);

            ((POLY_GT3 *)poly)->tpage = getTPage(tim_cube.mode&0x3, 0,
                                                 tim_cube.prect->x,
                                                 tim_cube.prect->y
                                                );

            setRGB0(poly, model->tmesh->c[i].r ,  model->tmesh->c[i].g  , model->tmesh->c[i].b);
            setRGB1(poly, model->tmesh->c[i+1].r, model->tmesh->c[i+1].g, model->tmesh->c[i+1].b);
            setRGB2(poly, model->tmesh->c[i+2].r, model->tmesh->c[i+2].g, model->tmesh->c[i+2].b);

            setUV3(poly, model->tmesh->u[i].vx  , model->tmesh->u[i].vy,
                         model->tmesh->u[i+1].vx, model->tmesh->u[i+1].vy,
                         model->tmesh->u[i+2].vx, model->tmesh->u[i+2].vy);
                         
            // Rotate, translate, and project the vectors and output the results into a primitive

            OTz  = RotTransPers(&model->tmesh->v[model->index[t]]  , (long*)&poly->x0, &p, &Flag);
            OTz += RotTransPers(&model->tmesh->v[model->index[t+1]], (long*)&poly->x1, &p, &Flag);
            OTz += RotTransPers(&model->tmesh->v[model->index[t+2]], (long*)&poly->x2, &p, &Flag);
            
            // Sort the primitive into the OT
            OTz /= 3;
            if ((OTz > 0) && (OTz < OTLEN))
                AddPrim(&ot[db][OTz-2], poly);
            
            nextpri += sizeof(POLY_GT3);
            
            t+=3;
            
        }
        
            dr_mode = (DR_MODE *)nextpri;
            
            setDrawMode(dr_mode,1,0, getTPage(tim_cube.mode&0x3, 0,
                                              tim_cube.prect->x,
                                              tim_cube.prect->y), &tws);  //set texture window
        
            AddPrim(&ot[db], dr_mode);
            
            nextpri += sizeof(DR_MODE);
        

        FntPrint("Hello overlay!\n");
        
        #ifndef USECD
        
        FntPrint("Overlay with id %d loaded at 0x%08x", overlayFileID, &load_all_overlays_here);
        
        #endif
        
        #ifdef USECD
    
            FntPrint("File: %s\n", overlayFile);
            
            FntPrint("Bytes read: %d", cdread);
    
        #endif
        
        FntFlush(-1);
        
        display();

    }
    return 0;
}
