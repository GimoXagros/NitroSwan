#include <nds.h>
#include <string.h>

#include "PaletteRaster.h"
#include "Cart.h"
#include "Gfx.h"
#include "ObjTileBuffer.h"

#define WS_VISIBLE_LINES 144
#define DS_GAME_TOP ((SCREEN_HEIGHT - WS_VISIBLE_LINES) / 2)
// WSC palette entries 0-127 feed the DS background palette. Entries 128-255
// are converted into OBJ_PALETTE by paletteTxAll and must not be replayed into
// the upper half of BG_PALETTE.
#define WS_BG_COLORS 128
#define MAX_BG_PALETTE_DELTAS 384
#define PALETTE_FRAME_COUNT 3

typedef struct {
	u8 line;
	u8 index;
	u16 color;
} PaletteDelta;

typedef struct {
	u16 base[WS_BG_COLORS];
	u16 lineStart[WS_VISIBLE_LINES + 1];
	PaletteDelta delta[MAX_BG_PALETTE_DELTAS];
	u16 count;
	u16 dropped;
} PaletteDeltaFrame;

static PaletteDeltaFrame frames[PALETTE_FRAME_COUNT];
static volatile int captureFrame;
static volatile int readyFrame = -1;
static volatile int activeFrame = -1;
static volatile u16 replayCursor;
static bool rasterEnabled;
bool wsvVideoWriteCallbackEnabled;
volatile u16 paletteRasterEventsFrame;
volatile u16 paletteRasterEventsMaximum;
volatile u16 paletteRasterDroppedFrame;
volatile u16 paletteRasterDroppedMaximum;
volatile u16 paletteRasterVCountIrqsFrame;
volatile u16 paletteRasterVCountIrqsMaximum;
static u16 previousPalette[WS_BG_COLORS];
static u16 previousBackdrop;

static inline u16 mapColor(u16 rawColor) {
	return MAPPED_RGB[rawColor & 0x0FFF];
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
	frame->base[0] = mapColor(previousBackdrop);
	for (unsigned int index = 1; index < WS_BG_COLORS; index++) {
		const u16 rawColor = palette[index];
		previousPalette[index] = rawColor;
		frame->base[index] = mapColor(rawColor);
	}
}

static void resetCaptureFrame(PaletteDeltaFrame *frame) {
	frame->count = 0;
	frame->dropped = 0;
	memset(frame->lineStart, 0, sizeof(frame->lineStart));
}

static void setBaseColor(PaletteDeltaFrame *frame, unsigned int index, u16 rawColor) {
	if (index < WS_BG_COLORS) {
		frame->base[index] = mapColor(rawColor);
	}
}

static void appendDelta(unsigned int line, unsigned int index, u16 rawColor) {
	PaletteDeltaFrame *frame = &frames[captureFrame];
	const u16 color = mapColor(rawColor);
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

void paletteRasterConfigure(const WsHeader *header) {
	const bool colorHardware = header != NULL && gSOC != SOC_ASWAN;
	rasterEnabled = colorHardware;
	wsvVideoWriteCallbackEnabled = colorHardware;
	readyFrame = -1;
	activeFrame = -1;
	captureFrame = 0;
	replayCursor = 0;
	paletteRasterEventsFrame = 0;
	paletteRasterEventsMaximum = 0;
	paletteRasterDroppedFrame = 0;
	paletteRasterDroppedMaximum = 0;
	paletteRasterVCountIrqsFrame = 0;
	paletteRasterVCountIrqsMaximum = 0;
	objTileBufferReset();
#if PALETTE_RASTER_DIAGNOSTIC != PALETTE_RASTER_CAPTURE_ONLY
	stopReplayIrq();
#endif
	if (colorHardware) {
		resetCaptureFrame(&frames[0]);
		snapshotBase(&frames[0]);
	}
}

void paletteRasterCapturePaletteWrite(unsigned int address) {
	if (!wsvVideoWriteCallbackEnabled || address < 0xFE00 || address > 0xFFFF) {
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

void wsvVideoRegisterWriteCallback(unsigned int port) {
	if (wsvVideoWriteCallbackEnabled && port == 0x01) {
		captureBackdropWrite();
	}
}

void paletteRasterFrameComplete(void) {
	if (!rasterEnabled) {
		return;
	}

	PaletteDeltaFrame *finished = &frames[captureFrame];
	paletteRasterEventsFrame = finished->count;
	paletteRasterDroppedFrame = finished->dropped;
	if (finished->count > paletteRasterEventsMaximum) {
		paletteRasterEventsMaximum = finished->count;
	}
	if (finished->dropped > paletteRasterDroppedMaximum) {
		paletteRasterDroppedMaximum = finished->dropped;
	}
	u16 cursor = 0;
	for (unsigned int line = 0; line < WS_VISIBLE_LINES; line++) {
		finished->lineStart[line] = cursor;
		while (cursor < finished->count && finished->delta[cursor].line == line) {
			cursor++;
		}
	}
	finished->lineStart[WS_VISIBLE_LINES] = finished->count;

	readyFrame = captureFrame;
	captureFrame = nextFreeFrame(activeFrame, readyFrame);
	resetCaptureFrame(&frames[captureFrame]);
	snapshotBase(&frames[captureFrame]);
}

void paletteRasterVBlank(void) {
	if (paletteRasterVCountIrqsFrame > paletteRasterVCountIrqsMaximum) {
		paletteRasterVCountIrqsMaximum = paletteRasterVCountIrqsFrame;
	}
	paletteRasterVCountIrqsFrame = 0;
	if (!rasterEnabled || readyFrame < 0) {
		stopReplayIrq();
		return;
	}

#if PALETTE_RASTER_DIAGNOSTIC == PALETTE_RASTER_CAPTURE_ONLY
	stopReplayIrq();
	return;
#else
	activeFrame = readyFrame;
	readyFrame = -1;
	PaletteDeltaFrame *active = &frames[activeFrame];
#if PALETTE_RASTER_DIAGNOSTIC == PALETTE_RASTER_BG_ONLY
	for (unsigned int index = 0; index < WS_BG_COLORS; index++) {
		BG_PALETTE[index] = active->base[index];
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
	paletteRasterVCountIrqsFrame++;
	if (replayCursor >= active->count) {
		stopReplayIrq();
		return;
	}
	const u8 line = active->delta[replayCursor].line;
	do {
		const PaletteDelta *event = &active->delta[replayCursor++];
		BG_PALETTE[event->index] = event->color;
	} while (replayCursor < active->count && active->delta[replayCursor].line == line);

	if (replayCursor < active->count) {
		SetYtrigger(DS_GAME_TOP + active->delta[replayCursor].line);
	}
	else {
		stopReplayIrq();
	}
#endif
}
