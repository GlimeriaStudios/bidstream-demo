"""Refresh a single publisher. A failed fetch or unrecognized listing preserves the previous snapshot."""
import argparse
import hashlib
import html as entities
import json
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from lxml import etree, html

UTC = timezone.utc
TODAY = datetime.now(UTC).date()
CUTOFF = TODAY - timedelta(days=45)
MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"


def read(url):
    request = Request(url, headers={"User-Agent": "BidStream/1.0 (+https://glimeriastudios.github.io/bidstream-demo/)"})
    with urlopen(request, timeout=35) as response:
        body = response.read(14_000_001)
    if len(body) > 14_000_000:
        raise ValueError("Unexpectedly large listing")
    return body


def document(url):
    return html.fromstring(read(url).decode("utf-8-sig"))


def clean(value):
    return " ".join(entities.unescape(value or "").split())


def words(element):
    return clean(" ".join(element.itertext()))


def published_text(value):
    for fmt in ("%d %B %Y", "%B %d, %Y", "%b %d, %Y", "%A, %d %B %Y %H:%M"):
        try:
            return datetime.strptime(clean(value), fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def notice(source, key, title, url, country, buyer="", published="", deadline="", kind="Tender notice", description="", language=""):
    if not key or not clean(title) or urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
        raise ValueError("Missing notice identity or HTTPS link")
    return dict(id=source + "-" + hashlib.sha256(str(key).encode()).hexdigest()[:20],
                title=clean(title), country=country, buyer=clean(buyer), source=NAMES[source],
                url=url, published=published, deadline=deadline, type=kind,
                description=clean(description), language=language)


def malawi(source):
    root = document("https://www.ppda.mw/tenders")
    tables = [table for table in root.xpath("//table") if "Closing Date" in words(table) and "Reference No." in words(table)]
    if len(tables) != 1:
        raise ValueError("Missing procurement notices table")
    rows = tables[0].xpath(".//tr[td]")
    if not rows and "no procurement notices" not in words(tables[0]).lower():
        raise ValueError("Unexpected empty procurement table")
    for row in rows:
        cells = row.xpath("./td")
        if len(cells) != 6:
            raise ValueError("Changed PPDA notice layout")
        title, buyer, ref, pub, due = [words(c) for c in cells[:5]]
        if re.search(r"^cancell?ation|^notification of (?:intention|award)|^award of", title, re.I):
            continue
        links = cells[5].xpath(".//a/@href")
        if not links:
            raise ValueError("Notice attachment missing")
        day = date.fromisoformat(due)
        if day < TODAY:
            continue
        url = urljoin("https://www.ppda.mw/tenders", links[0]).replace(" ", "%20")
        yield notice(source, url, title, url, "Malawi", buyer, date.fromisoformat(pub).isoformat(), due, description=ref)


def south_sudan(source):
    base = "https://tenderportal.ppdaa.gov.ss"
    root = document(base + "/current-bids")
    cards = root.xpath('//a[starts-with(@href,"/bid/")][.//h4]')
    if not cards and not re.search(r"no (?:current |open )?(?:bids|results)|0\s+(?:open bids|tenders)", words(root), re.I):
        raise ValueError("Unrecognized current-bid listing")
    for card in cards:
        due = card.xpath('.//time/@datetime')
        if not due:
            raise ValueError("Missing submission deadline")
        url = urljoin(base, card.get("href"))
        yield notice(source, url, words(card.xpath(".//h4")[0]), url, "South Sudan", deadline=due[0])


def burundi(source):
    base = "https://armp.gov.bi/wp-json/wp/v2/posts?"
    # The regulator separates supplies (29), services (24) and works (31).
    params = {"categories": "29,24,31", "after": CUTOFF.isoformat() + "T00:00:00",
              "per_page": 100, "_fields": "id,date,title,link,categories"}
    for page_no in range(1, 21):
        params["page"] = page_no
        with urlopen(Request(base + urlencode(params), headers={"User-Agent": "BidStream/1.0"}), timeout=35) as response:
            rows = json.load(response)
            total = int(response.headers["X-WP-TotalPages"])
        if not isinstance(rows, list) or total > 20:
            raise ValueError("Unexpected ARMP page count")
        for row in rows:
            title = clean(row["title"]["rendered"])
            if not re.search(r"appel d[’' ]offres?|manifestation d[’' ]int[ée]r[êe]t|demande de (?:cotation|propositions?)", title, re.I):
                continue
            if re.search(r"annul|attribut|résultat|rectificatif|avis de report", title, re.I):
                continue
            categories = {29: "Fournitures", 24: "Services", 31: "Travaux"}
            kind = ", ".join(categories[c] for c in row["categories"] if c in categories)
            yield notice(source, row["id"], title, row["link"], "Burundi", published=row["date"][:10], kind=kind, language="fr")
        if page_no >= total:
            return


def power(source):
    base = "https://www.eep.com.et/?page_id=5157"
    root = document(base)
    links = root.xpath('//h2/a[contains(@href,"?tender=")]')
    if not links:
        raise ValueError("EEP tender cards missing")
    for link in links:
        title = words(link)
        times = link.getparent().getparent().xpath('.//time/@datetime')
        if not times:
            raise ValueError("EEP publication date missing")
        pub = date.fromisoformat(times[0][:10])
        if pub < CUTOFF or not re.search(r"invitation|request for|procurement notice|REOI|bidding|expression of interest", title, re.I):
            continue
        yield notice(source, link.get("href"), title, link.get("href"), "Ethiopia", "Ethiopian Electric Power", pub.isoformat())


def utility(source):
    base = "https://eeu.gov.et"
    root = document(base + "/en/tenders")
    cards = root.xpath('//a[starts-with(@href,"/en/tenders/")][.//h3]')
    if not cards and not re.search(r"no (?:open |active )?(?:tenders|notices)", words(root), re.I):
        raise ValueError("EEU tender listing missing")
    for card in cards:
        body = words(card)
        if not body.startswith("Open ") or re.search(r"asset disposal|SCRAP|የሚወገድ", body, re.I):
            continue
        close = re.search(r"Closes\s+("+MONTH+r" \d{1,2}, \d{4})", body, re.I)
        if not close or not (due := published_text(close[1])):
            raise ValueError("EEU Gregorian closing date missing")
        if due < TODAY.isoformat():
            continue
        link = urljoin(base, card.get("href"))
        yield notice(source, link, words(card.xpath(".//h3")[0]), link, "Ethiopia", "Ethiopian Electric Utility", deadline=due)


def seychelles(source):
    base = "https://www.ntb.sc/"
    root = document(base)
    cards = root.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " jt-inner ")]')
    if not cards:
        raise ValueError("NTB listing missing")
    for card in cards:
        links = card.xpath('.//a[@class="jt-title"]')
        if not links:
            continue
        link = links[0]
        path = link.get("href", "")
        if not re.fullmatch(r"/tenders/[^/]+|/2-stage-tender/[^/]+/[^/]+", path) or re.search(r"cancel|award", path, re.I):
            continue
        stamps = card.xpath('.//span[@class="jtc_introdate"]/text()')
        if not stamps or not (pub := published_text(stamps[0])):
            raise ValueError("NTB publication date missing")
        if pub < CUTOFF.isoformat():
            continue
        url = urljoin(base, path)
        yield notice(source, path, words(link), url, "Seychelles", published=pub)


