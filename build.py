#!/usr/bin/env python3
"""
Kolkata Travel Router — data pipeline
----------------------------------
Reads raw route dumps (format:  CODE: Origin to Destination | stop, stop, ...),
normalises the inconsistent stop names, builds a routing graph, and exports a
single JSON that the web app consumes.

The normalisation layer is the important part: the source data spells the same
place many ways (Rashbehari/Rashbihari, Kidderpore/Khiderpur, Barabazar/
Burrabazar, Dum Dum/Dumdum, ...). Everything below funnels through canon().
"""
import ast, json, os, re, itertools, unicodedata
from collections import defaultdict, deque

GRAPH_INSERT_MIN_KM = 0.8
GRAPH_INSERT_MAX_KM = 2.2
GRAPH_INSERT_MAX_PER_EDGE = 3
INTERMEDIATE_HINTS_FILE = "route_intermediate_hints.json"

# ---------------------------------------------------------------- normalisation
# 1) token-level spelling fixes applied to the lowercased, punctuation-stripped key
SPELLING = {
    "rashbihari": "rashbehari", "rasbehari": "rashbehari",
    "khiderpur": "kidderpore", "khidirpur": "kidderpore", "kidderpur": "kidderpore",
    "khidderpore": "kidderpore", "khiderpore": "kidderpore",
    "burrabazar": "barabazar", "burra bazar": "barabazar",
    "bazer": "bazar",
    "mominpur": "mominpore",
    "bhawanipur": "bhowanipore", "bhowanipur": "bhowanipore", "bhawanipore": "bhowanipore",
    "tollygunj": "tollygunge",
    "dum dum": "dumdum",
    "salt lake": "saltlake",
    "ajoynagar": "ajaynagar",
    "baguihati": "baguiati",
    "keshtopur": "kestopur",
    "chiriamore": "chiria more",
    "sinthee": "sinthi",
    "rajabajar": "rajabazar",
    "deshoprio park": "deshapriya park", "desapriya park": "deshapriya park",
    "girishpark": "girish park",
    "manicktala": "maniktala",
    "ballygaunj": "ballygunge", "ballygunj": "ballygunge",
    "belgachhia": "belgachia",
    "belgacchia": "belgachia",
    "belghoria": "belgharia",
    "ultodanga": "ultadanga",
    "lake town": "laketown",
    "beliaghata": "beleghata",
    "sova bajar": "sovabazar", "sova bazar": "sovabazar",
    "sobhabazar": "sovabazar", "shobhabazar": "sovabazar",
    "haldiram": "haldirams",
    "anwarsah road": "anwar shah road", "anwar sha connector": "prince anwar shah connector",
    "p a sha connector": "prince anwar shah connector",
    "p a shah road": "anwar shah road", "pa shah road": "anwar shah road",
    "p a sha road": "anwar shah road",
    # --- added after duplicate audit (pure spelling variants) ---
    "dakshineshwar": "dakshineswar",
    "chadni": "chandni",
    "nagerbazar": "nager bazar",
    "sakherbazar": "sakher bazar",
    "sakherbzar": "sakher bazar",
    "mallickbazar": "mallick bazar",
    "mullickbazar": "mallick bazar",
    "shishu": "sishu",
    "shishumangal": "sishu mangal",
    "alipur": "alipore",
    "baishnabghata": "baisnabghata",
    "golfgreen": "golf green",
    "khardah": "khardaha",
    "mollargate": "mollar gate",
    "bhawani bhawan": "bhabani bhawan",
    "bichali ghar": "bichali ghat",
    "parnashree": "parnasree",
    "safuipara": "sapuipara",
    "khashmallik": "khasmallick",
    "gobindopur": "gobindapur",
    "malncha": "malancha",
    "tegharia": "teghoria",
    "majerhat": "majherhat",
    "sarobar": "sarovar",
    "phillips": "philips",
    "chingrihata": "chingrighata",
    "uttar panchannangram": "uttar panchannagram",
    "techonopolis": "technopolis",
    "akansha": "akanksha",
    "akankha": "akanksha",
    "highland park": "hiland park",
    "belepol": "belepole",
    "moulai": "moulali",
    "rabinrasadan": "rabindra sadan",
    "susrut": "sushrut",
    "shreebhumi": "sreebhumi",
    "santragachhi": "santragachi",
    "bamangachhi": "bamangachi",
    "joygachhi": "joygachi",
    "joygacchi": "joygachi",
    "bhaban": "bhawan",
    "udainarayanpur": "udaynarayanpur",
    "udanarayanpur": "udaynarayanpur",
    "udaynaryanpur": "udaynarayanpur",
    "bashirhat": "basirhat",
    "ramnarayanpurramnarayanpur": "ramnarayanpur",
    "v i p": "vip",
    "ultodanga": "ultadanga",
    "doltola": "doltala",
    "bonhoogly": "bonhooghly",
    "silpara": "shilpara",
    "champadali": "chapadali",
    "nababpur": "nawabpur",
    "bakshara": "baksara",
    "mallikbazar": "mallick bazar",
    "jinjira": "jhinjhira",
    "bajar": "bazar",
    "shirakol": "shirakole",
    "shirakhole": "shirakole",
    "kadambagacchi": "kadambagachi",
    "sevasram": "sevashram",
    "sodpur": "sodepur",
    "murarishah": "murarisha",
    "vandergachha": "vandergacha",
    "notun rastar": "natun rasta",
    "natun rastar": "natun rasta",
    "mahisbatan": "mahishbathan",
    "mahisbathan": "mahishbathan",
    "subhasnagar": "subhash nagar",
    "najrul": "nazrul",
    "kazi bari": "kazibari",
    "d l f": "dlf",
    "b t": "bt",
    "b t college": "bt college",
    "a p c": "apc",
    "a p c college": "apc college",
    "m g road": "mg road",
    "c i t road": "cit road",
    "p g hospital": "pg hospital",
    "p n b": "pnb",
    "s d f": "sdf",
    "w i p r o": "wipro",
    "r n chowdhury road": "rn chowdhury road",
    "eco park": "ecopark",
    "eco space": "ecospace",
    "new town": "newtown",
    "narkel bagan": "narkelbagan",
    "chinarpark": "chinar park",
    "new barrack pore": "new barrackpore",
    "michael nagar": "michaelnagar",
    "ashok nagar": "ashoknagar",
    "ashoknaga": "ashoknagar",
    "ashokenagar": "ashoknagar",
    "lake town": "laketown",
    "bally halt": "ballyhalt",
    "bally ghat": "ballyghat",
    "sukanta nagar": "sukantanagar",
    "rabindrasadan": "rabindra sadan",
    "beckbagan": "beck bagan",
    "bekbagan": "beck bagan",
    "dutta pukur": "duttapukur",
    "bakul tala": "bakultala",
    "bow bazar": "bowbazar",
    "das nagar": "dasnagar",
    "japanigate": "japani gate",
    "borali ghat": "boralighat",
    "hela battala": "helabattala",
    "kali park": "kalipark",
    "dhulor bandh": "dhulorbandh",
    "lal bazar": "lalbazar",
    "lal kuthi": "lalkuthi",
    "sarkar bazar": "sarkarbazar",
    "bhyabla halt": "bhyablahalt",
    "pramod nagar": "pramodnagar",
    "dhruba bazar": "dhrubabazar",
    "home town": "hometown",
    "prafulla nagar": "prafullanagar",
    "ukiler hat": "ukilerhat",
    "bidhan nagar college": "bidhannagar college",
    "p t s": "pts",
    "jadavpur p s": "jadavpur ps",
    "jadavpur thana": "jadavpur ps",
    "e m bypass": "em bypass",
    "b k paul": "bk paul",
    "s m nagar": "sm nagar",
    "c a island": "saltlake ca block",
    "ca island": "saltlake ca block",
    "saltlake c a block": "saltlake ca block",
    "b e college": "be college",
}
# 2) full-string aliases -> ONLY two-names-for-one-physical-point synonyms and
#    shorthand disambiguation. We deliberately do NOT merge facility-tagged stops.
#
#    Kolkata rule of thumb (per local feedback): ~2 km apart is a long distance,
#    so anything carrying a distinguishing tag is a SEPARATE stop and must stay
#    separate -- "Kasba" vs "Kasba PS" vs "Kasba Post Office", "Jadavpur" vs
#    "Jadavpur 8B" vs "Jadavpur PS", "Tollygunge" vs "Tollygunge Metro" vs
#    "Tollygunge Phari", every numbered Airport gate / Saltlake tank, Station vs
#    area, Bazar vs area, etc. The "X More / X Crossing" case (a junction whose
#    name simply *is* "the X crossing") is folded in canon() below, not here.
ALIASES = {
    # genuine two-names-for-one-spot synonyms only
    "dalhousie": "bbd bag", "b b d bag": "bbd bag",
    "esplanade l20": "esplanade",
    "howrah stn": "howrah station",
    "sealdah station": "sealdah", "sealdah stn": "sealdah",
    "central metro": "central",
    "maidan metro": "maidan",
    "howrah": "howrah station",
    "chandni": "chandni chowk", "chandni market": "chandni chowk",
    "shyambazar 5 point": "shyambazar",
    "rg kar hospital": "rg kar", "r g kar": "rg kar",
    "ruby hospital": "ruby",
    "belgachia metro": "belgachia",
    "sovabazar metro": "sovabazar", "sovabazar sutanuti": "sovabazar",
    "mahatma gandhi road": "mg road", "mg road metro": "mg road",
    "building": "beleghata building",
    "cit": "beleghata cit",
    "id hospital": "beleghata id hospital",
    "sales tax": "beleghata sales tax",
    "college": "college more",
    "saltlake karunamoyee": "karunamoyee",
    "saltlake sector v": "sector v", "sector v saltlake": "sector v",
    "sec v": "sector v",
    "city center": "city center 1", "city centre": "city center 1",
    "city centre 1": "city center 1", "city centre 2": "city center 2",
    "durgapur city centre": "durgapur city center",
    "ballygunge stn": "ballygunge station",
    "ballygunge s t n": "ballygunge station",
    "bidhannagar road": "ultadanga",
    "santragachi bus terminal": "santragachi bus terminus",
    "unitech gate no 1": "unitech gate 1",
    "airport 1 no gate": "airport gate 1",
    "airport 3 no gate": "airport gate 3",
    "bridge 4": "4 no bridge", "bridge no 4": "4 no bridge",
    # shorthand -> full name (keeps the place distinct, just spelled in full)
    "8b": "jadavpur 8b",
    "hudco": "ultadanga hudco",
    "hudco more": "ultadanga hudco",
    "pnb": "saltlake pnb",
    "pnb more": "saltlake pnb",
    "pnb island": "saltlake pnb",
    "tank 4": "saltlake 4no tank",
    "4 no tank": "saltlake 4no tank",
    "10 no tank": "saltlake 10no tank",
    "tank no 10": "saltlake 10no tank",
    "ultadanga station": "ultadanga",
    "ultodanga station": "ultadanga",
    "airport 1no": "airport gate 1", "airport 1": "airport gate 1",
    "airport 3no": "airport gate 3", "airport 3": "airport gate 3",
    "airport gate-1": "airport gate 1", "airport gate no 1": "airport gate 1",
    "airport gate-3": "airport gate 3", "airport gate no 3": "airport gate 3",
    "airport 3 gate": "airport gate 3", "airport 3no gate": "airport gate 3",
    "airport 2 no gate": "airport gate 2", "airport gate no 2": "airport gate 2",
    "airport gate 2 5": "airport gate 2.5", "airport gate no 2 5": "airport gate 2.5",
    "behala 14": "behala 14 no", "behala 14no": "behala 14 no",
    "dlf 1": "dlf1", "dlf1": "dlf1",
    "dlf 2": "dlf2", "dlf2": "dlf2",
    "city center-1": "city center 1",
    "city center-2": "city center 2",
    "4no bridge": "4 no bridge",
    "10no pole": "10 no pole",
    "8no kalibari": "8 no kalibari",
    "58-gate": "58 gate",
    "barasat dak bunglow": "barasat dakbunglow",
    "bongaon 1no railgate bazar": "bongaon 1 no railgate bazar",
    "baruipur fultala central terminus": "baruipur fultala",
    "barasat champadali": "barasat chapadali",
    "botanical garden": "b garden", "botanic garden": "b garden",
    "shapooji housing": "shapoorji",
    "shapoorji housing": "shapoorji",
    "sukho brishti": "shapoorji", "sukhobrishti": "shapoorji",
}
IGNORED_STOPS = {"more", "2", "3"}
STOP_EXPANSIONS = {
    "thakurpukur bazar thakurpukur 3a": ["Thakurpukur Bazar", "Thakurpukur 3A"],
}
# BusRepo's own search aliases from script.js replaceLocAlias(). Keep these
# conservative: only same-place spellings, or a familiar name pointed at the
# nearest explicit stop when the source data has no separate stop for it.
BUSREPO_SEARCH_ALIASES = {
    "Bidhannagar Road": "Ultadanga",
    "Exide More": "Exide",
    "PG": "Rabindra Sadan",
    "Dharmatala": "Esplanade",
    "Sector V": "College More",
    "Biswa Bangla Gate": "Narkelbagan",
    "Mint": "Mominpore",
    "Yuva Bharati Kirangan": "Saltlake Stadium",
    "Yuva Bharati Krirangan": "Saltlake Stadium",
    "Yuba Bharati Krirangan": "Saltlake Stadium",
    "CMRI Hospital": "Ekbalpur",
    "TCS Gitobitan": "Wipro More",
    "Panihati": "Ghola Bazar",
    "Candor Techspace": "Unitech Gate 1",
    "RDB Cinema": "SDF More",
}
# Search-only aliases make familiar local names discoverable without adding
# stops or edges to the graph. Keep these pointed at existing source stops.
SEARCH_ALIASES = {
    "Hudco": ["Ultadanga Hudco", "Ultadanga"],
    "Hazra More": "Hazra",
    "Topsia More": "Topsia",
    "Lake Town": "Laketown",
    "Prince Anwar Shah Connector": "Anwar Shah Road",
    "Chetla": "Chetla Park",
}
# words that mark a junction -- "X More" is the same point as "X"
JUNCTION = re.compile(r"\s+(more|crossing|xing)$")

