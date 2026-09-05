#ifndef PALETTE_RASTER_HEADER
#define PALETTE_RASTER_HEADER

#include <nds/ndstypes.h>

#include "WSCart/WSHeader.h"

#ifdef __cplusplus
extern "C" {
#endif

#define PALETTE_RASTER_CAPTURE_ONLY 1
#define PALETTE_RASTER_REPLAY_ONLY 2
#define PALETTE_RASTER_BG_ONLY 3

#ifndef PALETTE_RASTER_DIAGNOSTIC
#define PALETTE_RASTER_DIAGNOSTIC PALETTE_RASTER_BG_ONLY
#endif

void paletteRasterConfigure(const WsHeader *header);
void paletteRasterPrepareStateRestore(void);
void paletteRasterCompleteStateRestore(const WsHeader *header);
void paletteRasterCapturePaletteWrite(unsigned int address);
void wsvVideoRegisterWriteCallback(unsigned int port);
void paletteRasterFrameComplete(void);
void paletteRasterCommitFrame(void);
void paletteRasterBeginFrame(void);
void paletteRasterVBlank(void);
void paletteRasterVCountIrq(void);

extern bool wsvVideoWriteCallbackEnabled;
extern volatile u16 paletteRasterEventsFrame;
extern volatile u16 paletteRasterEventsMaximum;
extern volatile u16 paletteRasterDroppedFrame;
extern volatile u16 paletteRasterDroppedMaximum;
extern volatile u16 paletteRasterVCountIrqsFrame;
extern volatile u16 paletteRasterVCountIrqsMaximum;

#ifdef WSC_VIDEO_TRACE
typedef struct {
	s16 captureFrame;
	s16 pendingFrame;
	s16 readyFrame;
	s16 activeFrame;
	u16 lastVCountIrqs;
	u16 readyEvents;
	u16 readyDrops;
	u16 activeEvents;
	u16 activeDrops;
} PaletteRasterTraceState;

void paletteRasterGetTraceState(PaletteRasterTraceState *state);
#endif

#ifdef __cplusplus
}
#endif

#endif
