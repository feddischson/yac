/* -------------------------------------------------------------------
 *
 *
 *                                                                     
 *   File           : yac.c                         
 *   Project        : YAC (Yet Another CORDIC Core)                    
 *   Creation       : Jun. 2015                                       
 *   Limitations    :                                                  
 *   Synthesizer    :                                                  
 *   Target         :                                                  
 *                                                                     
 *   Author(s):     : Christian Haettich                               
 *   Email          : feddischson@gmail.com
 *                                                                     
 *                                                                     
 *                                                                    
 *                                                                     
 *   Description                                                       
 *        Implementation of functions to access the yac.
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
#include "yac.h"


#define REG32(adr) *((volatile unsigned long *)(adr))


void yac_init( YAC * yac,
               uint32_t   base,
               uint32_t   xy_width,
               uint32_t   a_width,
               uint8_t    rm_gain,
               uint16_t   entries )
{
  yac->base         = base;
  yac->xy_width     = xy_width;
  yac->a_width      = a_width;
  yac->rm_gain      = rm_gain;
  yac->entries      = entries;
  yac->status_reg   = base + ( entries<<4);
}



void yac_single( YAC * yac,
                 int32_t * x_i,
                 int32_t * y_i,
                 int32_t * z_i,
                 int32_t * x_o,
                 int32_t * y_o,
                 int32_t * z_o,
                 uint8_t * mode )
{
    REG32( yac->base + 0   ) =  *x_i;
    REG32( yac->base + 4   ) =  *y_i;
    REG32( yac->base + 8   ) =  *z_i;
    REG32( yac->base + 12  ) = *mode;
    REG32( yac->status_reg ) = (1<<YAC_ENTRIES_SHIFT) | 1;

    /* busy wait loop until the yac is done */
    while( REG32( yac->status_reg ) & 1 );

    *x_o = REG32( yac->base + 0 );
    *y_o = REG32( yac->base + 4 );
    *z_o = REG32( yac->base + 8 );
}
