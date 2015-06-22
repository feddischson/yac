#ifndef _MSG_H_
#define _MSG_H_
#include <stdint.h>

#define SYNC_BYTE  0x55

#define CMD_NOP     0x00
#define CMD_CALC    0x10


#pragma pack( push, 1 )
typedef union _MSG_ {
  struct _fields_ {
    uint8_t  sync;
    uint8_t  header;
    uint8_t  mode;
    int32_t payload[ 3 ];
    uint8_t  crc;
  }fields;

  uint8_t bytes[ sizeof( struct _fields_ ) ];

}Msg;
#pragma pack( pop )

#endif
