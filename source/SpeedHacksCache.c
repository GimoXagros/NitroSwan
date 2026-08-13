#include <nds.h>

// SpeedHacks.s patches two ARM handlers in main RAM.  Flush the data cache
// before invalidating the matching instruction-cache lines so the ARM946E-S
// cannot continue executing a stale version of a previously selected hack.
void speedHacksSync(const void *address, unsigned size) {
	DC_FlushRange(address, size);
	IC_InvalidateRange(address, size);
}
