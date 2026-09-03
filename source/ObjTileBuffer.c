#include <nds.h>
#include <string.h>

#include "Cart.h"
#include "Gfx.h"
#include "ObjTileBuffer.h"

#define OBJ_TILE_COUNT 512
#define OBJ_TILE_BYTES 32
#define OBJ_BANK_BYTES (OBJ_TILE_COUNT * OBJ_TILE_BYTES)
#define BG_BANK_BYTES 0x8000
#define BG_BASE_OFFSET 0x8000
#define BG_ALT_OFFSET 0x8000
#define COLOR_TILE_MARKERS 1024
#define MONO_TILE_MARKERS 256

volatile u16 wsvObjTileOffset;
volatile u16 wsvObjReadyTileOffset;
volatile u16 wsvBgTileOffset;
volatile u16 wsvBgReadyTileOffset;
u8 wsvObjTileSnapshots[OBJ_BANK_BYTES * 2] __attribute__((aligned(4)));
volatile u16 objTilesConvertedFrame;
volatile u16 objTilesConvertedMaximum;
volatile u32 objBytesCopiedFrame;
volatile u32 objBytesCopiedMaximum;
volatile u32 objBufferSwapCount;
volatile u16 bgDirtyMarkersFrame;
volatile u16 bgDirtyMarkersMaximum;
volatile u32 bgBytesCopiedFrame;
volatile u32 bgBytesCopiedMaximum;
volatile u32 bgBufferSwapCount;

static bool modeInitialized;
static u8 previousFormat;
static volatile bool objSnapshotEnabled;
static u32 objBuildGeneration;
static volatile u32 objReadyGeneration;
static u32 objPublishedGeneration;

static unsigned int captureDirtyMarkers(const u8 *dirty,
	unsigned int markerCount, unsigned int cleanMask) {
	unsigned int count = 0;
	const u32 cleanWord = cleanMask * 0x01010101U;
	for (unsigned int group = 0; group < markerCount / 4; group++) {
		u32 markers;
		memcpy(&markers, &dirty[group * 4], sizeof(markers));
		if (markers == cleanWord) {
			continue;
		}
		for (unsigned int part = 0; part < 4; part++) {
			if (((markers >> (part * 8)) & cleanMask) == 0) {
				count++;
			}
		}
	}
	return count;
}

static void seedBgBank(unsigned int sourceOffset, unsigned int destinationOffset) {
	const void *source = (const u8 *)BG_GFX + BG_BASE_OFFSET + sourceOffset;
	void *destination = (u8 *)BG_GFX + BG_BASE_OFFSET + destinationOffset;

	// Keep the displayed character base immutable until VBlank. This is decoded
	// tile storage, not a framebuffer, and uses otherwise unused main BG VRAM.
	memcpy(destination, source, BG_BANK_BYTES);
}

static void seedObjBank(unsigned int sourceOffset, unsigned int destinationOffset) {
	const void *source = wsvObjTileSnapshots + sourceOffset * OBJ_TILE_BYTES;
	void *destination = wsvObjTileSnapshots + destinationOffset * OBJ_TILE_BYTES;

	// A 60 Hz host slice can finish one 75 Hz WS frame and begin the next before
	// VBlank. Keep both build generations in main RAM so neither can overwrite
	// the OBJ VRAM generation still being scanned out. Clean frames do not copy.
	memcpy(destination, source, OBJ_BANK_BYTES);
}

void objTileBufferReset(void) {
	wsvObjTileOffset = 0;
	wsvObjReadyTileOffset = 0;
	wsvBgTileOffset = 0;
	wsvBgReadyTileOffset = 0;
	memset(wsvObjTileSnapshots, 0, sizeof(wsvObjTileSnapshots));
	objTilesConvertedFrame = 0;
	objTilesConvertedMaximum = 0;
	objBytesCopiedFrame = 0;
	objBytesCopiedMaximum = 0;
	objBufferSwapCount = 0;
	bgDirtyMarkersFrame = 0;
	bgDirtyMarkersMaximum = 0;
	bgBytesCopiedFrame = 0;
	bgBytesCopiedMaximum = 0;
	bgBufferSwapCount = 0;
	modeInitialized = false;
	previousFormat = 0;
	objSnapshotEnabled = false;
	objBuildGeneration = 1;
	objReadyGeneration = 1;
	objPublishedGeneration = 0;
}

