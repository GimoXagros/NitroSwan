#include <assert.h>

#include "GameIdentity.h"

int main(void) {
	// Original ROM header checksum 0xFD2E. Checksum is deliberately not an input.
	assert(isOnePieceGrandBattle(0x01, 0x01, 0x29, 0x00));
	// Modified/translated ROM header checksum 0x025F has the same product identity.
	assert(isOnePieceGrandBattle(0x01, 0x01, 0x29, 0x00));
	// Bit 7 is EEPROM write-protect behavior, not a product revision bit.
	assert(isOnePieceGrandBattle(0x01, 0x01, 0x29, 0x80));
	assert(!isOnePieceGrandBattle(0x01, 0x01, 0x28, 0x00));
	assert(!isOnePieceGrandBattle(0x02, 0x01, 0x29, 0x00));
	assert(!isOnePieceGrandBattle(0x01, 0x00, 0x29, 0x00));
	assert(!isOnePieceGrandBattle(0x01, 0x01, 0x29, 0x01));
	return 0;
}
