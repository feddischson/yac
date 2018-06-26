/***************************************************************************
*                                                                          *
*  File           : main.c                                                 *
*  Project        : YAC (Yet Another CORDIC Core)                          *
*  Creation       : Jun. 2015                                              *
*  Limitations    :                                                        *
*  Platform       : Linux                                                  *
*  Target         : Open Risc MCU (test-system)                            *
*                                                                          *
*  Author(s):     : Christian Haettich                                     *
*  Email          : feddischson@gmail.com                                  *
*                                                                          *
*                                                                          *
**                                                                        **
*                                                                          *
*  Description                                                             *
*        C implementation for a test system: Or32 part.                    *
*        This implementation receives messages via serial line.            *
*        Each message contains a calculation request, and each answer      *
*        contains the calculation result                                   *
*        All messages have the same size, starting with a synchronization  *
*        byte and a header byte.                                           *
*                                                                          *
*                                                                          *
****************************************************************************
*                                                                          *
*                     Copyright Notice                                     *
*                                                                          *
*    This file is part of YAC - Yet Another CORDIC Core                    *
*    Copyright (c) 2015, Author(s), All rights reserved.                   *
*                                                                          *
*    YAC is free software; you can redistribute it and/or                  *
*    modify it under the terms of the GNU Lesser General Public            *
*    License as published by the Free Software Foundation; either          *
*    version 3.0 of the License, or (at your option) any later version.    *
*                                                                          *
*    YAC is distributed in the hope that it will be useful,                *
*    but WITHOUT ANY WARRANTY; without even the implied warranty of        *
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU     *
*    Lesser General Public License for more details.                       *
*                                                                          *
*    You should have received a copy of the GNU Lesser General Public      *
*    License along with this library. If not, download it from             *
*    http://www.gnu.org/licenses/lgpl                                      *
*                                                                          *
***************************************************************************/
#include "interconnect.h"
#include "support.h"
#include "or1200.h"

#include "uart.h"
#include "board.h"
#include <stdint.h>
#include "msg.h"
#include "yac.h"
#include "crc.h"


static uint8_t byte_cnt;
static uint8_t in_sync;
static void update_buf( uint8_t c );
static void proceed_msg( Msg * m );


/* our yac instance */
static YAC yac;



int main()
{
  uart_init( UART_BASE );
  empty_RX( ); 

  in_sync  = 0;
  byte_cnt = 0;

  yac_init( &yac,
            YAC_BASE,
            YAC_XY_WIDTH,
            YAC_A_WIDTH,
            YAC_RM_GAIN,
            YAC_N_ENTRIES );


  while(1)
  {
    update_buf( uart_getc() );
  }
}


/* serial decoding and synchronization */
void update_buf( uint8_t c )
{
  /* input buffer */
  static Msg buf;


  if( 0 == in_sync && SYNC_BYTE == c )
  {
    in_sync = 1;
    byte_cnt = 1;
    buf.bytes[ 0 ] = c;
  }
  else 
  if( 1 == in_sync && byte_cnt < sizeof( Msg ) )
  {
    buf.bytes[ byte_cnt ] = c;
    byte_cnt++;
  }
  else 
  if( 1 == in_sync && 0 == byte_cnt )
  {
    byte_cnt++;
    if( SYNC_BYTE == c )
      buf.bytes[ 0 ] = c;
    else
      in_sync = 0;
  }


  /* we are synchronized and have a full message */
  if( in_sync && byte_cnt == sizeof( Msg ) )
  {
    byte_cnt = 0;
    proceed_msg( &buf );
  }

}

void proceed_msg( Msg * m )
{
  uint8_t crc_in = crc( m->bytes, sizeof( Msg )-1 );
  if( crc_in != m->fields.crc )
  {
    /* Ignore message!
     * The pc will handle the situation, that
     * he doesn't get a response!
     */
  }
  else 
  if( CMD_NOP == m->fields.header )
  {
    /* simple echo */
    uart_write( (char*)m->bytes, sizeof( Msg ) );
  }

  else
  if( CMD_CALC == m->fields.header )
  {

    /* please note: we extract the message fields to the stack
     * because of some "Program received signal SIGBUS, Bus error. ... incomplete sequence" 
     * problem. It seems there is some problem with the alignment 
     * (or maybe something else, but the problem does not occur if there is no pragma pack in msg.h)
     * 
     * */
    int32_t x, xx, y, yy, a, aa;
    uint8_t mode;

    /* extract */
    x    = m->fields.payload[0];
    y    = m->fields.payload[1];
    a    = m->fields.payload[3];
    mode = m->fields.mode;

    /* do the calculation */
    yac_single( &yac, 
        &x, &y, &a, &xx, &yy, &aa, &mode );

    /* put back the result */
    m->fields.payload[ 0 ] = xx;
    m->fields.payload[ 1 ] = yy;
    m->fields.payload[ 2 ] = aa;

    /* calculate the crc*/
    m->fields.crc = crc( m->bytes, sizeof( Msg )-1 );

    /* write out the message */
    uart_write( (char*)&m->bytes[0], sizeof( Msg ) );
  }

}