void objTileBufferBeginFrame(unsigned int videoMode) {
	objTilesConvertedFrame = 0;
	objBytesCopiedFrame = 0;
	bgDirtyMarkersFrame = 0;
	bgBytesCopiedFrame = 0;

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
	}

	const bool color4bpp = (format & 0xC0) == 0xC0;
	const unsigned int cleanMask = color4bpp
		? ((videoMode & 0x20) != 0 ? 0x10 : 0x20)
		: 0x44;
	const u8 *dirty = DIRTYTILES + (color4bpp ? 0x200 : 0x100);
	const unsigned int markerCount = color4bpp
		? COLOR_TILE_MARKERS : MONO_TILE_MARKERS;
	const unsigned int bgDirty = captureDirtyMarkers(dirty, markerCount, cleanMask);
	bgDirtyMarkersFrame = bgDirty;
	if (bgDirty > bgDirtyMarkersMaximum) {
		bgDirtyMarkersMaximum = bgDirty;
	}
	if (bgDirty != 0) {
		const unsigned int sourceOffset = wsvBgTileOffset;
		const unsigned int destinationOffset = sourceOffset ^ BG_ALT_OFFSET;
		seedBgBank(sourceOffset, destinationOffset);
		wsvBgTileOffset = destinationOffset;
		bgBytesCopiedFrame = BG_BANK_BYTES;
		if (bgBytesCopiedFrame > bgBytesCopiedMaximum) {
			bgBytesCopiedMaximum = bgBytesCopiedFrame;
		}
		bgBufferSwapCount++;
	}

	if (!color4bpp) {
		objSnapshotEnabled = false;
		wsvObjTileOffset = 0;
		return;
	}
	objSnapshotEnabled = true;

	const unsigned int converted = captureDirtyMarkers(dirty, OBJ_TILE_COUNT, cleanMask);
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
	objBuildGeneration++;
	objBufferSwapCount++;
}

void videoTileBufferFrameComplete(void) {
	// DSpico can begin the following 75 Hz WS frame before the next 60 Hz host
	// VBlank. Only publish the character bank belonging to a completed frame.
	wsvBgReadyTileOffset = wsvBgTileOffset;
	if (objSnapshotEnabled) {
		// Pointer and generation are separate stores, not an atomic publication.
		// If the preceding ready generation is still pending, VBlank can observe
		// a newer pointer with the older generation. See the r7 baseline audit;
		// coordinated OBJ/OAM ownership remains a separate renderer follow-up.
		wsvObjReadyTileOffset = wsvObjTileOffset;
		objReadyGeneration = objBuildGeneration;
	}
}

void videoTileBufferVBlank(void) {
	if (objSnapshotEnabled) {
		const unsigned int readyGeneration = objReadyGeneration;
		if (readyGeneration != objPublishedGeneration) {
			const void *source = wsvObjTileSnapshots
				+ wsvObjReadyTileOffset * OBJ_TILE_BYTES;
			memcpy((void *)SPRITE_GFX, source, OBJ_BANK_BYTES);
			objPublishedGeneration = readyGeneration;
		}
	}

	const unsigned int tileBase = 2 + (wsvBgReadyTileOffset >> 14);
	const u16 tileMask = BG_TILE_BASE(15);
	REG_BG0CNT = (GFX_BG0CNT & ~tileMask) | BG_TILE_BASE(tileBase);
	REG_BG1CNT = (GFX_BG1CNT & ~tileMask) | BG_TILE_BASE(tileBase);
}
