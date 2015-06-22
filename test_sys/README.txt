
Dependencies:
 - SVN / Git
 - SOC-Maker
 - SCons
 - or32 toolchain (compiler, linker, debugger)
 - advanced debug bridge software
 - Xilinx BSDL files (usually in our xilinx installation)
 - Spartan 3an starter kit 
   (no hard dependenciy, but 
   the procedure below needs to be adapted)



Do the following to get the test system working: 



  # replace <Version> in order to match your SOC-Maker version
  git clone  --branch <Version> https://github.com/feddischson/soc_maker_lib.git


  # create the system
  soc_maker test_system.yaml


  # create a Xilinx project file and synthesize all files 
  # from ./rtl and ./build

  # program your FPGA

  # Build the software
  # todo ...

