//
//  DspicoRomCache.c
//  NitroSwan
//
//  Keep the BlocksDS MPU layout intact and cache only the ROM banks currently
//  visible to the emulated WonderSwan CPU.
//

#include <stdint.h>
#include <string.h>

#include "DspicoRomCache.h"

#define ROM_BANK_SIZE       0x10000U
#define ROM_CACHE_SEGMENTS  15U
#define ROM_CACHE_SIZE      (ROM_BANK_SIZE * ROM_CACHE_SEGMENTS)
#define CACHE_LINE_SIZE     32U

static uintptr_t romStart;
static uintptr_t romEnd;
static uint8_t *cacheBase;
static const uint8_t *cacheTags[ROM_CACHE_SEGMENTS];
static bool cacheActive;

void dspicoRomCacheInvalidate(void) {
	memset(cacheTags, 0, sizeof(cacheTags));
}

void dspicoRomCacheDisable(void) {
	cacheActive = false;
	romStart = 0;
	romEnd = 0;
	cacheBase = NULL;
	dspicoRomCacheInvalidate();
}

void dspicoRomCacheInit(const void *romBase, uint32_t romSize, void *cacheMemory, uint32_t cacheSize) {
	dspicoRomCacheDisable();

	uintptr_t memoryStart = (uintptr_t)cacheMemory;
	uintptr_t alignedStart = (memoryStart + CACHE_LINE_SIZE - 1)
			& ~((uintptr_t)CACHE_LINE_SIZE - 1);
	uint32_t alignmentLoss = (uint32_t)(alignedStart - memoryStart);
	if (romBase == NULL || romSize == 0 || cacheMemory == NULL
			|| cacheSize < alignmentLoss || cacheSize - alignmentLoss < ROM_CACHE_SIZE) {
		return;
	}

	romStart = (uintptr_t)romBase;
	romEnd = romStart + romSize;
	if (romEnd < romStart) {
		dspicoRomCacheDisable();
		return;
	}

	cacheBase = (uint8_t *)alignedStart;
	cacheActive = true;
}

bool dspicoRomCacheIsActive(void) {
	return cacheActive;
}

const uint8_t *dspicoRomCacheMap(const uint8_t *source, uint32_t segment) {
	if (!cacheActive || segment == 0 || segment > ROM_CACHE_SEGMENTS) {
		return source;
	}

	uintptr_t sourceStart = (uintptr_t)source;
	if (sourceStart < romStart || sourceStart > romEnd
			|| ROM_BANK_SIZE > romEnd - sourceStart) {
		return source;
	}

	uint32_t slot = segment - 1;
	uint8_t *destination = cacheBase + slot * ROM_BANK_SIZE;
	if (cacheTags[slot] != source) {
		memcpy(destination, source, ROM_BANK_SIZE);
		cacheTags[slot] = source;
	}
	return destination;
}

void dspicoRomCacheUnmap(uint32_t segment) {
	if (segment != 0 && segment <= ROM_CACHE_SEGMENTS) {
		cacheTags[segment - 1] = NULL;
	}
}

void dspicoRomCacheWriteBack(uint32_t segment, uint32_t offset, uint32_t length) {
	if (!cacheActive || segment == 0 || segment > ROM_CACHE_SEGMENTS
			|| offset > ROM_BANK_SIZE || length > ROM_BANK_SIZE - offset) {
		return;
	}

	uint32_t slot = segment - 1;
	if (cacheTags[slot] != NULL) {
		memcpy((uint8_t *)cacheTags[slot] + offset,
				cacheBase + slot * ROM_BANK_SIZE + offset, length);
	}
}
