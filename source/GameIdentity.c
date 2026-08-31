#include "GameIdentity.h"

bool isOnePieceGrandBattle(uint8_t publisher, uint8_t color,
	uint8_t gameId, uint8_t gameRev) {
	// Bit 7 controls internal EEPROM write protection; bits 0-6 are the revision.
	return publisher == 0x01 && color == 0x01 && gameId == 0x29 &&
		(gameRev & 0x7F) == 0x00;
}
