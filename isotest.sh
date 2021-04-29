#!/bin/bash

make && mkpsxiso -y config/OverlayExample.xml && pcsx-redux -run -iso OverlayExample.cue
