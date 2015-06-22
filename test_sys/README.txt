

---------------------------------------
Author: C. Hättich (feddischson@gmx.com)
Date: 22 June 2015
---------------------------------------

Introduction
============
A simple test system is used to test the YAC core on a 
Spartan 3an starter kit (Xilinx). This test system
is based on a or32 CPU with some on-chip ram and an uart.

The system is created with the tool
soc_maker (see https://github.com/feddischson/soc_maker),
which takes the configuration file test_sys.yaml and generates
all the required files.
The result is placed in ./build.

The software contains two parts, a PC part and a embedded part.
Both are build with SCons (see www.scons.org), 
a replacement for make. 

The PC part creates test patterns and sends them to the test-system
on the FPGA. The test system calculates the CORDIC result and sends it back.
This result is compared with a software based calculation.





Dependencies:
=============
 - SVN / Git
 - SOC-Maker
 - SCons
 - or32 toolchain (compiler, linker, debugger)
 - advanced debug bridge software
 - Xilinx BSDL files (usually in our xilinx installation)
 - Spartan 3an starter kit 
   (no hard dependenciy, but 
   the procedure below needs to be adapted)


Description
===========

Do the following to get the test system working: 


  # replace <Version> in order to match your SOC-Maker version
  git clone  --branch <Version> https://github.com/feddischson/soc_maker_lib.git

  # initialize the soc_maker_lib
  soc_maker -i -l soc_maker_lib

  # create the system
  soc_maker -l ./ test_system.yaml



  # create a Xilinx project file and synthesize all files 
  # from ./rtl and ./build


  # program your FPGA and start the adv_jtag_bridge
  # 

  impact # and do the programming
  ./adv_jtag_bridge -t  -b <PATH_TO_BSDLS_FILES> -x 1 xpc_usb


  #
  # Build and run the software
  # 

  # in terminal 1:
  cd sw
  scons
  or32-elf-gdb test_sys_sw.or32 -x gdb.cmd


  #in terminal 2:
  cd sw
  ./test_tool /dev/ttyUSB0 115200 2000  #replace  /dev/ttyUSB0 with our serial port


