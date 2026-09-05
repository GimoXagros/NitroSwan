#ifndef RENDERER_ABI_SELF_TEST_HEADER
#define RENDERER_ABI_SELF_TEST_HEADER

#include <nds/ndstypes.h>

extern volatile u32 rendererAbiSelfTestResult;
u32 rendererAbiSentinelSelfTest(void);
u32 rendererAbiSentinelCallback(void);

#endif
