#include <nds.h>
#include <string.h>

#include "PaletteRaster.h"
#include "Gfx.h"

#define WS_VISIBLE_LINES 144
#define DS_GAME_TOP ((SCREEN_HEIGHT - WS_VISIBLE_LINES) / 2)
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
bool wsvScanlineCallbackEnabled;
static u16 previousPalette[WS_BG_COLORS];

static inline u16 mapColor(u16 rawColor) {
	return MAPPED_RGB[rawColor & 0x0FFF];
}

static void stopReplayIrq(void) {
	irqDisable(IRQ_VCOUNT);
	REG_DISPSTAT &= ~DISP_YTRIGGER_IRQ;
}

static void snapshotBase(PaletteDeltaFrame *frame) {
	const u16 *palette = (const u16 *)sphinx0.paletteRAM;
	frame->base[0] = EMUPALBUFF[0];
	for (unsigned int index = 1; index < WS_BG_COLORS; index++) {
		const u16 rawColor = palette[index];
		previousPalette[index] = rawColor;
		frame->base[index] = mapColor(rawColor);
	}
}

static void resetCaptureFrame(PaletteDeltaFrame *frame) {
	frame->count = 0;
	frame->dropped = 0;
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
	const bool isOnePiece = header != NULL &&
		header->publisher == 0x01 && header->color == 0x01 &&
		header->gameId == 0x29 && header->gameRev == 0x00 &&
		header->checksum == 0xFD2E;

	rasterEnabled = isOnePiece;
	wsvScanlineCallbackEnabled = isOnePiece;
	readyFrame = -1;
	activeFrame = -1;
	captureFrame = 0;
	replayCursor = 0;
#if PALETTE_RASTER_DIAGNOSTIC != PALETTE_RASTER_CAPTURE_ONLY
	stopReplayIrq();
#endif
	if (isOnePiece) {
		resetCaptureFrame(&frames[0]);
		snapshotBase(&frames[0]);
	}
}

void paletteRasterCaptureLine(int line) {
	if (!rasterEnabled || (unsigned int)line >= WS_VISIBLE_LINES) {
		return;
	}

	PaletteDeltaFrame *frame = &frames[captureFrame];
	if (line == 0) {
		snapshotBase(frame);
		return;
	}

	const u16 *palette = (const u16 *)sphinx0.paletteRAM;
	for (unsigned int index = 1; index < WS_BG_COLORS; index++) {
		const u16 rawColor = palette[index];
		if (rawColor == previousPalette[index]) {
			continue;
		}
		previousPalette[index] = rawColor;
		if (frame->count < MAX_BG_PALETTE_DELTAS) {
			frame->delta[frame->count++] =
				(PaletteDelta){(u8)line, (u8)index, mapColor(rawColor)};
		}
		else {
			frame->dropped++;
		}
	}
}

void wsvScanlineCallback(int line) {
	paletteRasterCaptureLine(line);
}

void paletteRasterFrameComplete(void) {
	if (!rasterEnabled) {
		return;
	}

	readyFrame = captureFrame;
	captureFrame = nextFreeFrame(activeFrame, readyFrame);
	resetCaptureFrame(&frames[captureFrame]);
}

void paletteRasterVBlank(void) {
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
	for (unsigned int index = 1; index < WS_BG_COLORS; index++) {
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