def regional_rss(source):
    trade = source == "trademark-africa"
    url = "https://trademarkafrica.com/category/tenders/feed/" if trade else "https://www.comesa.int/category/consultancies/feed/"
    channel = etree.fromstring(read(url), etree.XMLParser(resolve_entities=False, no_network=True)).find("channel")
    if channel is None or not channel.findtext("title"):
        raise ValueError("Expected the publisher's RSS channel")
    for item in channel.findall("item"):
        title = clean(item.findtext("title"))
        pub = parsedate_to_datetime(item.findtext("pubDate")).date()
        if pub < CUTOFF:
            continue
        country = "COMESA region"
        if trade:
            markets = re.findall(r"\b(?:Kenya|Uganda|Rwanda|Tanzania|Burundi|Ethiopia|Somalia|South Sudan|Djibouti|Malawi|Mozambique|Zambia|Madagascar|DRC|East African Community|East Africa)\b", title, re.I)
            if not markets:
                continue
            country = ", ".join(dict.fromkeys(m.title() if m.upper() != "DRC" else "Democratic Republic of the Congo" for m in markets))
        body = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or item.findtext("description") or ""
        content = words(html.fromstring(body)) if body.strip() else ""
        due = ""
        for match in re.finditer(r"(?:submission deadline|deadline for submission)[^:]{0,100}:\s*(\d{1,2} "+MONTH+r" \d{4}|"+MONTH+r" \d{1,2}, \d{4})", content, re.I):
            due = published_text(match[1])
        if due and due < TODAY.isoformat():
            continue
        link = item.findtext("link")
        yield notice(source, link, title, link, country, "TradeMark Africa" if trade else "COMESA Secretariat",
                     pub.isoformat(), due, "Procurement notice" if trade else "Consultancy")


