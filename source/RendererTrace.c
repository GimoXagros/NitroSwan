#ifdef WSC_VIDEO_TRACE

#include <nds.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "RendererTrace.h"
#include "Cart.h"
#include "Gfx.h"
#include "ObjTileBuffer.h"
#include "PaletteRaster.h"

#define TRACE_CAPACITY 128
#define TRACE_FILE "renderer-trace-r9.csv"

typedef struct {
	u32 sequence;
	u32 hostVBlank;
	u32 wsFrame;
	u32 spriteLatchFrame;
	u32 oamFrame;
	u32 epoch;
	u32 ticks;
	u32 vblankTicks;
	u32 bgSeedBytes;
	u32 bgSwaps;
	u32 cleanSkipped;
	u32 objBuildGeneration;
	u32 objReadyGeneration;
	u32 objPublishedGeneration;
	u32 objReadyTileGeneration;
	u32 objPublishedTileGeneration;
	u64 objTotalBytes;
	u32 objSeedBytes;
	u32 objPublishBytes;
	u16 scanline;
	u16 videoMode;
	u16 objBuildOffset;
	u16 objReadyOffset;
	u16 objPublishedOffset;
	u16 bgBuildOffset;
	u16 bgReadyOffset;
	u16 bgPublishedOffset;
	u16 dirtyObjTiles;
	u16 paletteEvents;
	u16 paletteDrops;
	u16 vcountIrqs;
	s16 objReadySlot;
	s16 objActiveSlot;
	s16 paletteCapture;
	s16 palettePending;
	s16 paletteReady;
	s16 paletteActive;
	u8 event;
} RendererTraceEntry;

static RendererTraceEntry traceRing[TRACE_CAPACITY];
static volatile u16 traceWrite;
static volatile u16 traceRead;
static volatile u32 traceDropped;
static u32 traceSequence;
static u32 hostVBlankCounter;
static bool traceFilesystemReady;
static bool traceHeaderWritten;
static char tracePath[1024];
static u32 traceEpoch;
static u32 vblankStart;
static bool traceTimerReady;
const void *rendererTraceOamSource;

// Diagnostic builds only; ARM9 timers 2/3 are unused by the emulator.
// Unsigned ticks: BUS_CLOCK / 64. Read high/low/high across cascade rollover.
static u32 traceTicks(void) {
	if (!traceTimerReady) return 0;
	u16 high, low;
	do {
		high = TIMER3_DATA;
		low = TIMER2_DATA;
	} while (high != TIMER3_DATA);
	return ((u32)high << 16) | low;
}

void rendererTraceReset(void) {
	traceEpoch++;
	rendererTraceOamSource = NULL;
}

static void rendererTraceRecord(char event) {
	ObjTileTraceState obj;
	PaletteRasterTraceState palette;
	const int oldIme = enterCriticalSection();
	objTileBufferGetTraceState(&obj);
	paletteRasterGetTraceState(&palette);
	const u16 next = (traceWrite + 1) % TRACE_CAPACITY;
	if (next == traceRead) {
		traceDropped++;
		leaveCriticalSection(oldIme);
		return;
	}
	RendererTraceEntry *entry = &traceRing[traceWrite];
	const bool wsCompletion = event == 'W';
	*entry = (RendererTraceEntry){
		.sequence = ++traceSequence,
		.hostVBlank = hostVBlankCounter,
		.wsFrame = obj.completedFrameGeneration,
		// No latch observation hook: never fabricate it from completion.
		.spriteLatchFrame = 0xFFFFFFFF,
		.oamFrame = obj.observedOamFrame,
		.epoch = traceEpoch,
		.ticks = traceTicks(),
		.vblankTicks = event == 'V' ? traceTicks() - vblankStart : 0,
		.bgSeedBytes = bgBytesCopiedFrame,
		.bgSwaps = bgBufferSwapCount,
		.cleanSkipped = skippedCleanGenerationCount,
		.objBuildGeneration = obj.objBuildGeneration,
		.objReadyGeneration = obj.readyFrameGeneration,
		.objPublishedGeneration = obj.publishedFrameGeneration,
		.objReadyTileGeneration = obj.readyTileGeneration,
		.objPublishedTileGeneration = obj.publishedTileGeneration,
		.objTotalBytes = objTotalBytes,
		.objSeedBytes = wsCompletion
			? obj.readySeedBytes : obj.publishedSeedBytes,
		.objPublishBytes = objPublishBytesHostFrame,
		.scanline = sphinx0.scanline,
		.videoMode = sphinx0.videoMode,
		.objBuildOffset = obj.objBuildOffset,
		.objReadyOffset = obj.objReadyOffset,
		.objPublishedOffset = obj.objPublishedOffset,
		.bgBuildOffset = obj.bgBuildOffset,
		.bgReadyOffset = obj.bgReadyOffset,
		.bgPublishedOffset = obj.bgPublishedOffset,
		.dirtyObjTiles = wsCompletion
			? obj.readyDirtyObjTiles : obj.publishedDirtyObjTiles,
		.paletteEvents = wsCompletion
			? palette.readyEvents : palette.activeEvents,
		.paletteDrops = wsCompletion
			? palette.readyDrops : palette.activeDrops,
		.vcountIrqs = palette.lastVCountIrqs,
		.objReadySlot = obj.readySlot,
		.objActiveSlot = obj.activeSlot,
		.paletteCapture = palette.captureFrame,
		.palettePending = palette.pendingFrame,
		.paletteReady = palette.readyFrame,
		.paletteActive = palette.activeFrame,
		.event = event,
	};
	traceWrite = next;
	leaveCriticalSection(oldIme);
}

