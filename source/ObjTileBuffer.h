#ifndef OBJ_TILE_BUFFER_HEADER
#define OBJ_TILE_BUFFER_HEADER

#include <nds/ndstypes.h>

#ifdef __cplusplus
extern "C" {
#endif

void objTileBufferReset(void);
void objTileBufferBeginFrame(unsigned int videoMode);
void videoTileBufferFrameComplete(void);
void videoTileBufferVBlank(void);

extern volatile u16 wsvObjTileOffset;
extern volatile u16 wsvBgTileOffset;
extern volatile u16 wsvBgReadyTileOffset;
extern volatile u16 objTilesConvertedFrame;
extern volatile u16 objTilesConvertedMaximum;
extern volatile u32 objBytesCopiedFrame;
extern volatile u32 objBytesCopiedMaximum;
extern volatile u32 objBufferSwapCount;
extern volatile u16 bgDirtyMarkersFrame;
extern volatile u16 bgDirtyMarkersMaximum;
extern volatile u32 bgBytesCopiedFrame;
extern volatile u32 bgBytesCopiedMaximum;
extern volatile u32 bgBufferSwapCount;

#ifdef __cplusplus
}
#endif

#endif
