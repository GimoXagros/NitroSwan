#include <nds.h>
#include <string.h>

#include "Cart.h"
#include "Gfx.h"
#include "ObjTileBuffer.h"
#include "PaletteRaster.h"

#define OBJ_TILE_COUNT 512
#define OBJ_TILE_BYTES 32
#define OBJ_BANK_BYTES (OBJ_TILE_COUNT * OBJ_TILE_BYTES)
#define BG_BANK_BYTES 0x8000
#define BG_BASE_OFFSET 0x8000
#define BG_ALT_OFFSET 0x8000
#define COLOR_TILE_MARKERS 1024
#define MONO_TILE_MARKERS 256
#define OBJ_PALETTE_BYTES 0x200
#define OAM_SNAPSHOT_BYTES 0x400

typedef struct {
	u32 frameGeneration;
	u32 tileGeneration;
	u16 objTileOffset;
	u16 bgTileOffset;
	u16 dirtyObjTiles;
	u16 seedBytes;
	u8 objSnapshotEnabled;
	u8 reserved[3];
} CompletedFrameDescriptor;

typedef struct {
	CompletedFrameDescriptor descriptor;
	u8 oam[OAM_SNAPSHOT_BYTES];
	u16 objPalette[OBJ_PALETTE_BYTES / sizeof(u16)];
} CompletedFrameSlot;

volatile u16 wsvObjTileOffset;
volatile u16 wsvObjReadyTileOffset;
volatile u16 wsvBgTileOffset;
volatile u16 wsvBgReadyTileOffset;
u8 wsvObjTileSnapshots[OBJ_BANK_BYTES * 2] __attribute__((aligned(4)));
volatile u16 objTilesConvertedWSFrame;
volatile u16 objTilesConvertedMaximum;
volatile u32 objSeedBytesFrame;
volatile u32 objPublishBytesHostFrame;
volatile u64 objTotalBytes;
volatile u32 objSeedBytesMaximum;
volatile u32 objBufferSwapCount;
volatile u32 objPublicationCount;
volatile u32 skippedCleanGenerationCount;
volatile u16 bgDirtyMarkersFrame;
volatile u16 bgDirtyMarkersMaximum;
volatile u32 bgBytesCopiedFrame;
volatile u32 bgBytesCopiedMaximum;
volatile u32 bgBufferSwapCount;

static bool modeInitialized;
static u8 previousFormat;
static volatile bool objSnapshotEnabled;
static volatile bool rendererQuiesced = true;
static u32 objBuildGeneration;
static u32 completedFrameGeneration;
static u32 publishedFrameGeneration;
static u32 publishedTileGeneration;
static const void *publishedOamSource;
static CompletedFrameSlot completedSlots[3] __attribute__((aligned(4)));
static volatile int captureFrameSlot;
static volatile int pendingFrameSlot = -1;
static volatile int readyFrameSlot;
static volatile int activeFrameSlot;

static void addObjTransferBytes(u32 bytes) {
	const int oldIme = enterCriticalSection();
	objTotalBytes += bytes;
	leaveCriticalSection(oldIme);
}

static int nextCompletedSlot(int active, int ready) {
	for (int slot = 0; slot < 3; slot++) {
		if (slot != active && slot != ready) {
			return slot;
		}
	}
	return 0;
}

static u32 nextGeneration(u32 generation) {
	generation++;
	return generation != 0 ? generation : 1;
}

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

void objTileBufferQuiesce(void) {
	const int oldIme = enterCriticalSection();
	rendererQuiesced = true;
	objSnapshotEnabled = false;
	readyFrameSlot = -1;
	pendingFrameSlot = -1;
	activeFrameSlot = -1;
	publishedFrameGeneration = 0;
	publishedOamSource = NULL;
	leaveCriticalSection(oldIme);
}

