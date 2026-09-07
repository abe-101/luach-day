"""Generate the static Hayom Yom archive for luach.day.

Reads hayomyom.json and writes:
    hayom-yom/index.html                 archive hub
    hayom-yom/<month>/index.html         13 month hubs
    hayom-yom/<month>-<day>/index.html   383 entry pages
    sitemap.xml                          every URL on the site

Pure stdlib. Run: python3 build/generate.py
"""

import html
import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hebcal  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://luach.day"
OUT = ROOT / "hayom-yom"

# URL slugs. These are the spellings people actually type; the templates
# mention common variants ("Nissan / Nisan") so the alternates match too.
SLUGS = {
    "1": "tishrei", "2": "cheshvan", "3": "kislev", "4": "tevet",
    "5": "shevat", "6": "adar", "6b": "adar-ii", "7": "nissan",
    "8": "iyar", "9": "sivan", "10": "tammuz", "11": "av", "12": "elul",
}
ORDER = ["1", "2", "3", "4", "5", "6", "6b", "7", "8", "9", "10", "11", "12"]

# Alternate romanisations, worked into the page copy for long-tail matching.
VARIANTS = {
    "1": "Tishri", "2": "Marcheshvan or Heshvan", "3": None,
    "4": "Teves", "5": "Shvat", "6": "Adar Aleph in a leap year",
    "6b": "Adar Bet", "7": "Nisan", "8": "Iyyar", "9": None,
    "10": "Tamuz", "11": "Menachem Av", "12": None,
}


def also_written(month_key):
    """' (also written X)', or nothing when there is no distinct variant."""
    variant = VARIANTS[month_key]
    return f" (also written {variant})" if variant else ""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<meta name="theme-color" content="#21409A">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="luach.day">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{site}/og-image.png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Suez+One&family=Frank+Ruhl+Libre:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/luach.css">
<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
<main class="sheet">
  <div class="strip">
    <span>{crumb}</span>
    <a class="site" href="/">luach.day</a>
  </div>
"""

FOOTER = """
  <div class="footer">
    <a href="/">Today's Hebrew date</a> ·
    <a href="/hayom-yom/">Hayom Yom archive</a>
  </div>
</main>
</body>
</html>
"""


def esc(s):
    return html.escape(str(s), quote=True)


def jsonld(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def breadcrumbs(trail):
    """trail: [(name, url), ...] -> BreadcrumbList JSON-LD."""
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": url}
            for i, (name, url) in enumerate(trail, 1)
        ],
    }


def upcoming(month_key, day, count=8, span=25):
    """Civil dates this Hebrew date falls on, starting from the current year.

    Skips years where the date does not exist -- Adar II only occurs in leap
    years, and 30 Kislev is absent from deficient years.
    """
    today = date.today()
    start_year = hebcal.from_gregorian(today)[0]
    rows = []
    for year in range(start_year, start_year + span):
        try:
            g = hebcal.to_gregorian(year, month_key, day)
        except ValueError:
            continue          # no such date in this Hebrew year
        if g < today:
            continue          # this year's occurrence has already passed
        rows.append((year, g))
        if len(rows) == count:
            break
    return rows


def entry_page(month_key, day, text, prev_ref, next_ref):
    slug = f"{SLUGS[month_key]}-{day}"
    url = f"{SITE}/hayom-yom/{slug}/"
    name = hebcal.MONTHS[month_key]
    name_he = hebcal.MONTH_HE[month_key]
    he_date = f"{hebcal.numeral(day)} {name_he}"
    label = f"{day} {name}"

    rows = upcoming(month_key, day)
    if rows:
        first_year, first_g = rows[0]
        window = f"{rows[0][0]}–{rows[-1][0]}"
    else:
        first_year = first_g = window = None

    title = f"Hayom Yom for {label} ({he_date}) | luach.day"
    description = (
        f"The Hayom Yom entry for {label} on the Jewish calendar, in the "
        f"original Hebrew, with the civil dates {label} falls on in "
        f"{window}." if window else
        f"The Hayom Yom entry for {label} on the Jewish calendar, in the "
        f"original Hebrew."
    )

    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": url + "#entry",
                "url": url,
                "headline": f"Hayom Yom — {label}",
                "inLanguage": "he",
                "articleBody": text,
                "isPartOf": {"@id": f"{SITE}/hayom-yom/#archive"},
                "about": {
                    "@type": "Book",
                    "name": "Hayom Yom",
                    "alternateName": "היום יום",
                    "author": {
                        "@type": "Person",
                        "name": "Rabbi Menachem Mendel Schneerson",
                    },
                },
            },
            breadcrumbs([
                ("luach.day", f"{SITE}/"),
                ("Hayom Yom", f"{SITE}/hayom-yom/"),
                (name, f"{SITE}/hayom-yom/{SLUGS[month_key]}/"),
                (label, url),
            ]),
        ],
    }

    parts = [HEAD.format(
        title=esc(title), description=esc(description), url=url, site=SITE,
        og_title=esc(f"Hayom Yom — {label}"), og_type="article",
        crumb=f'<a href="/hayom-yom/{SLUGS[month_key]}/">{esc(name)}</a>',
        jsonld=jsonld(graph),
    )]

    parts.append(f"""
  <h1 class="page-title">Hayom Yom<br><span class="num">{esc(label)}</span></h1>
  <p class="subtitle" lang="he" dir="rtl">{esc(he_date)}</p>

  <section class="hayomyom" lang="he" dir="rtl">
    <h2 class="hy-title">היום יום · {esc(he_date)}</h2>
    <p class="hy-text">{esc(text)}</p>
  </section>
