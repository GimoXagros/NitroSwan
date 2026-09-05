#ifndef RENDERER_TRACE_HEADER
#define RENDERER_TRACE_HEADER

#include <nds/ndstypes.h>

#ifdef __cplusplus
extern "C" {
#endif

void rendererTraceInit(bool filesystemReady);
void rendererTraceWSFrame(void);
void rendererTraceHostVBlank(void);
void rendererTraceFlush(void);

#ifdef __cplusplus
}
#endif

#endif
