#include <nds.h>
#include <string.h>

#include "Cart.h"
#include "ObjTileBuffer.h"

#define OBJ_TILE_COUNT 512
#define OBJ_TILE_BYTES 32
#define OBJ_BANK_BYTES (OBJ_TILE_COUNT * OBJ_TILE_BYTES)

volatile u16 wsvObjTileOffset;
volatile u16 objTilesConvertedFrame;
volatile u16 objTilesConvertedMaximum;
volatile u32 objBytesCopiedFrame;
volatile u32 objBytesCopiedMaximum;
volatile u32 objBufferSwapCount;

static bool modeInitialized;
static u8 previousFormat;

static unsigned int captureDirtyTiles(unsigned int cleanFlag) {
	const u8 *dirty = DIRTYTILES + 0x200;
	unsigned int count = 0;
	const u32 cleanWord = cleanFlag * 0x01010101U;
	for (unsigned int group = 0; group < OBJ_TILE_COUNT / 4; group++) {
		u32 markers;
		memcpy(&markers, &dirty[group * 4], sizeof(markers));
		if (markers == cleanWord) {
			continue;
		}
		for (unsigned int part = 0; part < 4; part++) {
			if (((markers >> (part * 8)) & cleanFlag) == 0) {
				count++;
			}
		}
	}
	return count;
}

static void seedObjBank(unsigned int sourceOffset, unsigned int destinationOffset) {
	volatile u32 *source = (volatile u32 *)SPRITE_GFX + sourceOffset * 8;
	volatile u32 *destination = (volatile u32 *)SPRITE_GFX + destinationOffset * 8;

	// The destination bank was displayed two generations ago. A partial seed
	// can miss tiles when games rewrite different animation tiles on successive
	// frames, so make a coherent snapshot whenever a generation is committed.
	// Clean frames do not copy or swap.
	memcpy((void *)destination, (const void *)source, OBJ_BANK_BYTES);
}

void objTileBufferReset(void) {
	wsvObjTileOffset = 0;
	objTilesConvertedFrame = 0;
	objTilesConvertedMaximum = 0;
	objBytesCopiedFrame = 0;
	objBytesCopiedMaximum = 0;
	objBufferSwapCount = 0;
	modeInitialized = false;
	previousFormat = 0;
}

void objTileBufferBeginFrame(unsigned int videoMode) {
	objTilesConvertedFrame = 0;
	objBytesCopiedFrame = 0;

	const u8 format = videoMode & 0xE0;
	if (!modeInitialized || format != previousFormat) {
		if (modeInitialized) {
			if ((format & 0xC0) == 0xC0) {
				memset(DIRTYTILES + 0x200, 0, 0x400);
			}
			else {
				memset(DIRTYTILES + 0x100, 0, 0x400);
			}
		}
		previousFormat = format;
		modeInitialized = true;
	}

	if ((format & 0xC0) != 0xC0) {
		wsvObjTileOffset = 0;
		return;
	}

	const unsigned int cleanFlag = (videoMode & 0x20) != 0 ? 0x10 : 0x20;
	const unsigned int converted = captureDirtyTiles(cleanFlag);
	objTilesConvertedFrame = converted;
	if (converted > objTilesConvertedMaximum) {
		objTilesConvertedMaximum = converted;
	}
	if (converted == 0) {
		return;
	}

	const unsigned int sourceOffset = wsvObjTileOffset;
	const unsigned int destinationOffset = sourceOffset ^ 0x200;
	seedObjBank(sourceOffset, destinationOffset);
	objBytesCopiedFrame = OBJ_BANK_BYTES;
	if (objBytesCopiedFrame > objBytesCopiedMaximum) {
		objBytesCopiedMaximum = objBytesCopiedFrame;
	}

	wsvObjTileOffset = destinationOffset;
	objBufferSwapCount++;
}
