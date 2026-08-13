#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "WSRTCCalendar.h"

static void test_normalize(void) {
    WSRTCDateTime rtc = { 0x24, 0x13, 0x00, 0x09, 0x27, 0x6A, 0x7F };

    wsRtcNormalizeDateTime(&rtc);

    assert(rtc.year == 0x24);
    assert(rtc.month == 0x12);
    assert(rtc.day == 0x01);
    assert(rtc.weekDay == 0x06);
    assert(rtc.hour == 0x23);
    assert(rtc.minute == 0x59);
    assert(rtc.second == 0x59);
}

static void test_month_ends(void) {
    WSRTCDateTime rtc = { 0x23, 0x02, 0x28, 0x02, 0x23, 0x59, 0x59 };
    wsRtcTickDateTime(&rtc);
    assert(rtc.year == 0x23 && rtc.month == 0x03 && rtc.day == 0x01);
    assert(rtc.weekDay == 0x03 && rtc.hour == 0x00);

    rtc = (WSRTCDateTime){ 0x24, 0x02, 0x28, 0x03, 0x23, 0x59, 0x59 };
    wsRtcTickDateTime(&rtc);
    assert(rtc.month == 0x02 && rtc.day == 0x29);
    wsRtcTickDateTime(&rtc);
    rtc.hour = 0x23;
    rtc.minute = 0x59;
    rtc.second = 0x59;
    wsRtcTickDateTime(&rtc);
    assert(rtc.month == 0x03 && rtc.day == 0x01);

    rtc = (WSRTCDateTime){ 0x99, 0x12, 0x31, 0x06, 0x23, 0x59, 0x59 };
    wsRtcTickDateTime(&rtc);
    assert(rtc.year == 0x00 && rtc.month == 0x01 && rtc.day == 0x01);
    assert(rtc.weekDay == 0x00);
}

static void test_invalid_date_is_clamped_to_month(void) {
    WSRTCDateTime rtc = { 0x23, 0x02, 0x31, 0x01, 0x12, 0x00, 0x00 };
    wsRtcNormalizeDateTime(&rtc);
    assert(rtc.day == 0x28);

    rtc = (WSRTCDateTime){ 0x24, 0x02, 0x31, 0x01, 0x12, 0x00, 0x00 };
    wsRtcNormalizeDateTime(&rtc);
    assert(rtc.day == 0x29);
}

int main(void) {
    test_normalize();
    test_month_ends();
    test_invalid_date_is_clamped_to_month();
    puts("RTC calendar regression tests passed");
    return 0;
}