def strip_notes(name):
    """Remove bracketed clarifications that otherwise become fake stop names."""
    s = unicodedata.normalize("NFKC", name).replace("|", " ")
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"[\(\[].*$", "", s)
    s = s.replace(")", " ").replace("]", " ")
    return re.sub(r"\s+", " ", s).strip()

def raw_key(name):
    s = strip_notes(name).lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[.\(\)\[\]]", " ", s)
    s = re.sub(r"\bno\.?\b", "no", s)
    s = re.sub(r"\bnumber\b", "no", s)
    return re.sub(r"\s+", " ", s).strip()

def terminal_name(name):
    s = strip_notes(name)
    if "/" in s:
        s = s.split("/", 1)[0].strip()
    return s

def add_stop(seq, raw_stop):
    for item in STOP_EXPANSIONS.get(raw_key(raw_stop), [raw_stop]):
        c = canon(item)
        if c and (not seq or seq[-1] != c):
            seq.append(c)

def canon(name):
    """messy stop string -> canonical Title-Case display name."""
    s = strip_notes(name).lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[.\(\)\[\]]", " ", s)              # drop punctuation
    s = re.sub(r"\bno\.?\b", "no", s)               # no. / no -> no
    s = re.sub(r"\bnumber\b", "no", s)
    s = re.sub(r"\s+", " ", s).strip()
    for a, b in SPELLING.items():                   # token-level spelling fixes
        s = re.sub(r"\b" + re.escape(a) + r"\b", b, s)   # word-boundary: no substring bleed
    s = re.sub(r"\s+", " ", s).strip()
    s = JUNCTION.sub("", s)                         # "X More/Crossing" == "X"
    s = ALIASES.get(s, s)                           # synonym merge
    if s in IGNORED_STOPS:
        return ""
    out = []
    for w in s.split():
        if w in ("bbd", "rg", "mg", "ps", "pts", "bnr", "sdf", "cit",
                 "gpo", "hmg", "nshm", "dlf", "sm", "wbtc", "id", "ils",
                 "kbkc", "amri", "gst", "ca", "fd", "gd", "bt", "apc",
                 "rn", "pg", "pnb", "em", "bk", "be", "vip", "ibm", "itc",
                 "ongc", "bit"):
            out.append(w.upper())
        elif re.fullmatch(r"dlf\d+", w):
            out.append("DLF " + w[3:])
        elif re.fullmatch(r"\d+[a-z]", w):          # stand codes: 8b -> 8B
            out.append(w.upper())
        else:
            out.append(w.capitalize())
    return " ".join(out)

