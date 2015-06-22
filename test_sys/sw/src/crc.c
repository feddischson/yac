#include <stdint.h>

/* 
 *  Message size up to 2^8 byte only!
 */
uint8_t crc( uint8_t *data, uint8_t l, uint8_t crc_init )
{
	uint8_t i, j;
	uint8_t crc = 0;

	for ( i = 0; i<l; i++ ) {
		crc ^= ( *data );
		for(j = 0; j<8; j++) {
			if (crc & 0x80)
				crc ^= 0x07;
			crc <<= 1;
		}
        data++;
	}
	return (uint8_t)crc;
}
