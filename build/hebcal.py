"""Hebrew calendar arithmetic, stdlib only.

Standard molad-based algorithm (Dershowitz & Reingold, "Calendrical
Calculations"), reworked to number months from Tishri=1, which is how
hayomyom.json is keyed. Verified against ICU via build/verify_calendar.py.
"""

from datetime import date

# RD (Rata Die) of 1 Tishri, year 1. RD 1 == 0001-01-01 == date.toordinal() 1.
HEBREW_EPOCH = -1373427

# Month keys as used by hayomyom.json: Tishri=1 … Elul=12, Adar II = "6b".
# In a leap year, month 6 is Adar I and "6b" is Adar II.
MONTHS = {
    "1": "Tishrei", "2": "Cheshvan", "3": "Kislev", "4": "Tevet",
    "5": "Shevat", "6": "Adar", "6b": "Adar II", "7": "Nissan",
    "8": "Iyar", "9": "Sivan", "10": "Tammuz", "11": "Av", "12": "Elul",
}

MONTH_HE = {
    "1": "תשרי", "2": "חשון", "3": "כסלו", "4": "טבת",
    "5": "שבט", "6": "אדר", "6b": "אדר ב׳", "7": "ניסן",
    "8": "אייר", "9": "סיון", "10": "תמוז", "11": "אב", "12": "אלול",
}

# Adar is named "Adar I" only when the year is a leap year.
ADAR_I_HE = "אדר א׳"


def is_leap(year):
    """A Hebrew year is a leap year 7 times in each 19-year cycle."""
    return ((7 * year + 1) % 19) < 7


def _elapsed_days(year):
    """Days from the epoch to 1 Tishri of `year`, before dechiyot 2-4."""
    months = (235 * ((year - 1) // 19)          # months in whole cycles
              + 12 * ((year - 1) % 19)          # regular years this cycle
              + (7 * ((year - 1) % 19) + 1) // 19)  # leap months this cycle
    parts = 12084 + 13753 * months
    day = 29 * months + parts // 25920
    # Dechiyah: molad zaken / lo ADU rosh, folded into one parity test.
    if (3 * (day + 1)) % 7 < 3:
        day += 1
    return day


def _new_year_delay(year):
    """Dechiyot GaTaRaD and BeTUTeKaPoT, detected via neighbouring years."""
    prev, cur, nxt = (_elapsed_days(year - 1), _elapsed_days(year),
                      _elapsed_days(year + 1))
    if nxt - cur == 356:
        return 2
    if cur - prev == 382:
        return 1
    return 0


def rosh_hashanah_rd(year):
    """RD of 1 Tishri of the given Hebrew year."""
    return HEBREW_EPOCH + _elapsed_days(year) + _new_year_delay(year)


def year_length(year):
    return rosh_hashanah_rd(year + 1) - rosh_hashanah_rd(year)


def months_of_year(year):
    """[(month_key, length)] in calendar order starting at Tishri."""
    length = year_length(year)
    cheshvan = 30 if length in (355, 385) else 29
    kislev = 29 if length in (353, 383) else 30
    months = [("1", 30), ("2", cheshvan), ("3", kislev), ("4", 29), ("5", 30)]
    if is_leap(year):
        months += [("6", 30), ("6b", 29)]   # Adar I is always 30 days
    else:
        months += [("6", 29)]
    months += [("7", 30), ("8", 29), ("9", 30), ("10", 29), ("11", 30),
               ("12", 29)]
    return months


def to_rd(year, month_key, day):
    """Hebrew date -> RD. `month_key` uses the Tishri=1 / '6b' scheme."""
    rd = rosh_hashanah_rd(year)
    for key, length in months_of_year(year):
        if key == month_key:
            if not 1 <= day <= length:
                raise ValueError(f"{month_key}-{day} not in Hebrew {year}")
            return rd + day - 1
        rd += length
    raise ValueError(f"no month {month_key!r} in Hebrew year {year}")


def from_rd(rd):
    """RD -> (year, month_key, day)."""
    # Estimate low, then walk forward; the estimate is never more than a
    # year or two off, so this settles in a couple of iterations.
    year = (rd - HEBREW_EPOCH) // 366 + 1
    while rosh_hashanah_rd(year + 1) <= rd:
        year += 1
    while rosh_hashanah_rd(year) > rd:
        year -= 1
    offset = rd - rosh_hashanah_rd(year)
    for key, length in months_of_year(year):
        if offset < length:
            return year, key, offset + 1
        offset -= length
    raise AssertionError("fell off the end of the Hebrew year")


def to_gregorian(year, month_key, day):
    return date.fromordinal(to_rd(year, month_key, day))


def from_gregorian(g):
    return from_rd(g.toordinal())


def month_name(month_key, year=None):
    """English month name; Adar becomes 'Adar I' in a known leap year."""
    if month_key == "6" and year is not None and is_leap(year):
        return "Adar I"
    return MONTHS[month_key]


def month_name_he(month_key, year=None):
    if month_key == "6" and year is not None and is_leap(year):
        return ADAR_I_HE
    return MONTH_HE[month_key]


def numeral(n):
    """Hebrew gematria numeral: 5 -> ה׳, 15 -> ט״ו, 5786 -> תשפ״ו."""
    values = [(400, "ת"), (300, "ש"), (200, "ר"), (100, "ק"), (90, "צ"),
              (80, "פ"), (70, "ע"), (60, "ס"), (50, "נ"), (40, "מ"),
              (30, "ל"), (20, "כ"), (10, "י"), (9, "ט"), (8, "ח"),
              (7, "ז"), (6, "ו"), (5, "ה"), (4, "ד"), (3, "ג"),
              (2, "ב"), (1, "א")]
    if not n:
        return ""
    rest, s = n % 1000, ""   # years drop the thousands: 5786 -> תשפ״ו
    for value, ch in values:
        while rest >= value:
            s += ch
            rest -= value
    # Avoid spelling the Divine Name.
    if s.endswith("יה"):
        s = s[:-2] + "טו"
    elif s.endswith("יו"):
        s = s[:-2] + "טז"
    return s + "׳" if len(s) == 1 else s[:-1] + "״" + s[-1]