# ---------------------------------------------------------------- parsing
# Accepts the native Kolbusopedia shapes, no reformatting needed:
#   CODE: Origin to Destination [via: a, b, c]
#   CODE:- Origin to Destination [via a, b]
#   CODE: Origin to Destination ( via a, b )
#   VS1:- Origin to Destination via a, b        (no brackets)
#   DN12: Origin - Destination [Via: a, b]
#   RT-35: Origin to Destination [a, b]          (bracketed stops, no "via")
def parse(path, kind, directional=False, scope="local", source="kolbusopedia"):
    routes, skipped = [], 0
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        code, rest = line.split(":", 1)
        code = code.strip()
        rest = rest.strip().lstrip("-").strip()
        bracket = re.search(r"\[(.*?)\]\s*$", rest)
        if bracket:
            head = rest[:bracket.start()]
            via = bracket.group(1)
        else:
            m = re.search(r"\bvia\b", rest, re.I)             # locate the via-list
            head, via = (rest[:m.start()], rest[m.end():]) if m else (rest, "")
        head = head.strip().rstrip("[(").strip()
        via = re.sub(r"^\s*via\s*[:-]?\s*", "", via, flags=re.I)
        via = via.strip().lstrip(":").strip(" []()").rstrip(").]").strip()
        low = head.lower()
        if " to " in low:
            i = low.find(" to ")
            origin, dest = head[:i], head[i+4:]
        else:
            m = re.search(r"\s+-\s+", head)
            if not m:
                skipped += 1; continue
            origin, dest = head[:m.start()], head[m.end():]
        if not origin.strip() or not dest.strip():
            skipped += 1; continue
        origin = terminal_name(origin)
        dest = terminal_name(dest)
        parts = [origin] + re.split(r"[,/]", via) + [dest]    # split on , and /
        seq = []
        for p in parts:
            add_stop(seq, p)
        if len(seq) >= 2:
            route = {"code": code, "kind": kind, "origin": seq[0], "dest": seq[-1],
                     "stops": seq, "scope": scope, "source": source}
            if directional:
                route["directional"] = True
            routes.append(route)
    if skipped:
        print(f"  ({skipped} non-route lines skipped in {path})")
    return routes

