//
//  DspicoRomCache.h
//  NitroSwan
//
//  Project-local ROM bank cache for DSpico debugger RAM.
//

#ifndef DSPICO_ROM_CACHE_HEADER
#define DSPICO_ROM_CACHE_HEADER

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void dspicoRomCacheInit(const void *romBase, uint32_t romSize, void *cacheMemory, uint32_t cacheSize);
void dspicoRomCacheDisable(void);
void dspicoRomCacheInvalidate(void);
bool dspicoRomCacheIsActive(void);

/** Maps one 64 KiB WonderSwan segment to cached main RAM. */
const uint8_t *dspicoRomCacheMap(const uint8_t *source, uint32_t segment);
void dspicoRomCacheUnmap(uint32_t segment);

/** Copies modified cached flash data back to the DSpico ROM image. */
void dspicoRomCacheWriteBack(uint32_t segment, uint32_t offset, uint32_t length);

#ifdef __cplusplus
} // extern "C"
#endif

#endif // DSPICO_ROM_CACHE_HEADER
