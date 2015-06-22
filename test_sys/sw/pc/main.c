/***************************************************************************
*                                                                          *
*  File           : main.c                                                 *
*  Project        : YAC (Yet Another CORDIC Core)                          *
*  Creation       : Jun. 2015                                              *
*  Limitations    :                                                        *
*  Platform       : Linux                                                  *
*  Target         : Linux-Os                                               *
*                                                                          *
*  Author(s):     : Christian Haettich                                     *
*  Email          : feddischson@opencores.org                              *
*                                                                          *
*                                                                          *
**                                                                        **
*                                                                          *
*  Description                                                             *
*        C implementation for a test system: PC part.                      *
*        This implementation sends messages via serial line.               *
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

#include <errno.h>
#include <termios.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <endian.h>
#include <math.h>

#include "msg.h"
#include "yac.h"
#include "crc.h"


/**
 * Some error numbers used by this little tool
 */
#define ERR_NONE      0   /* no error               */
#define ERR_CRC       1   /* CRC error              */
#define ERR_TIMEOUT   2   /* Timeout error          */
#define ERR_CALC      3   /* Calculation error      */
#define ERR_SYNC      4   /* Synchronization error  */
#define ERR_SERIAL    5   /* Serial comm. error     */

#if 0
 #define VERBOSE 
#endif


/* 
 * implemented in cordic_iterative.c 
 */
extern
void cordic_int( long long int   x_i, 
                 long long int   y_i,
                 long long int   a_i,
                 long long int * x_o,
                 long long int * y_o,
                 long long int * a_o,
                 int           * it_o,
                 int        mode,
                 int        XY_WIDTH,
                 int        A_WIDTH,
                 int        GUARD_BITS,
                 int        RM_GAIN );


/*
 * global message buffers
 */
static Msg global_out_buf;
static Msg global_in_buf;


/*
 * local functions
 */
uint8_t do_test           ( int fd, int x, int y, int z, int mode );
uint8_t do_sync           ( int fd );
uint8_t run_random_test   ( int fd, uint32_t n_test );
int     init_serial_port  ( char* portname, int baud, int timeout );
void    print_usage_and_exit( void );




int main( int argc, char* argv[] )
{
  int       i;
  char*     portname ;
  int       baud;
  int       serial_fd;
  int       n_tests;

  if( argc != 4 )
    print_usage_and_exit( );

  if( 1 != sscanf( argv[3], "%d", &n_tests ) )
    print_usage_and_exit( );
  if( 1 != sscanf( argv[2], "%d", &baud ) )
    print_usage_and_exit( );
  portname = argv[1];



  memset( global_out_buf.bytes, 0, sizeof( Msg ) );
  global_out_buf.fields.sync = SYNC_BYTE;


  serial_fd = init_serial_port( portname, baud, 10 );
  if( -1 == serial_fd )
    return -1;

  if( ERR_NONE != do_sync( serial_fd ) )
    fprintf( stderr, "Error: failed to sync\n" );

  run_random_test( serial_fd, n_tests );

  return 0;
}

/* 
 * Prints some usage message
 */
void print_usage_and_exit( void )
{
  printf( "Usage: TODO <port> <baud> <n-tests>\n" );
  exit( -1 );
}



/**
 * Initializes the serial port
 */
int init_serial_port( char* portname, int baud, int timeout )
{

  struct termios tty;
  int serial_fd = open ( portname, O_RDWR | O_NOCTTY | O_SYNC );
  if( serial_fd == -1 )
  {
    fprintf( stderr, "Error: Failed to open serial port %s\n", portname );
    return -1;
  }

  memset (&tty, 0, sizeof( tty ) );
  if (tcgetattr ( serial_fd, &tty ) != 0)
  {
    fprintf( stderr, "Error %d from tcgetattr", errno );
    return -1;
  }

  cfsetospeed (&tty, baud);
  cfsetispeed (&tty, baud);

  tty.c_cflag     = (tty.c_cflag & ~CSIZE) | CS8;
  tty.c_iflag    &= ~IGNBRK;         
  tty.c_lflag     = 0;                

  tty.c_oflag     = 0;                
  tty.c_cc[VMIN]  = 0;                       /* non blocking */
  tty.c_cc[VTIME] = 1;      

  tty.c_iflag    &= ~(IXON | IXOFF | IXANY); /* shut off xon/xoff ctrl */
  tty.c_cflag    |= (CLOCAL | CREAD);
  tty.c_cflag    &= ~(PARENB | PARODD);
  tty.c_cflag    |= 0;                       /* parity */
  tty.c_cflag    &= ~CSTOPB;
  tty.c_cflag    &= ~CRTSCTS;

  if (tcsetattr ( serial_fd, TCSANOW, &tty ) != 0)
  {
    fprintf( stderr, "Error %d from tcsetattr", errno);
    return -1;
  }

  return serial_fd;
}


/**
 * Function to send and receive one message.
 *
 */