BUSREPO_FILES = (
    "raw_busrepo_routes1.js",
    "raw_busrepo_routes2.js",
    "raw_busrepo_routes3.js",
    "raw_busrepo_routes4.js",
)
BUSREPO_ROUTE_RE = re.compile(
    r"^\s*(.*?)\s*:\s*(.*?)\s*\[\s*via\s*:?\s*(.*?)\s*\]\s*:",
    re.I,
)

def busrepo_kind(code, head):
    text = f"{code} {head}".lower()
    if "mini" in text:
        return "mini"
    if any(tag in text for tag in ("nbstc", "sbstc", "wbtc", "cstc", "ctc")):
        return "government"
    if re.match(r"^(ac|vs|st|e-|d-|s-?\d|sd-|dn-|kb|k-|c\b)", code.strip(), re.I):
        return "government"
    return "private"

def iter_js_route_strings(path):
    """Yield quoted route strings from Bus Repository's route JS arrays."""
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("//") or not line.startswith(('"', "'")):
            continue
        try:
            yield ast.literal_eval(line.rstrip(","))
        except (SyntaxError, ValueError):
            continue

def parse_busrepo_file(path):
    routes, skipped = [], 0
    scope = "local" if path.endswith("routes1.js") else "regional"
    for raw_route in iter_js_route_strings(path):
        m = BUSREPO_ROUTE_RE.match(raw_route)
        if not m:
            skipped += 1
            continue
        code, head, via = (m.group(1).strip(), m.group(2).strip(), m.group(3).strip())
        seq = []
        for part in via.split(","):
            add_stop(seq, part)
        if len(seq) < 2:
            skipped += 1
            continue
        routes.append({
            "code": code,
            "kind": busrepo_kind(code, head),
            "origin": seq[0],
            "dest": seq[-1],
            "stops": seq,
            "directional": True,
            "scope": scope,
            "source": "busrepo",
        })
    print(f"parsed {len(routes)} directional routes from {path}")
    if skipped:
        print(f"  ({skipped} non-route lines skipped in {path})")
    return routes

def parse_busrepo_routes():
    if not all(os.path.exists(path) for path in BUSREPO_FILES):
        return []
    return list(itertools.chain.from_iterable(parse_busrepo_file(path) for path in BUSREPO_FILES))

def route_match_key(code):
    code = re.sub(r"\(.*?\)", "", code).strip()
    return re.sub(r"[^A-Za-z0-9]", "", code).upper()

def apply_intermediate_hints(routes, path=INTERMEDIATE_HINTS_FILE):
    """
    Restore only bounded intermediate stops from older matched route data.

    The current BusRepo route remains authoritative: a hint can only fill an
    existing adjacent edge A -> C on the same route code, never create or
    replace a route.
    """
    try:
        raw_hints = json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        print("no route intermediate hints file found")
        return

    hints_by_code = defaultdict(list)
    for hint in raw_hints:
        a, c = hint.get("from"), hint.get("to")
        mids = hint.get("stops") or []
        if a and c and mids:
            hints_by_code[route_match_key(hint.get("code", ""))].append((a, c, mids))

    added = 0
    touched = 0
    for route in routes:
        hints = hints_by_code.get(route_match_key(route["code"]))
        if not hints:
            continue
        by_edge = {(a, c): mids for a, c, mids in hints}
        current_stops = set(route["stops"])
        expanded = []
        changed = False
        for a, c in zip(route["stops"], route["stops"][1:]):
            expanded.append(a)
            mids = by_edge.get((a, c), [])
            for stop in mids:
                if stop in current_stops or stop in expanded or stop in (a, c):
                    continue
                expanded.append(stop)
                current_stops.add(stop)
                added += 1
                changed = True
        expanded.append(route["stops"][-1])
        if changed:
            route["stops"] = expanded
            touched += 1
    print(f"restored {added} bounded intermediate stops on {touched} current routes")

