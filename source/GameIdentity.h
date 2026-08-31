#ifndef GAME_IDENTITY_HEADER
#define GAME_IDENTITY_HEADER

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

bool isOnePieceGrandBattle(uint8_t publisher, uint8_t color,
	uint8_t gameId, uint8_t gameRev);

#ifdef __cplusplus
}
#endif

#endif
