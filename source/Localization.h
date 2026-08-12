#ifndef LOCALIZATION_HEADER
#define LOCALIZATION_HEADER

#include <nds.h>

enum UiLanguage {
	UI_LANGUAGE_ENGLISH = 0,
	UI_LANGUAGE_JAPANESE = 1,
	UI_LANGUAGE_KOREAN = 2,
	UI_LANGUAGE_COUNT = 3
};

const char *tr(const char *english);
const char *getUiLanguageName(void);
u8 getUiLanguage(void);
void setUiLanguage(u8 language);
void cycleUiLanguage(void);

#endif // LOCALIZATION_HEADER