void objTileBufferReset(void) {
	objTileBufferQuiesce();
	wsvObjTileOffset = 0;
	wsvObjReadyTileOffset = 0;
	wsvBgTileOffset = 0;
	wsvBgReadyTileOffset = 0;
	memset(wsvObjTileSnapshots, 0, sizeof(wsvObjTileSnapshots));
	memset(completedSlots, 0, sizeof(completedSlots));
	objTilesConvertedWSFrame = 0;
	objTilesConvertedMaximum = 0;
	objSeedBytesFrame = 0;
	objPublishBytesHostFrame = 0;
	objTotalBytes = 0;
	objSeedBytesMaximum = 0;
	objBufferSwapCount = 0;
	objPublicationCount = 0;
	skippedCleanGenerationCount = 0;
	bgDirtyMarkersFrame = 0;
	bgDirtyMarkersMaximum = 0;
	bgBytesCopiedFrame = 0;
	bgBytesCopiedMaximum = 0;
	bgBufferSwapCount = 0;
	modeInitialized = false;
	previousFormat = 0;
	objBuildGeneration = 1;
	completedFrameGeneration = 1;
	publishedTileGeneration = 0;
	captureFrameSlot = 0;
}

void objTileBufferBeginFrame(unsigned int videoMode) {
	objTilesConvertedWSFrame = 0;
	objSeedBytesFrame = 0;
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
	objTilesConvertedWSFrame = converted;
	if (converted > objTilesConvertedMaximum) {
		objTilesConvertedMaximum = converted;
	}
	if (converted == 0) {
		return;
	}

	const unsigned int sourceOffset = wsvObjTileOffset;
	const unsigned int destinationOffset = sourceOffset ^ 0x200;
	seedObjBank(sourceOffset, destinationOffset);
	objSeedBytesFrame = OBJ_BANK_BYTES;
	addObjTransferBytes(OBJ_BANK_BYTES);
	if (objSeedBytesFrame > objSeedBytesMaximum) {
		objSeedBytesMaximum = objSeedBytesFrame;
	}

	wsvObjTileOffset = destinationOffset;
	objBuildGeneration = nextGeneration(objBuildGeneration);
	objBufferSwapCount++;
}

void objTileBufferCompleteStateRestore(unsigned int videoMode) {
	previousFormat = videoMode & 0xE0;
	modeInitialized = true;
	objSnapshotEnabled = (previousFormat & 0xC0) == 0xC0;
}

void videoTileBufferFrameComplete(const void *completedOam) {
	CompletedFrameSlot *slot = &completedSlots[captureFrameSlot];
	memcpy(slot->oam, completedOam, OAM_SNAPSHOT_BYTES);
	completedFrameGeneration = nextGeneration(completedFrameGeneration);
	slot->descriptor = (CompletedFrameDescriptor){
		.frameGeneration = completedFrameGeneration,
		.tileGeneration = objBuildGeneration,
		.objTileOffset = wsvObjTileOffset,
		.bgTileOffset = wsvBgTileOffset,
		.dirtyObjTiles = objTilesConvertedWSFrame,
		.seedBytes = objSeedBytesFrame,
		.objSnapshotEnabled = objSnapshotEnabled,
	};
	if (objSnapshotEnabled) {
		memcpy(slot->objPalette, EMUPALBUFF + 0x100,
			OBJ_PALETTE_BYTES);
		if (objTilesConvertedWSFrame == 0) {
			skippedCleanGenerationCount++;
		}
	}
	addObjTransferBytes(OAM_SNAPSHOT_BYTES +
		(objSnapshotEnabled ? OBJ_PALETTE_BYTES : 0));

	pendingFrameSlot = captureFrameSlot;
}

void videoTileBufferFrameCommit(void) {
	if (pendingFrameSlot < 0) {
		return;
	}

	// OBJ/OAM/BG and palette ready indices become visible together. All large
	// copies completed before this short metadata-only critical section.
	const int oldIme = enterCriticalSection();
	readyFrameSlot = pendingFrameSlot;
	CompletedFrameSlot *slot = &completedSlots[readyFrameSlot];
	wsvObjReadyTileOffset = slot->descriptor.objTileOffset;
	wsvBgReadyTileOffset = slot->descriptor.bgTileOffset;
	captureFrameSlot = nextCompletedSlot(activeFrameSlot, readyFrameSlot);
	pendingFrameSlot = -1;
	paletteRasterCommitFrame();
	rendererQuiesced = false;
	leaveCriticalSection(oldIme);
}