PRIVATE_MINI_CODE = re.compile(r"^(S-\d|M-\d|MM\d|MN\d)", re.I)
MINI_PUBLIC_NAMES = {
    "s-106": "Santoshpur BBD Bag Mini",
    "santoshpur mini": "Santoshpur BBD Bag Mini",
}
METRO_LINE_LABELS = {
    "BLUE": "Metro Blue Line",
    "GREEN": "Metro Green Line",
    "ORANGE": "Metro Orange Line",
    "YELLOW": "Metro Yellow Line",
    "PURPLE": "Metro Purple Line",
}

def display_code(route):
    """Use public-facing names for private mini buses instead of fleet-style codes."""
    code = route["code"].strip()
    key = code.lower()
    is_mini = route["kind"] == "mini" or route.get("is_mini") or (
        route["kind"] == "private" and (
            PRIVATE_MINI_CODE.match(code) or key.endswith(" mini")
        )
    )
    if not is_mini:
        return code
    if key in MINI_PUBLIC_NAMES:
        return MINI_PUBLIC_NAMES[key]
    return f"{route['origin']} {route['dest']} Mini"

def enrich_short_gaps(routes, max_missing=2):
    """Fill short omitted stops when another route proves they sit between a pair."""
    between = {}
    for route in routes:
        stops = route["stops"]
        for i, a in enumerate(stops):
            for j in range(i + 2, min(len(stops), i + max_missing + 3)):
                b = stops[j]
                mid = stops[i + 1:j]
                if not mid:
                    continue
                cur = between.get((a, b))
                if cur is None or len(mid) > len(cur):
                    between[(a, b)] = mid
                    between[(b, a)] = list(reversed(mid))

    added = 0
    for route in routes:
        expanded = []
        stops = route["stops"]
        for a, b in zip(stops, stops[1:]):
            expanded.append(a)
            mid = between.get((a, b))
            if not mid:
                continue
            if b in mid or a in mid:
                continue
            if any(stop in stops or stop in expanded for stop in mid):
                continue
            if expanded[-1] == mid[0]:
                mid = mid[1:]
            if mid and b == mid[-1]:
                mid = mid[:-1]
            if not mid:
                continue
            for stop in mid:
                if stop != expanded[-1]:
                    expanded.append(stop)
                    added += 1
        expanded.append(stops[-1])
        route["stops"] = expanded
    print(f"filled {added} short omitted stops")

def route_graph_parts(routes):
    stop_routes = defaultdict(set)
    for i, r in enumerate(routes):
        for s in set(r["stops"]):
            stop_routes[s].add(i)
    stops = sorted(stop_routes)
    route_set = [set(r["stops"]) for r in routes]
    route_adj = defaultdict(set)
    for rs in stop_routes.values():
        for a, b in itertools.combinations(rs, 2):
            route_adj[a].add(b)
            route_adj[b].add(a)
    return stop_routes, stops, route_set, route_adj

def add_export_alias(aliases, stop_set, alias, targets, force=False):
    if isinstance(targets, str):
        targets = [targets]
    for target in targets:
        target = canon(target)
        if target in stop_set and (force or alias not in stop_set):
            aliases[alias] = target
            break

def export_search_aliases(stops):
    stop_set = set(stops)
    aliases = {}
    for alias, targets in SEARCH_ALIASES.items():
        add_export_alias(aliases, stop_set, alias, targets)
    for alias, targets in BUSREPO_SEARCH_ALIASES.items():
        add_export_alias(aliases, stop_set, alias, targets, force=True)
    return dict(sorted(aliases.items(), key=lambda item: item[0].lower()))

def xy(stop, hub):
    lat, lng = hub[stop]
    return lng * 102.7, lat * 111.1

def segment_match(a, b, p, hub):
    ax, ay = xy(a, hub)
    bx, by = xy(b, hub)
    px, py = xy(p, hub)
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    length2 = vx * vx + vy * vy
    if not length2:
        return None
    t = (wx * vx + wy * vy) / length2
    if t <= 0.12 or t >= 0.88:
        return None
    cx, cy = ax + t * vx, ay + t * vy
    dist = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
    length = length2 ** 0.5
    return t, dist, length

def route_neighbors_and_counts(routes):
    neighbors = defaultdict(set)
    route_counts = defaultdict(int)
    for route in routes:
        for stop in set(route["stops"]):
            route_counts[stop] += 1
        for a, b in zip(route["stops"], route["stops"][1:]):
            neighbors[a].add(b)
            neighbors[b].add(a)
    return neighbors, route_counts

