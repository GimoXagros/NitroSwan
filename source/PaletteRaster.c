#include <nds.h>

#include "PaletteRaster.h"
#include "Cart.h"
#include "Gfx.h"

#define WS_VISIBLE_LINES 144
#define DS_GAME_TOP ((SCREEN_HEIGHT - WS_VISIBLE_LINES) / 2)
#define WS_BG_COLORS 128
#define MAX_BG_PALETTE_DELTAS 384
#define PALETTE_FRAME_COUNT 3

typedef struct {
	u8 line;
	u8 index;
	u16 color; // Raw RGB12; map on replay after any host gamma/contrast change.
} PaletteDelta;

typedef struct {
	u16 base[WS_BG_COLORS];
	PaletteDelta delta[MAX_BG_PALETTE_DELTAS];
	u16 count;
	u16 dropped;
	bool replayable;
} PaletteDeltaFrame;

static PaletteDeltaFrame frames[PALETTE_FRAME_COUNT];
static volatile int captureFrame;
static volatile int readyFrame = -1;
static volatile int activeFrame = -1;
static volatile u16 replayCursor;
static bool rasterEnabled;
bool wsvVideoWriteCallbackEnabled;
static u16 previousPalette[WS_BG_COLORS];
static u16 previousBackdrop;

static inline u16 mapColor(u16 rawColor) {
	return MAPPED_RGB[rawColor & 0x0FFF];
}

static bool directColorPalette(void) {
	// Mono and color 2bpp require paletteTxAll's expanded palette layout.
	return (sphinx0.videoMode & 0xC0) == 0xC0;
}

static bool canCapturePalette(void) {
	PaletteDeltaFrame *frame = &frames[captureFrame];
	if (!directColorPalette()) {
		frame->replayable = false;
	}
	// An observed incompatible mode invalidates this whole capture.
	return frame->replayable;
}

static inline u16 backdropRawColor(const u16 *palette) {
	if ((sphinx0.lcdControl & 1) == 0) {
		return sphinx0.defaultBgCol & 0x0FFF;
	}
	return palette[sphinx0.bgColor] & 0x0FFF;
}

static void stopReplayIrq(void) {
	irqDisable(IRQ_VCOUNT);
	REG_DISPSTAT &= ~DISP_YTRIGGER_IRQ;
}

static void snapshotBase(PaletteDeltaFrame *frame) {
	const u16 *palette = (const u16 *)sphinx0.paletteRAM;
	previousBackdrop = backdropRawColor(palette);
	frame->base[0] = previousBackdrop & 0x0FFF;
	for (unsigned int index = 1; index < WS_BG_COLORS; index++) {
		const u16 rawColor = palette[index];
		previousPalette[index] = rawColor;
		frame->base[index] = rawColor & 0x0FFF;
	}
}

static void resetCaptureFrame(PaletteDeltaFrame *frame) {
	frame->count = 0;
	frame->dropped = 0;
	frame->replayable = directColorPalette();
}

static void setBaseColor(PaletteDeltaFrame *frame, unsigned int index, u16 rawColor) {
	if (index < WS_BG_COLORS) {
		frame->base[index] = rawColor & 0x0FFF;
	}
}

static void appendDelta(unsigned int line, unsigned int index, u16 rawColor) {
	PaletteDeltaFrame *frame = &frames[captureFrame];
	const u16 color = rawColor & 0x0FFF;
	for (int event = frame->count - 1;
		event >= 0 && frame->delta[event].line == line; event--) {
		if (frame->delta[event].index == index) {
			frame->delta[event].color = color;
			return;
		}
	}
	if (frame->count < MAX_BG_PALETTE_DELTAS) {
		frame->delta[frame->count++] =
			(PaletteDelta){(u8)line, (u8)index, color};
	}
	else {
		frame->dropped++;
	}
}

static void captureBackdropWrite(void) {
	if (!canCapturePalette()) {
		return;
	}
	const u16 *palette = (const u16 *)sphinx0.paletteRAM;
	const u16 backdrop = backdropRawColor(palette);
	if (backdrop == previousBackdrop) {
		return;
	}
	previousBackdrop = backdrop;
	const u32 line = sphinx0.scanline;
	if (line < WS_VISIBLE_LINES - 1) {
		appendDelta(line + 1, 0, backdrop);
	}
	else if (line >= WS_VISIBLE_LINES) {
		setBaseColor(&frames[captureFrame], 0, backdrop);
	}
}

static int nextFreeFrame(int active, int ready) {
	for (int index = 0; index < PALETTE_FRAME_COUNT; index++) {
		if (index != active && index != ready) {
			return index;
		}
	}
	return 0;
}

void paletteRasterSuspend(void) {
	const int oldIme = enterCriticalSection();
	wsvVideoWriteCallbackEnabled = false;
	rasterEnabled = false;
	readyFrame = -1;
	activeFrame = -1;
	replayCursor = 0;
	stopReplayIrq();
	leaveCriticalSection(oldIme);
}

