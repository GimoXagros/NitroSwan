#ifndef CHEATS_HEADER
#define CHEATS_HEADER

#include <nds.h>
#include <stdbool.h>

#define MAX_CHEATS 64
#define MAX_CHEAT_NAME_COLUMNS 24
#define MAX_CHEAT_NAME_BYTES (MAX_CHEAT_NAME_COLUMNS * 4 + 1)

void cheatsReset(void);
bool cheatsLoad(void);
bool cheatsSave(void);
void cheatsApply(void);
int cheatsGetCount(void);
const char *cheatsGetName(int index);
bool cheatsIsEnabled(int index);
void cheatsToggle(int index);

#endif // CHEATS_HEADER