bool videoTileBufferIsQuiesced(void) {
	return rendererQuiesced;
}

const void *videoTileBufferVBlank(void) {
	objPublishBytesHostFrame = 0;
	if (readyFrameSlot >= 0) {
		activeFrameSlot = readyFrameSlot;
		readyFrameSlot = -1;
	}
	const CompletedFrameSlot *slot = activeFrameSlot >= 0
		? &completedSlots[activeFrameSlot] : NULL;
	const CompletedFrameDescriptor completed = slot != NULL
		? slot->descriptor : (CompletedFrameDescriptor){0};
	if (completed.frameGeneration != 0 &&
		completed.frameGeneration != publishedFrameGeneration) {
		if (completed.objSnapshotEnabled) {
			if (completed.tileGeneration != publishedTileGeneration) {
				const void *source = wsvObjTileSnapshots
					+ completed.objTileOffset * OBJ_TILE_BYTES;
				memcpy((void *)SPRITE_GFX, source, OBJ_BANK_BYTES);
				objPublishBytesHostFrame = OBJ_BANK_BYTES;
				addObjTransferBytes(OBJ_BANK_BYTES);
				publishedTileGeneration = completed.tileGeneration;
			}
			memcpy(EMUPALBUFF + 0x100, slot->objPalette,
				OBJ_PALETTE_BYTES);
		}
		publishedOamSource = slot->oam;
		publishedFrameGeneration = completed.frameGeneration;
		objPublicationCount++;
	}

	const unsigned int bgOffset = completed.frameGeneration != 0
		? completed.bgTileOffset : wsvBgReadyTileOffset;
	const unsigned int tileBase = 2 + (bgOffset >> 14);
	const u16 tileMask = BG_TILE_BASE(15);
	REG_BG0CNT = (GFX_BG0CNT & ~tileMask) | BG_TILE_BASE(tileBase);
	REG_BG1CNT = (GFX_BG1CNT & ~tileMask) | BG_TILE_BASE(tileBase);
	return publishedOamSource;
}

#ifdef WSC_VIDEO_TRACE
void objTileBufferGetTraceState(ObjTileTraceState *state) {
	const CompletedFrameDescriptor *ready = readyFrameSlot >= 0
		? &completedSlots[readyFrameSlot].descriptor : NULL;
	const CompletedFrameDescriptor *active = activeFrameSlot >= 0
		? &completedSlots[activeFrameSlot].descriptor : NULL;
	*state = (ObjTileTraceState){
		.completedFrameGeneration = completedFrameGeneration,
		.objBuildGeneration = objBuildGeneration,
		.readyFrameGeneration = ready ? ready->frameGeneration : 0,
		.readyTileGeneration = ready ? ready->tileGeneration : 0,
		.readyDirtyObjTiles = ready ? ready->dirtyObjTiles : 0,
		.readySeedBytes = ready ? ready->seedBytes : 0,
		.publishedFrameGeneration = publishedFrameGeneration,
		.publishedTileGeneration = publishedTileGeneration,
		.publishedDirtyObjTiles = active ? active->dirtyObjTiles : 0,
		.publishedSeedBytes = active ? active->seedBytes : 0,
		.objBuildOffset = wsvObjTileOffset,
		.objReadyOffset = ready ? ready->objTileOffset : 0,
		.objPublishedOffset = active ? active->objTileOffset : 0,
		.bgBuildOffset = wsvBgTileOffset,
		.bgReadyOffset = ready ? ready->bgTileOffset : 0,
		.bgPublishedOffset = active ? active->bgTileOffset : 0,
		.readySlot = readyFrameSlot,
		.activeSlot = activeFrameSlot,
	};
}
#endif
