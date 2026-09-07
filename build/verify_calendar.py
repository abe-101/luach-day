"""Verify hebcal.py against ICU's Hebrew calendar (via Node's Intl).

Walks every civil day in a range, converts with ICU and with hebcal, and
checks both directions agree. Run: python3 build/verify_calendar.py
"""

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hebcal  # noqa: E402

START, END = date(2000, 1, 1), date(2100, 12, 31)

# ICU's English month names -> hayomyom.json month keys.
ICU_MONTHS = {
    "Tishri": "1", "Heshvan": "2", "Kislev": "3", "Tevet": "4",
    "Shevat": "5", "Adar I": "6", "Adar": "6", "Adar II": "6b",
    "Nisan": "7", "Iyar": "8", "Sivan": "9", "Tamuz": "10",
    "Av": "11", "Elul": "12",
}

NODE = r"""
const start = new Date(Date.UTC(%d, %d, %d));
const days = %d;
const fmt = new Intl.DateTimeFormat('en-u-ca-hebrew', {
  day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC'
});
const out = [];
for (let i = 0; i < days; i++) {
  const d = new Date(start.getTime() + i * 86400000);
  const p = Object.fromEntries(fmt.formatToParts(d).map(x => [x.type, x.value]));
  out.push([p.month, Number(p.day), Number(p.year)]);
}
console.log(JSON.stringify(out));
"""


def icu_range(start, days):
    script = NODE % (start.year, start.month - 1, start.day, days)
    raw = subprocess.run(["node", "-e", script], capture_output=True,
                         text=True, check=True).stdout
    return json.loads(raw)


def main():
    days = (END - START).days + 1
    print(f"comparing {days} days, {START} .. {END}")
    expected = icu_range(START, days)

    failures = []
    for i, (icu_month, icu_day, icu_year) in enumerate(expected):
        g = START + timedelta(days=i)
        want = (icu_year, ICU_MONTHS[icu_month], icu_day)
        got = hebcal.from_gregorian(g)
        if got != want:
            failures.append(f"{g}: hebcal={got} icu={want}")
            continue
        # Round-trip: Hebrew date must map back to the same civil day.
        back = hebcal.to_gregorian(*got)
        if back != g:
            failures.append(f"{g}: round-trip gave {back}")

    if failures:
        print(f"FAIL: {len(failures)} mismatches")
        for line in failures[:20]:
            print("  " + line)
        sys.exit(1)
    print(f"OK: {days} days agree with ICU, both directions")


if __name__ == "__main__":
    main()
