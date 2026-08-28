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
void paletteRasterCaptureLine(int line);
void paletteRasterFrameComplete(void);
void paletteRasterVBlank(void);
void paletteRasterVCountIrq(void);

#ifdef __cplusplus
}
#endif

#endif