def enrich_geocoded_segments(routes, hub):
    """
    Insert known, geocoded stops into long route edges when geography and another
    route both say the stop belongs on that segment.
    """
    neighbors, route_counts = route_neighbors_and_counts(routes)
    candidates = [s for s in hub if route_counts.get(s, 0) >= 2]
    added = 0
    for route in routes:
        stops = route["stops"]
        route_stops = set(stops)
        expanded = []
        for a, b in zip(stops, stops[1:]):
            expanded.append(a)
            if a not in hub or b not in hub:
                continue
            ax, ay = xy(a, hub)
            bx, by = xy(b, hub)
            length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            if length < GRAPH_INSERT_MIN_KM or length > GRAPH_INSERT_MAX_KM:
                continue
            threshold = min(0.36, max(0.18, length * 0.34))
            matches = []
            for stop in candidates:
                if stop in route_stops or stop in (a, b):
                    continue
                if stop not in neighbors[a] and stop not in neighbors[b]:
                    continue
                match = segment_match(a, b, stop, hub)
                if not match:
                    continue
                t, dist, _ = match
                if dist <= threshold:
                    matches.append((t, dist, stop))
            chosen = []
            for t, dist, stop in sorted(matches):
                if all(abs(t - prev_t) > 0.08 for prev_t, _, _ in chosen):
                    chosen.append((t, dist, stop))
                if len(chosen) >= GRAPH_INSERT_MAX_PER_EDGE:
                    break
            for _, _, stop in chosen:
                if stop != expanded[-1]:
                    expanded.append(stop)
                    added += 1
        expanded.append(stops[-1])
        route["stops"] = expanded
    print(f"filled {added} geocoded segment stops")

def nearest_bus_stops(raw):
    raw = raw.replace("—", "/")
    out = []
    for part in re.split(r"\s*/\s*", raw):
        stop = canon(strip_notes(part))
        if stop and stop not in out:
            out.append(stop)
    return out

def parse_metro(path):
    routes, current, stops = [], None, []

    def flush():
        nonlocal stops, current
        if current and len(stops) >= 2:
            routes.append({
                "code": current,
                "kind": "metro",
                "origin": stops[0],
                "dest": stops[-1],
                "stops": stops,
            })
        stops = []

    try:
        rows = open(path, encoding="utf-8")
    except FileNotFoundError:
        return routes

    for raw in rows:
        line = raw.strip()
        m = re.match(r"([A-Z]+) LINE .*—", line)
        if m:
            flush()
            current = METRO_LINE_LABELS.get(m.group(1))
            continue
        if not current or "|" not in line or line.startswith("-"):
            continue
        station, nearest = [p.strip() for p in line.split("|", 1)]
        if not station or station.lower().startswith("metro station"):
            continue
        station_stop = canon(station)
        access_stops = nearest_bus_stops(nearest)
        for stop in [station_stop, *access_stops]:
            if stop and (not stops or stops[-1] != stop):
                stops.append(stop)
    flush()
    return routes

# ---------------------------------------------------------------- route loading
bus_routes = parse_busrepo_routes()
if bus_routes:
    print(f"using {len(bus_routes)} directional bus routes from Bus Repository")
else:
    raise SystemExit("Missing Bus Repository route sources. Expected raw_busrepo_routes1.js through raw_busrepo_routes4.js.")
print("using listed bus stops only; inferred bus stop insertion disabled")
apply_intermediate_hints(bus_routes)

metro_routes = parse_metro("Kolkata_Metro_Bus_Connections.txt")
print(f"parsed {len(metro_routes)} metro routes")

routes = []
stop_routes = defaultdict(set)
stops = []
route_set = []
route_adj = defaultdict(set)

def idx(r, s):
    return routes[r]["stops"].index(s)

def can_ride(r, a, b):
    if a not in route_set[r] or b not in route_set[r]:
        return False
    if routes[r].get("directional"):
        return idx(r, a) <= idx(r, b)
    return True

def ride_cost(r, a, b):
    if not can_ride(r, a, b):
        return 1e9
    i, j = idx(r, a), idx(r, b)
    return j - i if routes[r].get("directional") else abs(i - j)

def seg(r, a, b):
    """ordered stop list travelled on route r from a to b."""
    i, j = idx(r, a), idx(r, b)
    st = routes[r]["stops"]
    if routes[r].get("directional") and i > j:
        return []
    return st[i:j+1] if i <= j else st[j:i+1][::-1]

def shared(r1, r2):
    return route_set[r1] & route_set[r2]

def best_transfer(r1, r2, o, d):
    """pick the shared stop that minimises hops o->t on r1 + t->d on r2."""
    cands = shared(r1, r2)
    best, bc = None, 1e9
    for t in cands:
        if not can_ride(r1, o, t) or not can_ride(r2, t, d):
            continue
        c = ride_cost(r1, o, t) + ride_cost(r2, t, d)
        if c < bc:
            best, bc = t, c
    return best, bc

def uses_metro(*route_ids):
    return any(routes[r]["kind"] == "metro" for r in route_ids)

def metro_count(*route_ids):
    return sum(1 for r in route_ids if routes[r]["kind"] == "metro")

def route_scope_cost(r):
    if routes[r]["kind"] == "metro":
        return 0
    scope = routes[r].get("scope")
    if scope == "regional":
        return 3
    return 1

