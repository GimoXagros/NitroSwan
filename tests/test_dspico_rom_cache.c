#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "DspicoRomCache.h"

#define BANK_SIZE 0x10000U
#define CACHE_SIZE (15U * BANK_SIZE + 31U)

int main(void) {
	uint8_t *rom = malloc(2U * BANK_SIZE);
	uint8_t *cache = malloc(CACHE_SIZE);
	assert(rom != NULL && cache != NULL);

	memset(rom, 0x11, BANK_SIZE);
	memset(rom + BANK_SIZE, 0x22, BANK_SIZE);
	memset(cache, 0, CACHE_SIZE);

	dspicoRomCacheInit(rom, 2U * BANK_SIZE, cache, CACHE_SIZE);
	assert(dspicoRomCacheIsActive());

	const uint8_t *segment1 = dspicoRomCacheMap(rom, 1);
	const uint8_t *segment2 = dspicoRomCacheMap(rom + BANK_SIZE, 2);
	assert(segment1 != rom && segment2 != rom + BANK_SIZE);
	assert(segment1[0] == 0x11 && segment1[BANK_SIZE - 1] == 0x11);
	assert(segment2[0] == 0x22 && segment2[BANK_SIZE - 1] == 0x22);

	((uint8_t *)segment1)[123] = 0x5A;
	dspicoRomCacheWriteBack(1, 123, 1);
	assert(rom[123] == 0x5A);
	dspicoRomCacheUnmap(1);
	((uint8_t *)segment1)[124] = 0x6B;
	dspicoRomCacheWriteBack(1, 124, 1);
	assert(rom[124] != 0x6B);
	segment1 = dspicoRomCacheMap(rom, 1);

	rom[0] = 0x44;
	assert(dspicoRomCacheMap(rom, 1)[0] == 0x11);
	dspicoRomCacheInvalidate();
	assert(dspicoRomCacheMap(rom, 1)[0] == 0x44);

	const uint8_t *outside = rom + 2U * BANK_SIZE;
	assert(dspicoRomCacheMap(outside, 3) == outside);
	dspicoRomCacheDisable();
	assert(!dspicoRomCacheIsActive());
	assert(dspicoRomCacheMap(rom, 1) == rom);

	free(cache);
	free(rom);
	return 0;
}
