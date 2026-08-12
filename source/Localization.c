#include <string.h>

#include "Localization.h"

typedef struct {
	const char *english;
	const char *japanese;
	const char *korean;
} LocalizedString;

static u8 uiLanguage = UI_LANGUAGE_ENGLISH;

static const LocalizedString strings[] = {
	{"File", "ファイル", "파일"},
	{"Options", "設定", "설정"},
	{"About", "情報", "정보"},
	{"Load Game", "ゲーム読込", "게임 불러오기"},
	{"Load State", "ステート読込", "상태 불러오기"},
	{"Save State", "ステート保存", "상태 저장"},
	{"Load NVRAM", "NVRAM読込", "NVRAM 불러오기"},
	{"Save NVRAM", "NVRAM保存", "NVRAM 저장"},
	{"Load Patch", "パッチ読込", "패치 불러오기"},
	{"Cheats", "チート", "치트"},
	{"Save Settings", "設定を保存", "설정 저장"},
	{"Eject Game", "ゲーム取出", "게임 꺼내기"},
	{"Reset Console", "本体リセット", "본체 초기화"},
	{"Quit Emulator", "エミュ終了", "에뮬레이터 종료"},
	{"Controller", "コントローラー", "컨트롤러"},
	{"Display", "画面", "화면"},
	{"Machine", "本体", "기종"},
	{"Settings", "設定", "설정"},
	{"Debug", "デバッグ", "디버그"},
	{"Controller Settings", "コントローラー設定", "컨트롤러 설정"},
	{"Display Settings", "画面設定", "화면 설정"},
	{"Machine Settings", "本体設定", "기종 설정"},
	{"Quit Emulator?", "終了しますか？", "종료할까요?"},
	{"Cheat Menu", "チートメニュー", "치트 메뉴"},
	{"No cheats found.", "チートがありません。", "치트가 없습니다."},
	{"B Autofire:", "B連射:", "B 연사:"},
	{"A Autofire:", "A連射:", "A 연사:"},
	{"Swap A-B:  ", "A-B入替:  ", "A-B 교환:  "},
	{"Alternate map:", "別キー配置:", "대체 키 배치:"},
	{"Gamma:", "ガンマ:", "감마:"},
	{"Contrast:", "コントラスト:", "명암:"},
	{"B&W Palette:", "白黒パレット:", "흑백 팔레트:"},
	{"Border:", "ボーダー:", "테두리:"},
	{"Headphones:", "ヘッドホン:", "헤드폰:"},
	{"Cpu Speed Hacks:", "CPU高速化:", "CPU 가속:"},
	{"Import Internal EEPROM", "内蔵EEPROM読込", "내장 EEPROM 불러오기"},
	{"Clear Internal EEPROM", "内蔵EEPROM消去", "내장 EEPROM 지우기"},
	{"Select WS Bios", "WS BIOS選択", "WS BIOS 선택"},
	{"Select WS Color Bios", "WS Color BIOS選択", "WS Color BIOS 선택"},
	{"Select WS Crystal Bios", "WS Crystal BIOS選択", "WS Crystal BIOS 선택"},
	{"Language:", "言語:", "언어:"},
	{"Speed:", "速度:", "속도:"},
	{"Allow Refresh Change:", "リフレッシュ変更:", "화면 주사율 변경:"},
	{"Autoload State:", "ステート自動読込:", "상태 자동 불러오기:"},
	{"Autoload NVRAM:", "NVRAM自動読込:", "NVRAM 자동 불러오기:"},
	{"Autosave Settings:", "設定を自動保存:", "설정 자동 저장:"},
	{"Autopause Game:", "メニュー時停止:", "메뉴에서 일시정지:"},
	{"Powersave 2nd Screen:", "第2画面を節電:", "보조 화면 절전:"},
	{"Emulator on Bottom:", "ゲームを下画面:", "게임을 아래 화면에:"},
	{"Init Settings", "設定を初期化", "설정 초기화"},
	{"Debug Output:", "デバッグ表示:", "디버그 출력:"},
	{"Disable Foreground:", "前景を無効:", "전경 끄기:"},
	{"Disable Background:", "背景を無効:", "배경 끄기:"},
	{"Disable Sprites:", "スプライト無効:", "스프라이트 끄기:"},
	{"Disable Windows:", "ウィンドウ無効:", "윈도우 끄기:"},
	{"Step Frame", "1フレーム実行", "한 프레임 실행"},
	{"Yes ", "はい ", "예 "},
	{"No ", "いいえ ", "아니요 "},
	{"Off", "切", "끔"},
	{"On", "入", "켬"},
	{"With R", "R使用", "R과 함께"},
	{"Auto", "自動", "자동"},
	{"Normal", "標準", "보통"},
	{"Black & White", "白黒", "흑백"},
	{"Red", "赤", "빨강"},
	{"Green", "緑", "초록"},
	{"Blue", "青", "파랑"},
	{"Black", "黒", "검정"},
	{"Frame", "フレーム", "프레임"},
	{"BG Color", "背景色", "배경색"},
	{"None", "なし", "없음"},
	{"English", "English", "English"},
	{"Japanese", "日本語", "日本語"},
	{"Korean", "한국어", "한국어"},
	{"        Touch screen or", "      画面をタッチ または", "      화면을 터치하거나"},
	{"      press L+R for menu.", "       L+Rでメニュー。", "      L+R로 메뉴 열기."},
	{"     Please wait, loading.", "      読み込み中です。", "      불러오는 중입니다."},
	{"        Loading state...", "     ステート読込中…", "      상태 불러오는 중…"},
	{"        Saving state...", "     ステート保存中…", "       상태 저장 중…"},
	{"Loaded state.", "ステートを読み込みました。", "상태를 불러왔습니다."},
	{"Saved state.", "ステートを保存しました。", "상태를 저장했습니다."},
	{"Loaded NVRAM.", "NVRAMを読み込みました。", "NVRAM을 불러왔습니다."},
	{"Saved NVRAM.", "NVRAMを保存しました。", "NVRAM을 저장했습니다."},
	{"Settings loaded.", "設定を読み込みました。", "설정을 불러왔습니다."},
	{"Settings saved.", "設定を保存しました。", "설정을 저장했습니다."},
	{"File too large!", "ファイルが大きすぎます！", "파일이 너무 큽니다!"},
	{"Couldn't open file:", "ファイルを開けません:", "파일을 열 수 없습니다:"},
	{"Couldn't open state file:", "ステートを開けません:", "상태 파일을 열 수 없습니다:"},
	{"Couldn't alloc mem for state.", "ステート用メモリ不足。", "상태용 메모리가 부족합니다."},
	{"Wrong size of state.", "ステートサイズが不正です。", "상태 크기가 올바르지 않습니다."},
	{"Using Exp-RAM.", "拡張RAMを使用します。", "확장 RAM을 사용합니다."},
	{"English/Japanese/Korean", "英語/日本語/韓国語", "영어/일본어/한국어"}
	,{"B:        WS B button", "B:        WS Bボタン", "B:        WS B 버튼"}
	,{"A:        WS A button", "A:        WS Aボタン", "A:        WS A 버튼"}
	,{"Start:    WS Start button", "Start:    WS Startボタン", "Start:    WS 시작 버튼"}
	,{"Select:   WS Sound button", "Select:   WS Soundボタン", "Select:   WS 소리 버튼"}
	,{"DPad:     WS X1-X4", "十字キー: WS X1-X4", "십자키:   WS X1-X4"}
	,{"Cheats loaded.", "チートを読み込みました。", "치트를 불러왔습니다."}
	,{"Couldn't save cheats.", "チートを保存できません。", "치트를 저장할 수 없습니다."}
	,{"WonderWitch", "WonderWitch", "WonderWitch"}
	,{"BootFriend", "BootFriend", "BootFriend"}
	,{"Storage:", "ストレージ:", "저장소:"}
	,{"Upload File", "ファイル送信", "파일 보내기"}
	,{"Dir", "一覧", "목록"}
	,{"Execute", "実行", "실행"}
	,{"Delete", "削除", "삭제"}
	,{"Defrag", "最適化", "조각 모음"}
	,{"Download File", "ファイル受信", "파일 받기"}
	,{"NewFS (Formatt)", "新規FS (初期化)", "새 FS (초기화)"}
	,{"XMODEM Transmit", "XMODEM送信", "XMODEM 보내기"}
	,{"XMODEM Receive", "XMODEM受信", "XMODEM 받기"}
	,{"Reboot WW", "WW再起動", "WW 다시 시작"}
	,{"Interact", "対話", "대화형"}
	,{"Hello", "接続確認", "연결 확인"}
	,{"Formatt Storage?", "ストレージを初期化？", "저장소를 초기화할까요?"}
	,{"Green-Blue", "緑-青", "초록-파랑"}
	,{"Blue-Green", "青-緑", "파랑-초록"}
	,{"Puyo Puyo Tsu", "ぷよぷよ通", "뿌요뿌요 2"}
	,{"Max", "最大", "최대"}
	,{"        Trying Exp-RAM.", "       拡張RAMを確認中。", "       확장 RAM 확인 중."}
	,{"         Using Exp-RAM.", "       拡張RAMを使用。", "       확장 RAM 사용 중."}
	,{"   Please wait, decompressing.", "       展開しています。", "        압축 해제 중입니다."}
	,{"Error in settings file.", "設定ファイルが不正です。", "설정 파일이 올바르지 않습니다."}
	,{"Couldn't save settings.", "設定を保存できません。", "설정을 저장할 수 없습니다."}
	,{"Couldn't find folder:", "フォルダーがありません:", "폴더를 찾을 수 없습니다:"}
	,{"Can not load zip to Exp-RAM.", "ZIPを拡張RAMへ読込不可。", "ZIP을 확장 RAM에 불러올 수 없습니다."}
	,{"Not an IPS file:", "IPSファイルではありません:", "IPS 파일이 아닙니다:"}
};

const char *tr(const char *english) {
	if (english == NULL || uiLanguage == UI_LANGUAGE_ENGLISH) return english;
	for (unsigned int i = 0; i < sizeof(strings) / sizeof(strings[0]); i++) {
		if (strcmp(strings[i].english, english) == 0) {
			return uiLanguage == UI_LANGUAGE_JAPANESE
					? strings[i].japanese : strings[i].korean;
		}
	}
	return english;
}

const char *getUiLanguageName(void) {
	static const char *const names[] = {"English", "日本語", "한국어"};
	return names[uiLanguage];
}

u8 getUiLanguage(void) {
	return uiLanguage;
}

void setUiLanguage(u8 language) {
	uiLanguage = language < UI_LANGUAGE_COUNT ? language : UI_LANGUAGE_ENGLISH;
}

void cycleUiLanguage(void) {
	setUiLanguage(uiLanguage + 1);
}