uint8_t snd_rcv( int fd, Msg out_buf, Msg * in_buf, int fail_cnt )
{
  int w_bytes, r_bytes;
  uint8_t *ptr;
  uint8_t crc_in;
  out_buf.fields.payload[ 0 ] = htobe32( out_buf.fields.payload[ 0 ] );
  out_buf.fields.payload[ 1 ] = htobe32( out_buf.fields.payload[ 1 ] );
  out_buf.fields.payload[ 2 ] = htobe32( out_buf.fields.payload[ 2 ] );

  out_buf.fields.crc = crc( out_buf.bytes, sizeof( Msg )-1 );

  w_bytes = write( fd, out_buf.bytes, sizeof( Msg ) );

  if( w_bytes != sizeof( Msg ) )
    return ERR_SERIAL;

  ptr = &in_buf->bytes[ 0 ];
  while( w_bytes )
  {
    r_bytes = read( fd, ptr, w_bytes );
    ptr     += r_bytes;
    w_bytes -= r_bytes;

    if( --fail_cnt == 0 )
    {
      #if 0
      printf( "timeout\n" );
      #endif
      return ERR_TIMEOUT;
    }
  }
  crc_in = crc( in_buf->bytes, sizeof( Msg )-1 );
  in_buf->fields.payload[ 0 ] = be32toh( in_buf->fields.payload[ 0 ] );
  in_buf->fields.payload[ 1 ] = be32toh( in_buf->fields.payload[ 1 ] );
  in_buf->fields.payload[ 2 ] = be32toh( in_buf->fields.payload[ 2 ] );
  if( crc_in != in_buf->fields.crc )
  {
    #if 0
    printf( "crc error (%x <-> %x )\n", crc_in, in_buf->fields.crc ); 
    #endif
    return ERR_CRC;
  }

  if( in_buf->fields.sync == out_buf.fields.sync )
    return ERR_NONE;
  else
    return ERR_SYNC;
}

/**
 * Send and receive a synchronization message 
 * ( empty NOP message )
 */
uint8_t do_sync( int fd )
{
  uint8_t res;

  global_out_buf.fields.header = CMD_NOP;
  res = snd_rcv( fd, global_out_buf, &global_in_buf, 40 );
  if( res != ERR_NONE )
    return res;


  if( global_in_buf.fields.sync   == global_out_buf.fields.sync &&
      global_in_buf.fields.header == global_out_buf.fields.header )
    return ERR_NONE;
  else
    return ERR_SYNC;
}





/** 
 * Function to run n_test tests
 *
 */
uint8_t run_random_test( int fd, uint32_t n_test )
{

  uint8_t  res;
  uint32_t test_cnt = 0;
  uint32_t calc_cnt = 0;
  uint32_t crc_cnt  = 0;
  uint32_t othr_cnt = 0;

  srand( 1234 );
  uint32_t i;
  for( i=0; i < n_test; i++, test_cnt++ )
  {
    int32_t y = ( rand() % ( (int32_t) pow( 2, YAC_XY_WIDTH ) ) ) - pow( 2, YAC_XY_WIDTH-1 );
    int32_t x = ( rand() % ( (int32_t) pow( 2, YAC_XY_WIDTH ) ) ) - pow( 2, YAC_XY_WIDTH-1 );

    res = do_test( fd, x, y, 0,  YAC_FLAG_VEC_ROT | YAC_MODE_CIR   );

    if( ERR_NONE != res )
    {
      if( res == ERR_CALC )
        calc_cnt++;
      else if( res == ERR_CRC )
        crc_cnt++;
      else
        othr_cnt++;

    }
  }

  printf(" %d of %d tests failed, (crc-errors: %d, other errors: %d )\n", 
        calc_cnt, 
        test_cnt,
        crc_cnt,
        othr_cnt );

  return ERR_NONE;
}


/**
 * Run one single test
 *
 */
uint8_t do_test( int fd, int x, int y, int z, int mode )
{
  long long int xo;
  long long int yo;
  long long int zo;
  uint8_t res;
  int it;

  /* local calculation */
  cordic_int(
    x, y, z, &xo, &yo, &zo, &it, mode, 
      YAC_XY_WIDTH, 
      YAC_A_WIDTH,
      2,
      YAC_RM_GAIN
      );


  /* remote calculation */
  global_out_buf.fields.header = CMD_CALC;
  global_out_buf.fields.payload[ 0 ] = x;
  global_out_buf.fields.payload[ 1 ] = y;
  global_out_buf.fields.payload[ 2 ] = z;
  global_out_buf.fields.mode         = mode;
  res = snd_rcv( fd, global_out_buf, &global_in_buf, 10 );
  if( ERR_NONE != res  )
    return res;

  # if defined (VERBOSE)
  printf("( %d <-> %d ) \n", global_in_buf.fields.payload[0], (int)xo );
  printf("( %d <-> %d ) \n", global_in_buf.fields.payload[1], (int)yo );
  printf("( %d <-> %d ) \n", global_in_buf.fields.payload[2], (int)zo );
  #endif

  /* result comparions */
  if ( (xo == global_in_buf.fields.payload[0]) && 
       (yo == global_in_buf.fields.payload[1]) && 
       (zo == global_in_buf.fields.payload[2])  ) 
    return ERR_NONE;
  else
    return ERR_CALC;

}


