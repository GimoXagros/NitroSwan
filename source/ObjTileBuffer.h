#ifndef OBJ_TILE_BUFFER_HEADER
#define OBJ_TILE_BUFFER_HEADER

#include <nds/ndstypes.h>

#ifdef __cplusplus
extern "C" {
#endif

void objTileBufferReset(void);
void objTileBufferQuiesce(void);
void objTileBufferBeginFrame(unsigned int videoMode);
void objTileBufferCompleteStateRestore(unsigned int videoMode);
void videoTileBufferFrameComplete(const void *completedOam);
void videoTileBufferFrameCommit(void);
bool videoTileBufferIsQuiesced(void);
const void *videoTileBufferVBlank(void);

extern volatile u16 wsvObjTileOffset;
extern volatile u16 wsvObjReadyTileOffset;
extern volatile u16 wsvBgTileOffset;
extern volatile u16 wsvBgReadyTileOffset;
extern u8 wsvObjTileSnapshots[];
extern volatile u16 objTilesConvertedWSFrame;
extern volatile u16 objTilesConvertedMaximum;
extern volatile u32 objSeedBytesFrame;
extern volatile u32 objPublishBytesHostFrame;
extern volatile u64 objTotalBytes;
extern volatile u32 objBytesCopiedMaximum;
extern volatile u32 objBufferSwapCount;
extern volatile u32 objPublicationCount;
extern volatile u32 skippedCleanGenerationCount;
extern volatile u16 bgDirtyMarkersFrame;
extern volatile u16 bgDirtyMarkersMaximum;
extern volatile u32 bgBytesCopiedFrame;
extern volatile u32 bgBytesCopiedMaximum;
extern volatile u32 bgBufferSwapCount;

#ifdef WSC_VIDEO_TRACE
typedef struct {
	u32 completedFrameGeneration;
	u32 objBuildGeneration;
	u32 readyFrameGeneration;
	u32 readyTileGeneration;
	u16 readyDirtyObjTiles;
	u16 readySeedBytes;
	u32 publishedFrameGeneration;
	u32 publishedTileGeneration;
	u16 publishedDirtyObjTiles;
	u16 publishedSeedBytes;
	u16 objBuildOffset;
	u16 objReadyOffset;
	u16 objPublishedOffset;
	u16 bgBuildOffset;
	u16 bgReadyOffset;
	u16 bgPublishedOffset;
	s16 readySlot;
	s16 activeSlot;
} ObjTileTraceState;

void objTileBufferGetTraceState(ObjTileTraceState *state);
#endif

#ifdef __cplusplus
}
#endif

#endif
