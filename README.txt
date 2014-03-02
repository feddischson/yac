----------------------------------------------------------------------------
----                                                                    ----
----                  Copyright Notice                                  ----
----                                                                    ----
---- This file is part of YAC - Yet Another CORDIC Core                 ----
---- Copyright (c) 2014, Author(s), All rights reserved.                ----
----                                                                    ----
---- YAC is free software; you can redistribute it and/or               ----
---- modify it under the terms of the GNU Lesser General Public         ----
---- License as published by the Free Software Foundation; either       ----
---- version 3.0 of the License, or (at your option) any later version. ----
----                                                                    ----
---- YAC is distributed in the hope that it will be useful,             ----
---- but WITHOUT ANY WARRANTY; without even the implied warranty of     ----
---- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU  ----
---- Lesser General Public License for more details.                    ----
----                                                                    ----
---- You should have received a copy of the GNU Lesser General Public   ----
---- License along with this library. If not, download it from          ----
---- http://www.gnu.org/licenses/lgpl                                   ----
----                                                                    ----
----------------------------------------------------------------------------




Files and folders:
------------------

 ./c_octave :  contains a bit-accurate C-implementation of the YAC.
               This C-implementation is used for analyzing the performance
               and to generate RTL testbench stimulus
               (cordic_iterative_test.m).
               The file cordic_iterative_code.m is used to create some
               VHDL/C-code automatically.

 ./rtl/vhdl :  Contains the VHDL implementation files

 ./doc      :  Will contain a detailed documentation in future.




