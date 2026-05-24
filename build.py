#!/usr/bin/env python3
"""
Kolkata Bus Router — data pipeline
----------------------------------
Reads raw route dumps (format:  CODE: Origin to Destination | stop, stop, ...),
normalises the inconsistent stop names, builds a routing graph, and exports a
single JSON that the web app consumes.

The normalisation layer is the important part: the source data spells the same
place many ways (Rashbehari/Rashbihari, Kidderpore/Khiderpur, Barabazar/
Burrabazar, Dum Dum/Dumdum, ...). Everything below funnels through canon().
"""
import json, re, itertools
from collections import defaultdict, deque

# ---------------------------------------------------------------- normalisation
# 1) token-level spelling fixes applied to the lowercased, punctuation-stripped key
SPELLING = {
    "rashbihari": "rashbehari", "rasbehari": "rashbehari",
    "khiderpur": "kidderpore", "khidirpur": "kidderpore", "kidderpur": "kidderpore",
    "burrabazar": "barabazar", "burra bazar": "barabazar",
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
    "sova bajar": "sovabazar", "sova bazar": "sovabazar",
    "sobhabazar": "sovabazar", "shobhabazar": "sovabazar",
    "haldiram": "haldirams",
    "anwarsah road": "anwar shah road", "anwar sha connector": "prince anwar shah connector",
    # --- added after duplicate audit (pure spelling variants) ---
    "dakshineshwar": "dakshineswar",
    "chadni": "chandni",
    "nagerbazar": "nager bazar",
    "sakherbazar": "sakher bazar",
    "mallickbazar": "mallick bazar",
    "shishu": "sishu",
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
    "lake town": "laketown",
    "bally halt": "ballyhalt",
    "bally ghat": "ballyghat",
    "sukanta nagar": "sukantanagar",
    "rabindrasadan": "rabindra sadan",
    "beckbagan": "beck bagan",
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
    "c a island": "ca island",
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
    "chandni": "chandni chowk", "chandni market": "chandni chowk",
    "shyambazar 5 point": "shyambazar",
    "rg kar hospital": "rg kar", "r g kar": "rg kar",
    "ruby hospital": "ruby",
    # shorthand -> full name (keeps the place distinct, just spelled in full)
    "8b": "jadavpur 8b",
    "hudco": "ultadanga hudco",
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
# words that mark a junction -- "X More" is the same point as "X"
JUNCTION = re.compile(r"\s+(more|crossing|xing)$")

def canon(name):
    """messy stop string -> canonical Title-Case display name."""
    s = name.lower().strip()
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
    out = []
    for w in s.split():
        if w in ("bbd", "rg", "mg", "ps", "pts", "bnr", "sdf", "cit",
                 "gpo", "hmg", "nshm", "dlf", "sm", "wbtc", "id", "ils",
                 "kbkc", "amri", "gst", "ca", "fd", "gd", "bt", "apc",
                 "rn", "pg", "pnb", "em", "bk", "be"):
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
def parse(path, kind):
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
        origin = re.sub(r"\(.*?\)", "", origin).strip()       # drop parentheticals
        dest   = re.sub(r"\(.*?\)", "", dest).strip()
        parts = [origin] + re.split(r"[,/]", via) + [dest]    # split on , and /
        seq = []
        for p in parts:
            c = canon(p)
            if c and (not seq or seq[-1] != c):               # drop consecutive dupes
                seq.append(c)
        if len(seq) >= 2:
            routes.append({"code": code, "kind": kind,
                            "origin": seq[0], "dest": seq[-1], "stops": seq})
    if skipped:
        print(f"  ({skipped} non-route lines skipped in {path})")
    return routes

routes = parse("raw_private.txt", "private") + parse("raw_govt.txt", "government")
print(f"parsed {len(routes)} routes")

PRIVATE_MINI_CODE = re.compile(r"^(S-\d|M-\d|MM\d|MN\d)", re.I)
MINI_PUBLIC_ORIGINS = {
    "s-106": "Santoshpur",
    "santoshpur mini": "Santoshpur",
}

def display_code(route):
    """Use public-facing names for private mini buses instead of fleet-style codes."""
    code = route["code"].strip()
    key = code.lower()
    is_mini = route["kind"] == "private" and (
        PRIVATE_MINI_CODE.match(code) or key.endswith(" mini")
    )
    if not is_mini:
        return code
    origin = MINI_PUBLIC_ORIGINS.get(key, route["origin"])
    return f"{origin} {route['dest']} Mini"

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

# ---------------------------------------------------------------- graph
enrich_short_gaps(routes)

stop_routes = defaultdict(set)          # stop -> set(route index)
for i, r in enumerate(routes):
    for s in set(r["stops"]):
        stop_routes[s].add(i)
stops = sorted(stop_routes)
print(f"{len(stops)} unique stops after normalisation")

route_set = [set(r["stops"]) for r in routes]
# route adjacency: two routes are linked if they share >=1 stop
route_adj = defaultdict(set)
by_stop = list(stop_routes.values())
for rs in by_stop:
    for a, b in itertools.combinations(rs, 2):
        route_adj[a].add(b); route_adj[b].add(a)

def idx(r, s):
    return routes[r]["stops"].index(s)

def seg(r, a, b):
    """ordered stop list travelled on route r from a to b (routes are bidirectional)."""
    i, j = idx(r, a), idx(r, b)
    st = routes[r]["stops"]
    return st[i:j+1] if i <= j else st[j:i+1][::-1]

def shared(r1, r2):
    return route_set[r1] & route_set[r2]

def best_transfer(r1, r2, o, d):
    """pick the shared stop that minimises hops o->t on r1 + t->d on r2."""
    cands = shared(r1, r2)
    best, bc = None, 1e9
    for t in cands:
        c = abs(idx(r1, o) - idx(r1, t)) + abs(idx(r2, t) - idx(r2, d))
        if c < bc:
            best, bc = t, c
    return best, bc

def find(o, d):
    o, d = canon(o), canon(d)
    out = {"origin": o, "dest": d, "direct": [], "one": [], "two": []}
    if o not in stop_routes or d not in stop_routes:
        out["error"] = "unknown stop"
        return out
    start, end = stop_routes[o], stop_routes[d]

    # ---- direct
    for r in sorted(start & end, key=lambda r: abs(idx(r, o) - idx(r, d))):
        out["direct"].append({"legs": [{"route": display_code(routes[r]),
                                        "kind": routes[r]["kind"],
                                        "from": o, "to": d,
                                        "stops": seg(r, o, d)}]})
    # ---- one transfer
    seen = set()
    cands = []
    for r1 in start:
        for r2 in end & route_adj[r1]:
            if r1 == r2:
                continue
            key = tuple(sorted((routes[r1]["code"], routes[r2]["code"])))
            if key in seen:
                continue
            t, cost = best_transfer(r1, r2, o, d)
            if t is None or t in (o, d):
                continue
            seen.add(key)
            cands.append((cost, r1, r2, t))
    for cost, r1, r2, t in sorted(cands)[:10]:
        out["one"].append({"legs": [
            {"route": display_code(routes[r1]), "kind": routes[r1]["kind"],
             "from": o, "to": t, "stops": seg(r1, o, t)},
            {"route": display_code(routes[r2]), "kind": routes[r2]["kind"],
             "from": t, "to": d, "stops": seg(r2, t, d)}]})

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
                    key = (routes[r1]["code"], routes[r2]["code"], routes[r3]["code"])
                    if key in seen2:
                        continue
                    # choose t1 in r1&r2, t2 in r2&r3
                    s12, s23 = shared(r1, r2), shared(r2, r3)
                    bt, bcost = None, 1e9
                    for a in s12:
                        for b in s23:
                            if len({o, a, b, d}) < 4:
                                continue
                            cc = (abs(idx(r1, o) - idx(r1, a)) +
                                  abs(idx(r2, a) - idx(r2, b)) +
                                  abs(idx(r3, b) - idx(r3, d)))
                            if cc < bcost:
                                bt, bcost = (a, b), cc
                    if bt is None:
                        continue
                    seen2.add(key)
                    c2.append((bcost, r1, r2, r3, bt[0], bt[1]))
        for cost, r1, r2, r3, a, b in sorted(c2)[:6]:
            out["two"].append({"legs": [
                {"route": display_code(routes[r1]), "kind": routes[r1]["kind"],
                 "from": o, "to": a, "stops": seg(r1, o, a)},
                {"route": display_code(routes[r2]), "kind": routes[r2]["kind"],
                 "from": a, "to": b, "stops": seg(r2, a, b)},
                {"route": display_code(routes[r3]), "kind": routes[r3]["kind"],
                 "from": b, "to": d, "stops": seg(r3, b, d)}]})
    return out

# ---------------------------------------------------------------- hub coords
HUB = {
 "Esplanade":[22.5645,88.3510],"Howrah Station":[22.5838,88.3426],"Sealdah":[22.5675,88.3700],
 "BBD Bag":[22.5697,88.3486],"Barabazar":[22.5760,88.3530],"Shyambazar":[22.5990,88.3740],
 "Hatibagan":[22.5945,88.3720],"Girish Park":[22.5870,88.3620],"MG Road":[22.5820,88.3570],
 "Maniktala":[22.5860,88.3870],"Ultadanga":[22.5910,88.3990],"Kankurgachi":[22.5800,88.3960],
 "Phoolbagan":[22.5760,88.3920],"Beleghata":[22.5640,88.4060],"Park Circus":[22.5390,88.3670],
 "Moulali":[22.5610,88.3680],"Rabindra Sadan":[22.5440,88.3470],"Maidan":[22.5530,88.3460],
 "Park Street":[22.5530,88.3520],"Exide":[22.5430,88.3520],"Hazra More":[22.5260,88.3450],
 "Kalighat":[22.5180,88.3430],"Rashbehari":[22.5140,88.3530],"Gariahat":[22.5170,88.3660],
 "Golpark":[22.5130,88.3650],"Dhakuria":[22.5040,88.3680],"Jadavpur 8B":[22.4970,88.3710],
 "Jadavpur PS":[22.4960,88.3690],"Tollygunge":[22.5010,88.3460],"Tollygunge Phari":[22.5020,88.3500],
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

# ---------------------------------------------------------------- export
data = {
    "routes": [{"code": display_code(r), "kind": r["kind"], "stops": r["stops"]} for r in routes],
    "stops": [{"name": s, "routes": len(stop_routes[s]),
               "lat": HUB.get(s, [None, None])[0], "lng": HUB.get(s, [None, None])[1]}
              for s in sorted(stops, key=lambda s: -len(stop_routes[s]))],
}
json.dump(data, open("busdata.json", "w"), ensure_ascii=False)
print(f"exported busdata.json  ({len(data['routes'])} routes, {len(data['stops'])} stops, "
      f"{sum(1 for s in stops if s in HUB)} geocoded)")

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
