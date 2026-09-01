#include <nds.h>
#include <string.h>

#include "Cart.h"
#include "ObjTileBuffer.h"

#define OBJ_TILE_COUNT 512
#define OBJ_TILE_BYTES 32
#define OBJ_DIRTY_WORDS (OBJ_TILE_COUNT / 32)

volatile u16 wsvObjTileOffset;
volatile u16 objTilesConvertedFrame;
volatile u16 objTilesConvertedMaximum;
volatile u32 objBytesCopiedFrame;
volatile u32 objBytesCopiedMaximum;
volatile u32 objBufferSwapCount;

static u32 previousDirty[OBJ_DIRTY_WORDS];
static u32 currentDirty[OBJ_DIRTY_WORDS];
static bool bufferInitialized;
static bool modeInitialized;
static u8 previousFormat;

static unsigned int bitCount(u32 bits) {
	return __builtin_popcount(bits);
}

static unsigned int captureDirtyTiles(unsigned int cleanFlag) {
	const u8 *dirty = DIRTYTILES + 0x200;
	unsigned int count = 0;
	memset(currentDirty, 0, sizeof(currentDirty));
	const u32 cleanWord = cleanFlag * 0x01010101U;
	for (unsigned int group = 0; group < OBJ_TILE_COUNT / 4; group++) {
		u32 markers;
		memcpy(&markers, &dirty[group * 4], sizeof(markers));
		if (markers == cleanWord) {
			continue;
		}
		for (unsigned int part = 0; part < 4; part++) {
			const unsigned int tile = group * 4 + part;
			if (((markers >> (part * 8)) & cleanFlag) == 0) {
				currentDirty[tile >> 5] |= 1U << (tile & 31);
				count++;
			}
		}
	}
	return count;
}

static unsigned int seedChangedTiles(unsigned int sourceOffset,
	unsigned int destinationOffset) {
	volatile u32 *source = (volatile u32 *)SPRITE_GFX + sourceOffset * 8;
	volatile u32 *destination = (volatile u32 *)SPRITE_GFX + destinationOffset * 8;
	unsigned int copied = 0;

	for (unsigned int word = 0; word < OBJ_DIRTY_WORDS; word++) {
		u32 bits = previousDirty[word];
		copied += bitCount(bits);
		while (bits != 0) {
			const unsigned int bit = __builtin_ctz(bits);
			const unsigned int tile = word * 32 + bit;
			const unsigned int offset = tile * (OBJ_TILE_BYTES / sizeof(u32));
			for (unsigned int part = 0; part < OBJ_TILE_BYTES / sizeof(u32); part++) {
				destination[offset + part] = source[offset + part];
			}
			bits &= bits - 1;
		}
	}
	return copied;
}

void objTileBufferReset(void) {
	wsvObjTileOffset = 0;
	objTilesConvertedFrame = 0;
	objTilesConvertedMaximum = 0;
	objBytesCopiedFrame = 0;
	objBytesCopiedMaximum = 0;
	objBufferSwapCount = 0;
	memset(previousDirty, 0, sizeof(previousDirty));
	memset(currentDirty, 0, sizeof(currentDirty));
	bufferInitialized = false;
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
				memset(DIRTYTILES + 0x100, 0, 0x100);
			}
		}
		previousFormat = format;
		modeInitialized = true;
		bufferInitialized = false;
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

	if (!bufferInitialized) {
		memset(previousDirty, 0xFF, sizeof(previousDirty));
		bufferInitialized = true;
	}

	const unsigned int sourceOffset = wsvObjTileOffset;
	const unsigned int destinationOffset = sourceOffset ^ 0x200;
	const unsigned int copied = seedChangedTiles(sourceOffset, destinationOffset);
	objBytesCopiedFrame = copied * OBJ_TILE_BYTES;
	if (objBytesCopiedFrame > objBytesCopiedMaximum) {
		objBytesCopiedMaximum = objBytesCopiedFrame;
	}

	wsvObjTileOffset = destinationOffset;
	memcpy(previousDirty, currentDirty, sizeof(previousDirty));
	objBufferSwapCount++;
}
