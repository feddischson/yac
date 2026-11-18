
Synopsis
=============
This repository holds a CORDIC digital design written in VHDL. which can be used e.g. for integration in FPGA-based SOCs.


Description
==============

CORDIC is the acronym for COordinate Rotation DIgital Computer and 
allows a hardware efficient calculation of various functions 
like - atan, sin, cos - atanh, sinh, cosh, - division, multiplication. 
Hardware efficient means, that only shifting, additions and 
subtractions in combination with table-lookup is required. This makes 
it suitable for a realization in digital hardware. Good 
introductions can be found in [1][2][3][5]. 



The following six CORDIC modes are supported: 
 - trigonometric rotation
 - trigonometric vectoring
 - linear rotation
 - linear vectoring
 - hyperbolic rotation
 - hyperbolic vectoring


The iterative core (`cordic_iterative_int`) is started 
with a set of input data and after a specific amount of 
clock cycles, the result is 
available. No parallel data can be processed by the iterative core.

The pipelined core (`cordic_pipeline_int`) does circular rotation, or with the generic
`VECTORING = true` circular vectoring (magnitude and angle, output `a_o`).
It accepts a new sample every clock cycle and has a fixed latency of 
`1 + N_ITER + RM_GAIN` clocks. The angle is a binary angle: 
`a_i` is an unsigned fraction of a full circle. 

In addition to an IP-core written in VHDL, a bit-accurate C-model 
is provided for each core. The C-model of the iterative core can be 
compiled as mex for a usage with Octave or 
Matlab. The C-model of the pipelined core is plain C99 with a Python (`ctypes`, 
`numpy`) wrapper and needs neither Octave nor Matlab. 
Therefore, the C-models allow a bit-accurate analysis 
of the CORDIC performance on a higher level. 


For a more detailed documentation, see `./doc/documentation.pdf`





Status
==================
- C-model implementation is done
- RTL model implementation is done
- RTL model is verified against C-model
- Wishbone-bus wrapper is added
- Included into a small SoC, tested on a spartan-3 FPGA
- Testing within an SOC is done (see `./test_sys`)
- Pipelined core (rotation and vectoring): C-model, Python wrapper and RTL are done.
  The RTL is compared bit-exactly with the C-model in 112 VUnit tests (Questa),
  and the C-model is compared with the exact rotation and the exact vectoring
  (`./test/model/run.py`).
  The default generics are placeholders, not set by an FFT accuracy measurement.
- Pipelined core, rotation, synthesis on Cyclone V 5CSEBA6U23I7 (Quartus 23.1,
  default generics, no pin assignments): 524 ALMs, 1068 registers, no DSP
  blocks, no block memory, Fmax 252.53 MHz in the slow 1100 mV 100 C model and
  243.78 MHz in the slow 1100 mV -40 C model, indicative only
- Pipelined core, vectoring and further synthesis rows: see `./doc/documentation.pdf`,
  chapter Pipelined Core, section Synthesis.




Next-Steps / Open Points
=========================
- Circuit optimizations
- Numerical optimizations




Files and folders:
====================

  - `./c_octave`  contains a bit-accurate C-implementation of the YAC.
                  This C-implementation is used for analyzing the performance
                  and to generate RTL testbench stimulus
                  (cordic_iterative_test.m).
                  The file cordic_iterative_code.m is used to create some
                  VHDL/C-code automatically.
  - `./c_model`   contains the bit-accurate C-implementation of the pipelined core
                  (`cordic_pipeline.c`), its `ctypes` wrapper
                  (`cordic_pipeline.py`) and the table generator
                  (`gen_tables.py`), which writes `cordic_pipeline_tables.h`
                  and `rtl/vhdl/cordic_pipeline_pkg.vhd`.
  - `./rtl/vhdl`  Contains the VHDL implementation files
  - `./test`      Contains the tests of the pipelined core: `model/run.py`
                  (C-model against the exact rotation) and `pipeline/run.py`
                  (VUnit, RTL against the C-model).
  - `./doc`       Contains the documentation (`documentation.tex`, `documentation.pdf`).
  - `./test_sys`  Contains a test system to test the YAC on a spartan-3an board



Running the tests of the pipelined core
=========================================

Create a Python environment with `python3 -m venv <dir>` and install
`py_requirements.txt`. The tests need gcc. `pipeline/run.py` needs Questa
in the `PATH`, and both scripts build the C-model into their output directory.

```
<dir>/bin/python test/model/run.py --out <scratch>/model
<dir>/bin/python test/pipeline/run.py -o <scratch>/vunit -p 8
```

`model/run.py` ends with `OK` and writes `sweep.csv` and `sweep_vec.csv` (rotation and
vectoring accuracy over the generics) into its output directory. `pipeline/run.py` ends with `All passed!`.


References
====================
  - [1] Andraka, Ray; A survey of CORDIC algorithms for FPGA based computers, 1989 
  - [2] Hu, Yu Hen; CORDIC-Based VLSI Architectures for Digital Signal Processing, 1992 
  - [3] CORDIC on wikibook: http://en.wikibooks.org/wiki/Digital_Circuits/CORDIC 
  - [4] CORDIC on wikipedia:http://en.wikipedia.org/wiki/CORDIC 
  - [5] David, Herbert; Meyr, Heinricht; CORDIC Algorithms and Architectures 
       http://www.eecs.berkeley.edu/newton/Classes/EE290sp99/lectures/ee290aSp996_1/cordic_chap24.pdf 


License
==============
```

                   Copyright Notice                                 

  This file is part of YAC - Yet Another CORDIC Core                
  Copyright (c) 2026, Author(s), All rights reserved.               

  YAC is free software; you can redistribute it and/or              
  modify it under the terms of the GNU Lesser General Public        
  License as published by the Free Software Foundation; either      
  version 3.0 of the License, or (at your option) any later version.

  YAC is distributed in the hope that it will be useful,            
  but WITHOUT ANY WARRANTY; without even the implied warranty of    
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU 
  Lesser General Public License for more details.                   

  You should have received a copy of the GNU Lesser General Public  
  License along with this library. If not, download it from         
  http://www.gnu.org/licenses/lgpl                                  


         Author(s):  Christian Haettich        
         Email       feddischson@gmail.com 

```