def boamp(source):
    endpoint = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records?"
    for area, country in [("974", "Réunion"), ("976", "Mayotte")]:
        offset = 0
        while True:
            params = {"where": "code_departement='"+area+"' AND nature_categorise='appeloffre/standard' AND datelimitereponse >= now()",
                      "select": "idweb,objet,dateparution,datelimitereponse,nomacheteur,url_avis,code_departement",
                      "order_by": "dateparution DESC,idweb ASC", "limit": 100, "offset": offset}
            batch = json.loads(read(endpoint + urlencode(params)))
            rows = batch["results"]
            if not isinstance(rows, list) or not isinstance(batch["total_count"], int) or (not rows and offset < batch["total_count"]):
                raise ValueError("Unexpected BOAMP pagination")
            for item in rows:
                codes = item["code_departement"] or []
                markets = [label for code, label in [("974", "Réunion"), ("976", "Mayotte")] if code in codes]
                yield notice(source, item["idweb"], item["objet"], item["url_avis"], ", ".join(markets) or country,
                             item["nomacheteur"], item["dateparution"][:10], item["datelimitereponse"], description="BOAMP / DILA " + item["idweb"], language="fr")
            offset += len(rows)
            if offset >= batch["total_count"]:
                break
            if offset >= 10000:
                raise ValueError("BOAMP result exceeds API offset window")


def zambia(source):
    base = "https://eprocure.zppa.org.zm/epps/notices/viewPublishedNotices.do"
    root = document(base)
    tables = [t for t in root.xpath("//table") if [words(h) for h in t.xpath(".//th")][:3] == ["Type", "Title", "Date Upl."]]
    if len(tables) != 1:
        raise ValueError("Missing ZPPA publication table")
    for row in tables[0].xpath(".//tr[td]"):
        cells = row.xpath("./td")
        if len(cells) != 6:
            raise ValueError("Changed ZPPA notice fields")
        if words(cells[0]) != "Tender Notice" or words(cells[4]) != "Published":
            continue
        pub = datetime.strptime(words(cells[5]), "%d/%m/%Y %H:%M:%S").date()
        if pub < CUTOFF:
            continue
        link = urljoin(base, cells[0].xpath(".//a/@href")[0])
        yield notice(source, link, words(cells[1]), link, "Zambia", published=pub.isoformat())


def igad(source):
    # The legacy category feed stopped updating in 2022. These are the filters used by the live boards.
    for kind in ("consultancies", "tender"):
        channel = etree.fromstring(read("https://igad.int/?feed=job_feed&job_types=" + kind),
                                   etree.XMLParser(resolve_entities=False, no_network=True)).find("channel")
        if channel is None or not channel.findtext("title"):
            raise ValueError("Missing IGAD listings feed")
        for item in channel.findall("item"):
            title = clean(item.findtext("title"))
            pub = parsedate_to_datetime(item.findtext("pubDate")).date()
            if pub < CUTOFF:
                continue
            location = clean(item.xpath('string(*[local-name()="location"])'))
            # Some Sudan projects list Kenya as the administrative posting location.
            if re.search(r"Khartoum|\bin Sudan\b", title, re.I) and not re.search(r"South Sudan|Djibouti|Ethiopia|Somalia|Uganda|Kenya", title, re.I):
                continue
            if not re.search(r"Djibouti|Ethiopia|Eritrea|Kenya|Somalia|Uganda|South Sudan|IGAD", location + " " + title, re.I):
                continue
            raw = item.xpath('string(*[local-name()="encoded"])')
            body = words(html.fromstring(raw)) if raw else ""
            dates = re.findall(r"(?:delivered|emailed|submitted)[^.]{0,100}?\bby (?:[\w:+ -]{0,30}? on )?(\d{1,2})(?:st|nd|rd|th)? (" + MONTH + r") (20\d{2})", body, re.I)
            due = published_text(" ".join(dates[-1])) if dates else ""
            if due and due < TODAY.isoformat():
                continue
            url = item.findtext("link")
            yield notice(source, url, title, url, location or "IGAD region", "IGAD", pub.isoformat(), due, kind.capitalize())

PUBLISHERS = {
    "zambia-zppa": ("Zambia ZPPA", zambia), "igad-opportunities": ("IGAD", igad),
    "burundi-armp": ("Burundi ARMP", burundi), "malawi-ppda": ("Malawi PPDA", malawi),
    "south-sudan-ppdaa": ("South Sudan PPDAA", south_sudan), "ethiopia-eep": ("Ethiopia EEP", power),
    "ethiopia-eeu": ("Ethiopia EEU", utility), "seychelles-ntb": ("Seychelles NTB", seychelles),
    "trademark-africa": ("TradeMark Africa", regional_rss), "comesa-consultancies": ("COMESA Consultancies", regional_rss),
    "boamp-indian-ocean": ("BOAMP Indian Ocean", boamp),
}
NAMES = {key: settings[0] for key, settings in PUBLISHERS.items()}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=PUBLISHERS)
    args = parser.parse_args()
    unique = {item["id"]: item for item in PUBLISHERS[args.source][1](args.source)}
    payload = {"checkedAt": datetime.now(UTC).isoformat(), "notices": list(unique.values())}
    dest = Path(__file__).with_name(args.source + ".json")
    temp = dest.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(dest)
    print(args.source, len(unique))
