ROOT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))

export DESIGN_NAME     	= exploration

export VERILOG_FILES 	= $(ROOT_DIR)/exploration.v
export SDC_FILE      	= $(ROOT_DIR)/constraints.sdc
export FOOTPRINT_TCL = $(ROOT_DIR)/pads.tcl
export MACRO_PLACE_TCL = $(ROOT_DIR)/macros.tcl
export DIE_AREA    	 	= 0 0 2560 1600
export CORE_AREA   	 	= 0 0 2550 1590