""")

    if rows:
        trs = "\n".join(
            f'      <tr><td>{r[1].strftime("%B %-d, %Y")}</td>'
            f'<td>{r[1].strftime("%A")}</td>'
            f'<td class="he">{esc(hebcal.numeral(day))} '
            f'{esc(hebcal.month_name_he(month_key, r[0]))} '
            f'{esc(hebcal.numeral(r[0]))}</td></tr>'
            for r in rows
        )
        parts.append(f"""
  <h2 class="section-head">When is {esc(label)}?</h2>
  <table class="dates">
    <thead><tr><th>Civil date</th><th>Day</th><th>Hebrew date</th></tr></thead>
    <tbody>
{trs}
    </tbody>
  </table>
  <p class="caption">Each Hebrew day begins at nightfall the evening before the
  civil date shown.</p>
""")

    parts.append(f"""
  <h2 class="section-head">About this entry</h2>
  <div class="prose">
    <p><em>Hayom Yom</em> (&#x05d4;&#x05d9;&#x05d5;&#x05dd; &#x05d9;&#x05d5;&#x05dd;,
    &ldquo;day by day&rdquo;) is an anthology of Chassidic aphorisms and customs
    with one entry for every day of the Hebrew year. It was compiled in 1942 by
    Rabbi Menachem Mendel Schneerson, the Lubavitcher Rebbe, at the instruction
    of his father-in-law, the Previous Rebbe.</p>
    <p>This page carries the entry for <strong>{esc(label)}</strong> &mdash; the
    {esc(day)}{ordinal_suffix(day)} day of
    {esc(name)}{esc(also_written(month_key))} &mdash; in the original Hebrew.
    Browse the
    <a href="/hayom-yom/{SLUGS[month_key]}/">whole of {esc(name)}</a>, or
    see <a href="/">today&rsquo;s Hebrew date and today&rsquo;s entry</a>.</p>
  </div>

  <nav class="pager">
    <a href="/hayom-yom/{prev_ref[0]}/">&larr; {esc(prev_ref[1])}</a>
    <a href="/hayom-yom/{next_ref[0]}/">{esc(next_ref[1])} &rarr;</a>
  </nav>
""")
    parts.append(FOOTER.format(site=SITE))
    return slug, "".join(parts)


def ordinal_suffix(n):
    if 11 <= n % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def month_page(month_key, days, data):
    slug = SLUGS[month_key]
    url = f"{SITE}/hayom-yom/{slug}/"
    name = hebcal.MONTHS[month_key]
    name_he = hebcal.MONTH_HE[month_key]

    leap_note = ""
    if month_key == "6b":
        leap_note = (
            "<p>Adar II (&#x05d0;&#x05d3;&#x05e8; &#x05d1;&#x05f3;) exists only "
            "in a Jewish leap year, when a second Adar is added &mdash; seven "
            "years in every nineteen. In an ordinary year these entries are read "
            f'in <a href="/hayom-yom/adar/">Adar</a>.</p>')
    elif month_key == "6":
        leap_note = (
            "<p>In a leap year this month is Adar I, and it is followed by "
            f'<a href="/hayom-yom/adar-ii/">Adar II</a>.</p>')

    title = f"Hayom Yom for {name} — all {len(days)} days | luach.day"
    description = (
        f"Every Hayom Yom entry for the month of {name}"
        f"{also_written(month_key)} on the Jewish calendar, in the original "
        f"Hebrew — all {len(days)} days.")

    items = "\n".join(
        f'    <li><a href="/hayom-yom/{slug}-{d}/">{d}'
        f'<span class="he">{esc(hebcal.numeral(d))}</span></a></li>'
        for d in days
    )

    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": url + "#month",
                "url": url,
                "name": f"Hayom Yom — {name}",
                "isPartOf": {"@id": f"{SITE}/hayom-yom/#archive"},
            },
            breadcrumbs([
                ("luach.day", f"{SITE}/"),
                ("Hayom Yom", f"{SITE}/hayom-yom/"),
                (name, url),
            ]),
        ],
    }

    body = HEAD.format(
        title=esc(title), description=esc(description), url=url, site=SITE,
        og_title=esc(f"Hayom Yom — {name}"), og_type="website",
        crumb=f'<a href="/hayom-yom/">Hayom Yom</a>',
        jsonld=jsonld(graph),
    ) + f"""
  <h1 class="page-title">{esc(name)}</h1>
  <p class="subtitle" lang="he" dir="rtl">{esc(name_he)} &middot; {len(days)} days</p>

  <div class="prose">
    <p>Every <em>Hayom Yom</em> entry for
    {esc(name)}{esc(also_written(month_key))}. Pick a day to read its entry in
    the original Hebrew.</p>
    {leap_note}
  </div>

  <h2 class="section-head">Days of {esc(name)}</h2>
  <ul class="grid">
{items}
  </ul>