void paletteRasterConfigure(const WsHeader *header) {
	paletteRasterSuspend();
	// Select emulated hardware, not a title or a particular ROM dump.
	const bool colorHardware = header != NULL && gSOC != SOC_ASWAN;
	captureFrame = 0;
	if (colorHardware) {
		resetCaptureFrame(&frames[0]);
		snapshotBase(&frames[0]);
	}
	const int oldIme = enterCriticalSection();
	rasterEnabled = colorHardware;
	wsvVideoWriteCallbackEnabled = colorHardware;
	leaveCriticalSection(oldIme);
}

void paletteRasterCapturePaletteWrite(unsigned int address) {
	if (!wsvVideoWriteCallbackEnabled || address < 0xFE00 || address > 0xFFFF) {
		return;
	}
	if (!canCapturePalette()) {
		return;
	}
	const u16 *palette = (const u16 *)sphinx0.paletteRAM;
	const unsigned int index = (address - 0xFE00) >> 1;
	const u16 rawColor = palette[index];
	const u32 line = sphinx0.scanline;
	if (index > 0 && index < WS_BG_COLORS && rawColor != previousPalette[index]) {
		previousPalette[index] = rawColor;
		if (line < WS_VISIBLE_LINES - 1) {
			appendDelta(line + 1, index, rawColor);
		}
		else if (line >= WS_VISIBLE_LINES) {
			setBaseColor(&frames[captureFrame], index, rawColor);
		}
	}
	if (index == sphinx0.bgColor) {
		captureBackdropWrite();
	}
}

// The host assembly entry aligns the stack from either Sphinx write path.
void paletteRasterCaptureRegisterWrite(unsigned int port) {
	if (wsvVideoWriteCallbackEnabled && port == 0x01) {
		captureBackdropWrite();
	}
}

void paletteRasterFrameComplete(void) {
	if (!rasterEnabled) {
		return;
	}

	// VBlank can consume/clear readyFrame between the argument loads below.
	// Keep excluding the completed slot even after it becomes active.
	const int finishedFrame = captureFrame;
	if (!canCapturePalette()) {
		frames[finishedFrame].count = 0;
		frames[finishedFrame].dropped = 0;
	}
	// Publish unsupported frames too: they must retire an older color replay.
	readyFrame = finishedFrame;
	captureFrame = nextFreeFrame(activeFrame, finishedFrame);
	resetCaptureFrame(&frames[captureFrame]);
	snapshotBase(&frames[captureFrame]);
}

void paletteRasterVBlank(void) {
	if (!rasterEnabled || (readyFrame < 0 && activeFrame < 0)) {
		stopReplayIrq();
		return;
	}

#if PALETTE_RASTER_DIAGNOSTIC == PALETTE_RASTER_CAPTURE_ONLY
	stopReplayIrq();
	return;
#else
	if (readyFrame >= 0) {
		activeFrame = readyFrame;
		readyFrame = -1;
	}
	PaletteDeltaFrame *active = &frames[activeFrame];
	// Eligibility belongs to the completed frame, not the next live mode.
	if (!active->replayable) {
		replayCursor = 0;
		stopReplayIrq();
		return;
	}
#if PALETTE_RASTER_DIAGNOSTIC == PALETTE_RASTER_BG_ONLY
	for (unsigned int index = 0; index < WS_BG_COLORS; index++) {
		BG_PALETTE[index] = mapColor(active->base[index]);
	}
#endif
	replayCursor = 0;
	if (active->count == 0) {
		stopReplayIrq();
		return;
	}
	SetYtrigger(DS_GAME_TOP + active->delta[0].line);
	REG_DISPSTAT |= DISP_YTRIGGER_IRQ;
	irqEnable(IRQ_VCOUNT);
#endif
}

void paletteRasterVCountIrq(void) {
#if PALETTE_RASTER_DIAGNOSTIC == PALETTE_RASTER_CAPTURE_ONLY
	stopReplayIrq();
#else
	const int frameIndex = activeFrame;
	if (!rasterEnabled || frameIndex < 0) {
		stopReplayIrq();
		return;
	}

	PaletteDeltaFrame *active = &frames[frameIndex];
	if (!active->replayable) {
		stopReplayIrq();
		return;
	}
	if (replayCursor >= active->count) {
		stopReplayIrq();
		return;
	}
	const u8 line = active->delta[replayCursor].line;
	do {
		const PaletteDelta *event = &active->delta[replayCursor++];
		BG_PALETTE[event->index] = mapColor(event->color);
	} while (replayCursor < active->count && active->delta[replayCursor].line == line);

	if (replayCursor < active->count) {
		SetYtrigger(DS_GAME_TOP + active->delta[replayCursor].line);
	}
	else {
		stopReplayIrq();
	}
#endif
}