void rendererTraceInit(bool filesystemReady) {
	traceFilesystemReady = filesystemReady;
	// Do not steal an occupied timer from an unexpected runtime/library.
	if (!(TIMER2_CR & TIMER_ENABLE) && !(TIMER3_CR & TIMER_ENABLE)) {
		TIMER2_DATA = 0;
		TIMER3_DATA = 0;
		TIMER3_CR = TIMER_ENABLE | TIMER_CASCADE;
		TIMER2_CR = TIMER_ENABLE | TIMER_DIV_64;
		traceTimerReady = true;
	}
}

void rendererTraceWSFrame(void) {
	rendererTraceRecord('W');
}

void rendererTraceHostVBlank(void) {
	rendererTraceRecord('V');
}

void rendererTraceSetDataDirectory(void) {
	// Called after ensureFolder(), while cwd is the selected supported data
	// folder. Retain its device-qualified path before ROM browsing changes cwd.
	char directory[sizeof(tracePath)];
	if (getcwd(directory, sizeof(directory)) == NULL) return;
	const int length = snprintf(tracePath, sizeof(tracePath), "%s/%s", directory, TRACE_FILE);
	if (length < 0 || (unsigned int)length >= sizeof(tracePath)) tracePath[0] = 0;
}

void rendererTraceHostVBlankBegin(void) {
	hostVBlankCounter++;
	vblankStart = traceTicks();
}

void rendererTraceFlush(void) {
	if (!traceFilesystemReady || !tracePath[0] || traceRead == traceWrite) {
		return;
	}
	FILE *file = fopen(tracePath, "a");
	if (file == NULL) {
		return;
	}
	if (!traceHeaderWritten) {
		fseek(file, 0, SEEK_END);
		if (ftell(file) == 0) {
			fputs("test_id,event,seq,host_vblank,ws_frame,scanline,sprite_latch_frame,oam_frame,video_mode,obj_build_gen,obj_ready_frame,obj_published_frame,obj_ready_tile_gen,obj_published_tile_gen,obj_build_bank,obj_ready_bank,obj_published_bank,bg_build_bank,bg_ready_bank,bg_published_bank,obj_dirty_tiles,obj_seed_bytes,obj_publish_bytes,obj_total_bytes,palette_capture,palette_pending,palette_ready,palette_active,palette_events,palette_drops,vcount_irqs,ring_drops,epoch,ticks,vblank_ticks,bg_seed_bytes,bg_swaps,clean_skipped,timer_available\n", file);
		}
		traceHeaderWritten = true;
	}
	// Snapshot the end, so IRQ producers cannot turn a slow flush into an
	// unbounded loop. The next batch is left for a later main-loop iteration.
	const u16 end = traceWrite;
	while (traceRead != end) {
		RendererTraceEntry entry;
		const int oldIme = enterCriticalSection();
		entry = traceRing[traceRead];
		traceRead = (traceRead + 1) % TRACE_CAPACITY;
		const u32 dropped = traceDropped;
		leaveCriticalSection(oldIme);
		const int result = fprintf(file,
			"manual,%c,%lu,%lu,%lu,%u,%lu,%lu,%u,%lu,%lu,%lu,%lu,%lu,%u,%u,%u,%u,%u,%u,%u,%lu,%lu,%llu,%d,%d,%d,%d,%u,%u,%u,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%u\n",
			entry.event, (unsigned long)entry.sequence,
			(unsigned long)entry.hostVBlank, (unsigned long)entry.wsFrame,
			entry.scanline, (unsigned long)entry.spriteLatchFrame,
			(unsigned long)entry.oamFrame, entry.videoMode,
			(unsigned long)entry.objBuildGeneration,
			(unsigned long)entry.objReadyGeneration,
			(unsigned long)entry.objPublishedGeneration,
			(unsigned long)entry.objReadyTileGeneration,
			(unsigned long)entry.objPublishedTileGeneration,
			entry.objBuildOffset, entry.objReadyOffset,
			entry.objPublishedOffset, entry.bgBuildOffset,
			entry.bgReadyOffset, entry.bgPublishedOffset,
			entry.dirtyObjTiles, (unsigned long)entry.objSeedBytes,
			(unsigned long)entry.objPublishBytes,
			(unsigned long long)entry.objTotalBytes,
			entry.paletteCapture, entry.palettePending,
			entry.paletteReady, entry.paletteActive,
			entry.paletteEvents, entry.paletteDrops, entry.vcountIrqs,
			(unsigned long)dropped, (unsigned long)entry.epoch,
			(unsigned long)entry.ticks, (unsigned long)entry.vblankTicks,
			(unsigned long)entry.bgSeedBytes, (unsigned long)entry.bgSwaps,
			(unsigned long)entry.cleanSkipped, traceTimerReady);
		if (result < 0) {
			const int oldIme = enterCriticalSection();
			traceDropped++;
			leaveCriticalSection(oldIme);
			break;
		}
	}
	fclose(file);
}

#endif