""" + FOOTER.format(site=SITE)
    return slug, body


def archive_page(months):
    url = f"{SITE}/hayom-yom/"
    total = sum(len(d) for _, d in months)
    title = "Hayom Yom — complete daily archive in Hebrew | luach.day"
    description = (
        f"The complete Hayom Yom archive: all {total} daily entries in the "
        "original Hebrew, one for every day of the Jewish year, browsable by "
        "Hebrew month and day.")

    items = "\n".join(
        f'    <li><a href="/hayom-yom/{SLUGS[m]}/">{esc(hebcal.MONTHS[m])}'
        f'<span class="he">{esc(hebcal.MONTH_HE[m])}</span></a></li>'
        for m, _ in months
    )

    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": url + "#archive",
                "url": url,
                "name": "Hayom Yom archive",
                "description": description,
                "isPartOf": {"@id": f"{SITE}/#website"},
            },
            breadcrumbs([
                ("luach.day", f"{SITE}/"),
                ("Hayom Yom", url),
            ]),
        ],
    }

    return "", HEAD.format(
        title=esc(title), description=esc(description), url=url, site=SITE,
        og_title="Hayom Yom — complete daily archive", og_type="website",
        crumb=f'<a href="/">luach.day</a>', jsonld=jsonld(graph),
    ) + f"""
  <h1 class="page-title">Hayom Yom</h1>
  <p class="subtitle" lang="he" dir="rtl">&#x05d4;&#x05d9;&#x05d5;&#x05dd; &#x05d9;&#x05d5;&#x05dd; &middot; {total} entries</p>

  <div class="prose">
    <p><em>Hayom Yom</em> &mdash; &ldquo;day by day&rdquo; &mdash; is an anthology
    of Chassidic aphorisms and customs arranged by the days of the Hebrew year,
    compiled in 1942 by Rabbi Menachem Mendel Schneerson, the Lubavitcher Rebbe,
    at the instruction of his father-in-law, the Previous Rebbe. It carries one
    short entry for each day: a teaching, a custom, or a remembered practice.</p>
    <p>All {total} entries are collected here in the original Hebrew, one page per
    Hebrew date. Start with <a href="/">today&rsquo;s entry</a>, or choose a
    month below.</p>
  </div>

  <h2 class="section-head">Months of the Jewish year</h2>
  <ul class="grid months">
{items}
  </ul>
""" + FOOTER.format(site=SITE)


def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def main():
    data = json.loads((ROOT / "hayomyom.json").read_text(encoding="utf-8"))

    # Calendar-ordered list of every entry: Tishri 1 .. Elul 29.
    months = []
    for m in ORDER:
        days = sorted(int(k.rsplit("-", 1)[1]) for k in data if
                      k.rsplit("-", 1)[0] == m)
        if days:
            months.append((m, days))
    sequence = [(m, d) for m, days in months for d in days]

    if OUT.exists():
        shutil.rmtree(OUT)

    urls = [(f"{SITE}/", "daily"), (f"{SITE}/hayom-yom/", "monthly")]

    _, body = archive_page(months)
    write(OUT / "index.html", body)

    for m, days in months:
        slug, body = month_page(m, days, data)
        write(OUT / slug / "index.html", body)
        urls.append((f"{SITE}/hayom-yom/{slug}/", "yearly"))

    for i, (m, d) in enumerate(sequence):
        prev_m, prev_d = sequence[i - 1]
        next_m, next_d = sequence[(i + 1) % len(sequence)]
        prev_ref = (f"{SLUGS[prev_m]}-{prev_d}",
                    f"{prev_d} {hebcal.MONTHS[prev_m]}")
        next_ref = (f"{SLUGS[next_m]}-{next_d}",
                    f"{next_d} {hebcal.MONTHS[next_m]}")
        slug, body = entry_page(m, d, data[f"{m}-{d}"], prev_ref, next_ref)
        write(OUT / slug / "index.html", body)
        urls.append((f"{SITE}/hayom-yom/{slug}/", "yearly"))

    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, freq in urls:
        priority = "1.0" if url == f"{SITE}/" else (
            "0.9" if url.endswith("/hayom-yom/") else "0.7")
        lines += ["  <url>", f"    <loc>{url}</loc>",
                  f"    <lastmod>{today}</lastmod>",
                  f"    <changefreq>{freq}</changefreq>",
                  f"    <priority>{priority}</priority>", "  </url>"]
    lines.append("</urlset>")
    write(ROOT / "sitemap.xml", "\n".join(lines) + "\n")

    print(f"{len(sequence)} entry pages, {len(months)} month pages, "
          f"1 archive page, {len(urls)} sitemap URLs")


if __name__ == "__main__":
    main()
