#ifndef OBJ_TILE_BUFFER_HEADER
#define OBJ_TILE_BUFFER_HEADER

#include <nds/ndstypes.h>

#ifdef __cplusplus
extern "C" {
#endif

void objTileBufferReset(void);
void objTileBufferBeginFrame(unsigned int videoMode);

extern volatile u16 wsvObjTileOffset;
extern volatile u16 objTilesConvertedFrame;
extern volatile u16 objTilesConvertedMaximum;
extern volatile u32 objBytesCopiedFrame;
extern volatile u32 objBytesCopiedMaximum;
extern volatile u32 objBufferSwapCount;

#ifdef __cplusplus
}
#endif

#endif
