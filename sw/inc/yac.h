/* -------------------------------------------------------------------
 *
 *
 *                                                                     
 *   File           : yac.h                         
 *   Project        : YAC (Yet Another CORDIC Core)                    
 *   Creation       : Jun. 2015                                       
 *   Limitations    :                                                  
 *   Synthesizer    :                                                  
 *   Target         :                                                  
 *                                                                     
 *   Author(s):     : Christian Haettich                               
 *   Email          : feddischson@opencores.org                        
 *                                                                     
 *                                                                     
 *                                                                    
 *                                                                     
 *   Description                                                       
 *        Header file for YAC driver
 *                                                                     
 *                                                                     
 *                                                                     
 *                                                                    
 *                                                                     
 *                                                                     
 *                                                                     
 *  -------------------------------------------------------------------
 *                                                                     
 *                   Copyright Notice                                  
 *                                                                     
 *  This file is part of YAC - Yet Another CORDIC Core                 
 *  Copyright (c) 2015, Author(s), All rights reserved.                
 *                                                                     
 *  YAC is free software; you can redistribute it and/or               
 *  modify it under the terms of the GNU Lesser General Public         
 *  License as published by the Free Software Foundation; either       
 *  version 3.0 of the License, or (at your option) any later version. 
 *                                                                     
 *  YAC is distributed in the hope that it will be useful,             
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of     
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU  
 *  Lesser General Public License for more details.                    
 *                                                                     
 *  You should have received a copy of the GNU Lesser General Public   
 *  License along with this library. If not, download it from          
 *  http://www.gnu.org/licenses/lgpl                                   
 *                                                                     
 *  -------------------------------------------------------------------
 */


#ifndef _YAC_H_
#define _YAC_H_

#include <stdint.h>


#define YAC_FLAG_VEC_ROT     0x08
#define YAC_FLAG_ATAN_3      0x04
#define YAC_MODE_MSK         0x03
#define YAC_MODE_CIR         0x00
#define YAC_MODE_LIN         0x01
#define YAC_MODE_HYP         0x02


#define YAC_ENTRIES_SHIFT   16



/*
 * Setup of the instanciated yac
 */
#define YAC_XY_WIDTH        8
#define YAC_A_WIDTH         8
#define YAC_RM_GAIN         3
#define YAC_N_ENTRIES       4



typedef struct _YAC_
{
  uint32_t     base;
  uint32_t     status_reg;
  uint32_t     xy_width;
  uint32_t     a_width;
  uint8_t      rm_gain;
  uint16_t     entries;
}YAC;


void yac_init( YAC * yac,
               uint32_t   base,
               uint32_t   xy_width,
               uint32_t   a_width,
               uint8_t    rm_gain,
               uint16_t   entries );

void yac_single( YAC * yac,
                 int32_t * x_i,
                 int32_t * y_i,
                 int32_t * z_i,
                 int32_t * x_o,
                 int32_t * y_o,
                 int32_t * z_o,
                 uint8_t * mode );



#endif /* _YAC_H_ */

