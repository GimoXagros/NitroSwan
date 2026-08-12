#include <ctype.h>
#include <stdio.h>
#include <string.h>

#include "Cheats.h"
#include "Memory.h"
#include "Shared/FileHelper.h"
#include "Shared/UnicodeText.h"
#include "Shared/EmuMenu.h"

typedef struct {
	u32 address;
	u8 value;
	u8 compare;
	bool hasCompare;
	bool enabled;
	char name[MAX_CHEAT_NAME_BYTES];
} Cheat;

static Cheat cheats[MAX_CHEATS];
static int cheatCount;

static int hexValue(char value) {
	if (value >= '0' && value <= '9') return value - '0';
	if (value >= 'a' && value <= 'f') return value - 'a' + 10;
	if (value >= 'A' && value <= 'F') return value - 'A' + 10;
	return -1;
}

static bool parseHex(const char *text, int digits, u32 *value) {
	u32 result = 0;
	for (int i = 0; i < digits; i++) {
		const int digit = hexValue(text[i]);
		if (digit < 0) return false;
		result = (result << 4) | digit;
	}
	*value = result;
	return true;
}

static bool parseCode(const char *code, Cheat *cheat) {
	const size_t length = strlen(code);
	u32 address;
	u32 value;
	u32 compare = 0;
	bool hasCompare = false;
	if (length == 8 && code[5] == ':') {
		if (!parseHex(code, 5, &address) || !parseHex(code + 6, 2, &value)) {
			return false;
		}
	}
	else if (length == 7) {
		if (!parseHex(code, 5, &address) || !parseHex(code + 5, 2, &value)) {
			return false;
		}
	}
	else if (length == 11 && code[5] == '?' && code[8] == ':') {
		if (!parseHex(code, 5, &address)
				|| !parseHex(code + 6, 2, &compare)
				|| !parseHex(code + 9, 2, &value)) {
			return false;
		}
		hasCompare = true;
	}
	else {
		return false;
	}
	// NitroSwan currently guarantees safe low-level writes only for the
	// WonderSwan's internal RAM and active cartridge SRAM windows.
	if (address > 0x1FFFF) return false;
	cheat->address = address;
	cheat->value = value;
	cheat->compare = compare;
	cheat->hasCompare = hasCompare;
	return true;
}

void cheatsReset(void) {
	memset(cheats, 0, sizeof(cheats));
	cheatCount = 0;
}

bool cheatsLoad(void) {
	cheatsReset();
	if (currentFilename[0] == 0) return false;
	char cheatName[FILENAME_MAX_LENGTH];
	setFileExtension(cheatName, currentFilename, ".cht", sizeof(cheatName));
	FILE *file = fopen(cheatName, "r");
	if (file == NULL) return false;

	char line[256];
	while (cheatCount < MAX_CHEATS && fgets(line, sizeof(line), file)) {
		size_t length = strlen(line);
		const bool completeLine = length > 0 && line[length - 1] == '\n';
		while (length && (line[length - 1] == '\n' || line[length - 1] == '\r')) {
			line[--length] = 0;
		}
		if (!completeLine && !feof(file)) {
			int ch;
			while ((ch = fgetc(file)) != '\n' && ch != EOF) { }
			continue;
		}
		char *cursor = line;
		while (isspace((unsigned char)*cursor)) cursor++;
		if (*cursor == 0 || *cursor == '#' || *cursor == ';') continue;
		char *codeEnd = cursor;
		while (*codeEnd && !isspace((unsigned char)*codeEnd)) codeEnd++;
		if (*codeEnd) {
			*codeEnd++ = 0;
			while (isspace((unsigned char)*codeEnd)) codeEnd++;
		}

		Cheat candidate = {0};
		if (!parseCode(cursor, &candidate)) continue;
		if (*codeEnd == '0' || *codeEnd == '1') {
			candidate.enabled = *codeEnd++ == '1';
		}
		while (isspace((unsigned char)*codeEnd)) codeEnd++;
		textCopyColumns(candidate.name, sizeof(candidate.name),
				*codeEnd ? codeEnd : cursor, MAX_CHEAT_NAME_COLUMNS);
		cheats[cheatCount++] = candidate;
	}
	fclose(file);
	if (cheatCount) infoOutput("Cheats loaded.");
	return cheatCount > 0;
}

bool cheatsSave(void) {
	if (cheatCount == 0 || currentFilename[0] == 0) return false;
	char cheatName[FILENAME_MAX_LENGTH];
	setFileExtension(cheatName, currentFilename, ".cht", sizeof(cheatName));
	FILE *file = fopen(cheatName, "w");
	if (file == NULL) return false;
	for (int i = 0; i < cheatCount; i++) {
		if (cheats[i].hasCompare) {
			fprintf(file, "%05lX?%02X:%02X %d %s\n",
					(unsigned long)cheats[i].address, cheats[i].compare,
					cheats[i].value, cheats[i].enabled, cheats[i].name);
		}
		else {
			fprintf(file, "%05lX:%02X %d %s\n",
					(unsigned long)cheats[i].address, cheats[i].value,
					cheats[i].enabled, cheats[i].name);
		}
	}
	const bool ok = fclose(file) == 0;
	if (!ok) infoOutput("Couldn't save cheats.");
	return ok;
}

void cheatsApply(void) {
	if (cheatCount == 0) return;
	for (int i = 0; i < cheatCount; i++) {
		if (!cheats[i].enabled) continue;
		const u32 scaledAddress = cheats[i].address << 12;
		if (cheats[i].hasCompare
				&& cpuReadMem20(scaledAddress) != cheats[i].compare) {
			continue;
		}
		cpuWriteMem20(scaledAddress, cheats[i].value);
	}
}

int cheatsGetCount(void) {
	return cheatCount;
}

const char *cheatsGetName(int index) {
	return index >= 0 && index < cheatCount ? cheats[index].name : "";
}

bool cheatsIsEnabled(int index) {
	return index >= 0 && index < cheatCount && cheats[index].enabled;
}

void cheatsToggle(int index) {
	if (index < 0 || index >= cheatCount) return;
	cheats[index].enabled = !cheats[index].enabled;
	cheatsSave();
}