def find(o, d):
    o, d = canon(o), canon(d)
    out = {"origin": o, "dest": d, "direct": [], "one": [], "two": []}
    if o not in stop_routes or d not in stop_routes:
        out["error"] = "unknown stop"
        return out
    start, end = stop_routes[o], stop_routes[d]

    # ---- direct
    direct_routes = [r for r in start & end if can_ride(r, o, d)]
    for r in sorted(direct_routes, key=lambda r: (not uses_metro(r), route_scope_cost(r), ride_cost(r, o, d))):
        out["direct"].append({"legs": [{"route": display_code(routes[r]),
                                        "kind": routes[r]["kind"],
                                        "from": o, "to": d,
                                        "towards": routes[r].get("dest", ""),
                                        "stops": seg(r, o, d)}],
                              "cost": ride_cost(r, o, d)})
    # ---- one transfer
    seen = set()
    cands = []
    for r1 in start:
        for r2 in end & route_adj[r1]:
            if r1 == r2:
                continue
            t, cost = best_transfer(r1, r2, o, d)
            if t is None or t in (o, d):
                continue
            key = (r1, r2, t)
            if key in seen:
                continue
            seen.add(key)
            cands.append((not uses_metro(r1, r2), route_scope_cost(r1) + route_scope_cost(r2), -metro_count(r1, r2), cost, r1, r2, t))
    for _, _, _, cost, r1, r2, t in sorted(cands)[:10]:
        out["one"].append({"legs": [
            {"route": display_code(routes[r1]), "kind": routes[r1]["kind"],
             "from": o, "to": t, "towards": routes[r1].get("dest", ""), "stops": seg(r1, o, t)},
            {"route": display_code(routes[r2]), "kind": routes[r2]["kind"],
             "from": t, "to": d, "towards": routes[r2].get("dest", ""), "stops": seg(r2, t, d)}],
            "cost": cost})

    # ---- two transfers
    if len(out["direct"]) + len(out["one"]) < 4:
        seen2 = set()
        c2 = []
        for r1 in start:
            for r3 in end:
                if r3 == r1:
                    continue
                mids = route_adj[r1] & route_adj[r3]
                for r2 in mids:
                    if r2 in (r1, r3) or r2 in start or r2 in end:
                        continue
                    key = (r1, r2, r3)
                    if key in seen2:
                        continue
                    # choose t1 in r1&r2, t2 in r2&r3
                    s12, s23 = shared(r1, r2), shared(r2, r3)
                    bt, bcost = None, 1e9
                    for a in s12:
                        for b in s23:
                            if len({o, a, b, d}) < 4:
                                continue
                            if not can_ride(r1, o, a) or not can_ride(r2, a, b) or not can_ride(r3, b, d):
                                continue
                            cc = ride_cost(r1, o, a) + ride_cost(r2, a, b) + ride_cost(r3, b, d)
                            if cc < bcost:
                                bt, bcost = (a, b), cc
                    if bt is None:
                        continue
                    seen2.add(key)
                    c2.append((not uses_metro(r1, r2, r3), route_scope_cost(r1) + route_scope_cost(r2) + route_scope_cost(r3), -metro_count(r1, r2, r3), bcost, r1, r2, r3, bt[0], bt[1]))
        for _, _, _, cost, r1, r2, r3, a, b in sorted(c2)[:6]:
            out["two"].append({"legs": [
                {"route": display_code(routes[r1]), "kind": routes[r1]["kind"],
                 "from": o, "to": a, "towards": routes[r1].get("dest", ""), "stops": seg(r1, o, a)},
                {"route": display_code(routes[r2]), "kind": routes[r2]["kind"],
                 "from": a, "to": b, "towards": routes[r2].get("dest", ""), "stops": seg(r2, a, b)},
                {"route": display_code(routes[r3]), "kind": routes[r3]["kind"],
                 "from": b, "to": d, "towards": routes[r3].get("dest", ""), "stops": seg(r3, b, d)}],
                "cost": cost})
    return out

