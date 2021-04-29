__heap_base = MAX(__ovl0_end, __ovl1_end);

SECTIONS {            
        OVERLAY __bss_end : NOCROSSREFS SUBALIGN(4)
    {
        .ovlload
        {
            load_all_overlays_here = .;
        }
        .ovl0
        {
			KEEP(cubetex.o(.text))
			__ovl0_ctor = .;
			KEEP(cubetex.o(.text.startup._GLOBAL__*))
			KEEP(cubetex.o(.text.*))
			KEEP(cubetex.o(.rodata*))
            KEEP(cubetex.o(.sdata*))
			KEEP(cubetex.o(.data*))
            KEEP(cubetex.o(.sbss*))
			KEEP(cubetex.o(.bss*))
			KEEP(cubetex.o(.ctors))
            
			. = ALIGN(4);
			__ovl0_end = .;			
		}

        .ovl1
        {
			KEEP(tritex.o(.text))
			__ovl1_ctor = .;
			KEEP(tritex.o(.text.startup._GLOBAL__*))
			KEEP(tritex.o(.text.*))
			KEEP(tritex.o(.rodata*))
            KEEP(tritex.o(.sdata*))
			KEEP(tritex.o(.data*))
            KEEP(tritex.o(.sbss*))
			KEEP(tritex.o(.bss*))
			KEEP(tritex.o(.ctors))
			
			. = ALIGN(4);
			__ovl1_end = .;			
		}
	}
}
