#ifdef RENDERER_ABI_SELF_TEST

#include <stdint.h>

#include "RendererAbiSelfTest.h"

volatile u32 rendererAbiSelfTestResult;

__attribute__((noinline)) u32 rendererAbiSentinelCallback(void) {
	register uintptr_t stackPointer __asm__("sp");
	volatile u32 stackExercise[4] = {1, 2, 3, 4};
	return (stackPointer & 7U) | (stackExercise[0] - 1U);
}

#endif