# ---------------------------------------------------------------- hub coords
HUB = {
  "Exide":[22.5377,88.3317],
  "Acropolis Mall":[22.5145,88.3929],
  "Jadavpur University":[22.4998,88.3695],
  "Deshapriya Park":[22.5174,88.3526],
  "Sishu Mangal":[22.5245,88.3524],
  "Garcha Road":[22.5257,88.3633],
  "Ballygunge Phari":[22.5281,88.3661],
  "Gariahat":[22.5197,88.3652],
  "Tollygunge Metro":[22.4943,88.3454],
  "Hazra":[22.5238,88.3466],
 "Esplanade":[22.5645,88.3510],"Howrah Station":[22.5838,88.3426],"Sealdah":[22.5675,88.3700],
 "BBD Bag":[22.5697,88.3486],"Barabazar":[22.5760,88.3530],"Shyambazar":[22.5990,88.3740],
 "Hatibagan":[22.5945,88.3720],"Girish Park":[22.5870,88.3620],"MG Road":[22.5820,88.3570],
 "Maniktala":[22.5860,88.3870],"Ultadanga":[22.5910,88.3990],"Kankurgachi":[22.5800,88.3960],
 "Phoolbagan":[22.5760,88.3920],"Beleghata":[22.5640,88.4060],"Park Circus":[22.5390,88.3670],
 "Moulali":[22.5610,88.3680],"Rabindra Sadan":[22.5440,88.3470],"Maidan":[22.5530,88.3460],
 "Park Street":[22.5530,88.3520],"Exide":[22.5430,88.3520],"Hazra More":[22.5260,88.3450],
 "Kalighat":[22.5180,88.3430],"Rashbehari":[22.5140,88.3530],"Gariahat":[22.5170,88.3660],
 "Golpark":[22.5130,88.3650],"Dhakuria":[22.5040,88.3680],"Jodhpur Park":[22.5055,88.3635],
 "Jadavpur 8B":[22.4970,88.3710],
 "Jadavpur PS":[22.4960,88.3690],"Tollygunge":[22.5010,88.3460],"Tollygunge Phari":[22.5020,88.3500],
 "South City":[22.5017,88.3617],"Lords":[22.5020,88.3564],"Lake Gardens":[22.5053,88.3548],
 "Anwar Shah Road":[22.5020,88.3495],"Prince Anwar Shah Connector":[22.5018,88.3520],
 "Jogesh Chandra College":[22.5030,88.3495],
 "Behala Chowrasta":[22.4980,88.3110],"Behala 14 No":[22.5060,88.3170],"Taratala":[22.5160,88.3120],
 "Majherhat":[22.5230,88.3210],"Mominpore":[22.5310,88.3270],"Ekbalpur":[22.5350,88.3280],
 "Kidderpore":[22.5380,88.3320],"Hastings":[22.5470,88.3340],"Fort William":[22.5540,88.3410],
 "New Alipore":[22.5040,88.3320],"Alipore Zoo":[22.5360,88.3320],"Chetla":[22.5170,88.3370],
 "Garia Metro":[22.4680,88.3970],"Naktala":[22.4760,88.3760],"Bansdroni":[22.4800,88.3650],
 "Netaji Nagar":[22.4830,88.3620],"Baghajatin":[22.4790,88.3870],"Patuli":[22.4720,88.3940],
 "Mukundapur":[22.4980,88.3990],"Ruby":[22.5130,88.4010],"Science City":[22.5400,88.3950],
 "Topsia More":[22.5390,88.3890],"Chingrighata":[22.5780,88.4150],"Saltlake Stadium":[22.5700,88.4050],
 "Karunamoyee":[22.5780,88.4170],"Sector V":[22.5760,88.4320],"College More":[22.5770,88.4290],
 "Newtown":[22.5810,88.4640],"Airport Gate 1":[22.6470,88.4410],"Kaikhali":[22.6320,88.4370],"Dumdum":[22.6420,88.4310],
 "Nager Bazar":[22.6300,88.4200],"Lake Town":[22.6080,88.4080],"Baguiati":[22.6130,88.4310],
 "Kestopur":[22.6010,88.4280],"Dumdum Park":[22.6090,88.4140],"Belgachia":[22.6010,88.3850],
 "RG Kar":[22.6060,88.3770],"Sinthi":[22.6230,88.3870],"Dunlop":[22.6440,88.3760],
 "Dakshineswar":[22.6550,88.3570],"Bonhooghly":[22.6360,88.3820],"Kamarhati":[22.6720,88.3760],
 "Sodepur":[22.7000,88.3870],"Barasat":[22.7240,88.4810],"Madhyamgram":[22.6970,88.4500],
 "Howrah Maidan":[22.5890,88.3340],"Bagbazar":[22.6010,88.3650],"Cossipore":[22.6150,88.3680],
 "Ballygunge Station":[22.5290,88.3650],"Kasba":[22.5160,88.3870],"Anandapur":[22.5090,88.4030],
 "Thakurpukur":[22.4670,88.3050],"Sakher Bazar":[22.4860,88.3090],"Diamond Plaza":[22.6280,88.4150],
 "Bangur Avenue":[22.6160,88.4060],"Central":[22.5730,88.3540],"Chandni Chowk":[22.5670,88.3520],
 "College Street":[22.5750,88.3640],"Wellington":[22.5630,88.3590],"Ramgarh":[22.4830,88.3760],
 "Rajabazar":[22.5790,88.3760],"Khanna Cinema":[22.5950,88.3830],"Patipukur":[22.6150,88.3960],
}

# ---------------------------------------------------------------- graph
routes = bus_routes + metro_routes
stop_routes, stops, route_set, route_adj = route_graph_parts(routes)
print(f"{len(stops)} unique stops after normalisation")

# ---------------------------------------------------------------- export
def export_route(route):
    out = {"code": display_code(route), "kind": route["kind"], "stops": route["stops"]}
    out["scope"] = route.get("scope") or ("metro" if route["kind"] == "metro" else "local")
    if route.get("directional"):
        out["directional"] = True
        out["towards"] = route["dest"]
    return out

data = {
    "routes": [export_route(r) for r in routes],
    "stops": [{"name": s, "routes": len(stop_routes[s]),
               "lat": HUB.get(s, [None, None])[0], "lng": HUB.get(s, [None, None])[1]}
              for s in sorted(stops, key=lambda s: -len(stop_routes[s]))],
    "aliases": export_search_aliases(stops),
}
json.dump(data, open("busdata.json", "w"), ensure_ascii=False)
print(f"exported busdata.json  ({len(data['routes'])} routes, {len(data['stops'])} stops, "
      f"{sum(1 for s in stops if s in HUB)} geocoded, {len(data['aliases'])} aliases)")

try:
    html = open("kolkata-bus-router.html", encoding="utf-8").read()
    embedded = "const DATA = " + json.dumps(data, ensure_ascii=False) + ";"
    html, replaced = re.subn(
        r"const DATA = .*?;\n\n/\* ===================== graph construction ===================== \*/",
        embedded + "\n\n/* ===================== graph construction ===================== */",
        html,
        count=1,
        flags=re.S,
    )
    if replaced:
        for page in ("kolkata-bus-router.html", "kolkata-travel-router.html", "index.html"):
            open(page, "w", encoding="utf-8").write(html)
        print("embedded route data in kolkata-bus-router.html and travel aliases")
    else:
        print("warning: could not find embedded DATA block to refresh")
except FileNotFoundError:
    pass

# ---------------------------------------------------------------- smoke tests
for o, d in [("Garia Metro", "Howrah Station"), ("Behala Chowrasta", "Salt Lake"),
             ("Airport", "Esplanade"), ("Thakurpukur", "Sealdah"),
             ("Jadavpur", "Shyambazar")]:
    res = find(o, d)
    print(f"\n{o} -> {d}   [{res.get('origin')} -> {res.get('dest')}]")
    if res.get("error"):
        print("   ", res["error"]); continue
    print(f"   direct: {len(res['direct'])}   1-change: {len(res['one'])}   2-change: {len(res['two'])}")
    for j in (res["direct"][:1] or res["one"][:1]):
        print("    e.g.", " -> ".join(f"[{l['route']}] {l['from']}->{l['to']}" for l in j["legs"]))
