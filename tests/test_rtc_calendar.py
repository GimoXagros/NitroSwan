#!/usr/bin/env python3
"""RTC calendar vectors and source/API regression checks."""

from dataclasses import dataclass
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RTC_SOURCE = ROOT / "source" / "WSCart" / "WSRTC" / "WSRTCCalendar.c"
RTC_HEADER = ROOT / "source" / "WSCart" / "WSRTC" / "WSRTCCalendar.h"


def from_bcd(value: int) -> int:
    return ((value >> 4) * 10) + (value & 0x0F)


def to_bcd(value: int) -> int:
    return ((value // 10) << 4) | (value % 10)


def normalize(value: int, minimum: int, maximum: int) -> int:
    if (value & 0x0F) > 9 or (value >> 4) > 9:
        return maximum
    return max(minimum, min(maximum, from_bcd(value)))


def leap(year: int) -> bool:
    return year % 4 == 0


def month_days(year: int, month: int) -> int:
    return (31, 29 if leap(year) else 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31)[month - 1]


@dataclass
class DateTime:
    year: int
    month: int
    day: int
    weekday: int
    hour: int
    minute: int
    second: int

    def normalize(self) -> None:
        self.year = normalize(self.year, 0, 99)
        self.month = normalize(self.month, 1, 12)
        self.day = normalize(self.day, 1, month_days(self.year, self.month))
        self.weekday = normalize(self.weekday, 0, 6)
        self.hour = normalize(self.hour & 0x3F, 0, 23)
        self.minute = normalize(self.minute, 0, 59)
        self.second = normalize(self.second, 0, 59)
        for name in ("year", "month", "day", "hour", "minute", "second"):
            setattr(self, name, to_bcd(getattr(self, name)))


class RtcCalendarTests(unittest.TestCase):
    def test_vectors(self):
        rtc = DateTime(0x24, 0x13, 0x00, 0x09, 0x27, 0x6A, 0x7F)
        rtc.normalize()
        self.assertEqual(rtc, DateTime(0x24, 0x12, 0x01, 0x06, 0x23, 0x59, 0x59))

        for year, expected in ((0x23, 0x28), (0x24, 0x29)):
            rtc = DateTime(year, 0x02, 0x31, 1, 0x12, 0, 0)
            rtc.normalize()
            self.assertEqual(rtc.day, expected)

    def test_runtime_helper_api_is_present(self):
        self.assertTrue(RTC_SOURCE.is_file())
        self.assertTrue(RTC_HEADER.is_file())
        source = RTC_SOURCE.read_text(encoding="utf-8")
        header = RTC_HEADER.read_text(encoding="utf-8")
        self.assertIn("wsRtcNormalizeDateTime", source)
        self.assertIn("wsRtcTickDateTime", source)
        self.assertIn("typedef struct", header)


if __name__ == "__main__":
    unittest.main()
