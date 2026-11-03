"""Vergleicht zwei unabhängige Transkriptionsläufe und schreibt die Abweichungen samt Prüfseite.

    python -P abgleich.py <pilot-ordner> <manifest.jsonl> <lauf-a> <lauf-b> <bilder-url> <pruefseite.html>

Einheit des Vergleichs ist eine Tabellenzelle, ein Feld oder eine Textzeile. Stimmen zwei Läufe
überein, heißt das nicht, dass sie richtig liegen, nur dass hier niemand nachsehen muss.

Die Prüfseite enthält eine geschichtete Stichprobe, nicht alle Abweichungen: Der Pilot soll
Fehlerquoten messen, nicht jeden Fehler beheben.
"""
import difflib
import hashlib
import json
import os
import random
import re
import sys

ZU_PRUEFEN = ("wert_beide_sicher", "wert_einer_unsicher", "fehlt")
ARTEN = ("identisch", "nur_leerzeichen", "schreibmaschine", "nur_markierung", "strich_gegen_leer", "anderswo", "kopf") + ZU_PRUEFEN
BLOCKTYPEN = ("tabelle", "felder", "text", "vordruck", "stempel", "vermerk")
MARKE = re.compile(r"\[\?[^\]]*\]|\[\.\.\.\]|\[-\?-\]")
QUOTEN = {"liste": 50, "karte": 20, "hand": 20, "bogen": 15, "fliesstext": 15}
STELLEN_STICHPROBE = 40


def normal(wert):
    if wert is None:
        return None
    wert = re.sub(r"\s+", " ", str(wert)).strip()
    return wert or None


def zeichen_normal(wert):
    """Gleicht Eigenheiten aus, die keine Lesung sind: Schreibmaschinen tippten o für 0 und l für 1."""
    wert = re.sub(r"(?<=\d)[oO]|[oO](?=\d)", "0", wert)
    wert = re.sub(r"(?<=\d)[lI]|[lI](?=\d)", "1", wert)
    wert = re.sub(r"[„“”″]", '"', wert)
    return re.sub(r"[–—−]", "-", wert)


def ohne_markierung(wert):
    wert = re.sub(r"\[\?([^\]]+)\]", r"\1", wert)
    wert = re.sub(r"\[\+(.*?)\+\]", r"\1", wert)
    return wert.replace("[?]", "").replace("[...]", "")


def flach(wert):
    return re.sub(r"\s+", "", zeichen_normal(ohne_markierung(wert))).casefold()


def art_der_abweichung(a, b, ort):
    if a == b:
        return "identisch"
    if "Spaltenkopf" in ort or ort.startswith("vordruck"):
        return "kopf"
    if a is None or b is None:
        wert = a if b is None else b
        return "strich_gegen_leer" if re.fullmatch(r"[-\"„“”–—−.\s]*", wert) else "fehlt"
    if a.replace(" ", "") == b.replace(" ", ""):
        return "nur_leerzeichen"
    if zeichen_normal(a).replace(" ", "") == zeichen_normal(b).replace(" ", ""):
        return "schreibmaschine"
    if flach(a) == flach(b):
        return "nur_markierung"
    return "wert_einer_unsicher" if MARKE.search(a) or MARKE.search(b) else "wert_beide_sicher"


def aehnlichkeit(a, b):
    return difflib.SequenceMatcher(None, a or "", b or "", autojunk=False).ratio()


def ausrichten(links, rechts, text=lambda x: x):
    """Paart zwei Folgen so, dass ähnliche Einträge zusammenkommen (Needleman-Wunsch)."""
    n, m = len(links), len(rechts)
    tl, tr = [text(x) for x in links], [text(x) for x in rechts]
    punkte = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            punkte[i][j] = max(punkte[i + 1][j + 1] + aehnlichkeit(tl[i], tr[j]) - 0.3, punkte[i + 1][j], punkte[i][j + 1])
    paare, i, j = [], 0, 0
    while i < n and j < m:
        if punkte[i][j] == punkte[i + 1][j + 1] + aehnlichkeit(tl[i], tr[j]) - 0.3:
            paare.append((links[i], rechts[j]))
            i, j = i + 1, j + 1
        elif punkte[i][j] == punkte[i + 1][j]:
            paare.append((links[i], None))
            i += 1
        else:
            paare.append((None, rechts[j]))
            j += 1
    paare += [(x, None) for x in links[i:]] + [(None, x) for x in rechts[j:]]
    return paare


def einheiten(a, b):
    """Liefert (Ort, Wert A, Wert B, Zeilenanfang) für jede Einheit der Seite."""
    for typ in BLOCKTYPEN:
        blocks_a = [x for x in a["blocks"] if x.get("typ") == typ]
        blocks_b = [x for x in b["blocks"] if x.get("typ") == typ]
        for nr in range(max(len(blocks_a), len(blocks_b))):
            ba = blocks_a[nr] if nr < len(blocks_a) else {}
            bb = blocks_b[nr] if nr < len(blocks_b) else {}
            if typ == "tabelle":
                yield from tabelle(nr, ba, bb)
            elif typ == "felder":
                yield from felder(nr, ba, bb)
            else:
                for k, (x, y) in enumerate(ausrichten(normal_zeilen(ba.get("text")), normal_zeilen(bb.get("text")))):
                    yield f"{typ} {nr + 1}, Zeile {k + 1}", x, y, None


def normal_zeilen(text):
    return [z for z in (normal(t) for t in (text or "").split("\n")) if z]


def tabelle(nr, a, b):
    zeilen = lambda block: [[normal(z) for z in zeile] for zeile in block.get("zeilen", [])]
    kopf = a.get("spalten") or b.get("spalten") or []
    paare = ausrichten(zeilen(a), zeilen(b), lambda zeile: " ".join(z for z in zeile if z))
    for k, (x, y) in enumerate(paare):
        x, y = x or [], y or []
        kontext = " ".join([z for z in (x or y) if z][:2])
        for s in range(max(len(x), len(y))):
            wa = x[s] if s < len(x) else None
            wb = y[s] if s < len(y) else None
            if wa is None and wb is None:
                continue
            spalte = normal(kopf[s]) if s < len(kopf) and kopf[s] else f"Spalte {s + 1}"
            yield f"Tabelle {nr + 1}, Zeile {k + 1}, {spalte}", wa, wb, kontext
    kopf_a = [normal(z) or "" for z in a.get("spalten", [])]
    kopf_b = [normal(z) or "" for z in b.get("spalten", [])]
    for s, (x, y) in enumerate(ausrichten(kopf_a, kopf_b)):
        yield f"Tabelle {nr + 1}, Spaltenkopf {s + 1}", x, y, None


def felder(nr, a, b):
    schluessel = lambda feld: re.sub(r"\W+", "", (feld.get("etikett") or "").casefold())
    paare = ausrichten(a.get("felder", []), b.get("felder", []), schluessel)
    for x, y in paare:
        name = normal((x or y).get("etikett")) or "ohne Etikett"
        yield f"Felder {nr + 1}, {name}", normal((x or {}).get("wert")), normal((y or {}).get("wert")), None


def lesbarer_ort(ort, kontext):
    teile = ort.split(", ")
    art = teile[0].split()[0]
    if art == "Tabelle":
        return f"Tabellenzeile „{ohne_markierung(kontext or '')}“, Spalte „{', '.join(teile[2:])}“"
    if art == "Felder":
        return f"Feld „{', '.join(teile[1:])}“"
    return {"vermerk": "Randvermerk", "stempel": "Stempel", "text": "Text", "vordruck": "Vordruck"}.get(art, ort)


def seitentext(wert):
    """Aller Inhalt einer Seite als ein String, um Werte an anderer Stelle wiederzufinden."""
    if isinstance(wert, str):
        return flach(wert)
    if isinstance(wert, list):
        return "|".join(seitentext(x) for x in wert)
    if isinstance(wert, dict):
        return "|".join(seitentext(v) for k, v in wert.items() if k not in ("typ", "schrift", "wo", "farbe", "spalten", "etikett"))
    return ""


def markierungen(wert):
    """Zählt unleserliche und unsichere Stellen im Text, unabhängig davon, ob sie in `stellen` stehen."""
    if isinstance(wert, str):
        return len(MARKE.findall(wert))
    if isinstance(wert, list):
        return sum(markierungen(x) for x in wert)
    if isinstance(wert, dict):
        return sum(markierungen(x) for x in wert.values())
    return 0


def gueltig(transkript, pfad):
    if not isinstance(transkript.get("blocks"), list):
        sys.exit(f"Kein Feld blocks: {pfad}")
    for block in transkript["blocks"]:
        if block.get("typ") not in BLOCKTYPEN:
            sys.exit(f"Unbekannter Block {block.get('typ')!r}: {pfad}")


def stichprobe_ziehen(seiten):
    zug = random.Random(7)
    faelle = {}
    for typ, anzahl in QUOTEN.items():
        kandidaten = [(s["bild"], x) for s in seiten if s["typ"] == typ for x in s["abweichungen"]]
        for bild, x in zug.sample(kandidaten, min(anzahl, len(kandidaten))):
            faelle.setdefault(bild, []).append(x)
    kandidaten = [
        (s["bild"], {"id": f"{s['bild']}-stelle-{lauf}-{n}", "art": "stelle", "wo": "Vom Modell als unsicher markierte Stelle",
                     "lesung": stelle.get("lesung"), "lage": {k: stelle[k] for k in "xybh"}})
        for s in seiten for lauf, stellen in zip("ab", s["stellen"]) for n, stelle in enumerate(stellen)
        if all(isinstance(stelle.get(k), (int, float)) for k in "xybh")
    ]
    for bild, x in zug.sample(kandidaten, min(STELLEN_STICHPROBE, len(kandidaten))):
        faelle.setdefault(bild, []).append(x)
    return faelle


def main():
    pilot, manifest, lauf_a, lauf_b, bilder_url, seite = sys.argv[1:7]
    with open(os.path.join(pilot, "auswahl.jsonl"), encoding="utf-8") as f:
        auswahl = [json.loads(zeile) for zeile in f]
    with open(manifest, encoding="utf-8") as f:
        masse = {z["sha256"]: z for z in map(json.loads, f)}
    seiten, typen = [], {}
    for z in auswahl:
        transkripte = []
        for lauf in (lauf_a, lauf_b):
            pfad = os.path.join(pilot, "laeufe", lauf, z["bild"] + ".json")
            with open(pfad, encoding="utf-8") as f:
                transkript = json.load(f)
            gueltig(transkript, pfad)
            transkripte.append(transkript)
        texte = [seitentext(t["blocks"]) for t in transkripte]
        zaehler = dict.fromkeys(ARTEN, 0)
        abweichungen = []
        for nummer, (ort, wa, wb, kontext) in enumerate(einheiten(*transkripte)):
            art = art_der_abweichung(wa, wb, ort)
            if art == "fehlt":
                wert, anderer = (wa, texte[1]) if wb is None else (wb, texte[0])
                # Kurze Werte wie „m“ oder „/“ kommen auf fast jeder Seite irgendwo vor und belegen nichts.
                if len(flach(wert)) >= 3 and flach(wert) in anderer:
                    art = "anderswo"
            zaehler[art] += 1
            if art in ZU_PRUEFEN:
                schluessel = f"{z['bild']}-{nummer}"
                abweichungen.append({
                    "id": schluessel, "ort": ort, "wo": lesbarer_ort(ort, kontext), "kontext": kontext, "a": wa, "b": wb, "art": art,
                    # Links und rechts werden gemischt, damit die Prüfung nicht einem Lauf vertraut.
                    "tausch": hashlib.sha256(schluessel.encode()).digest()[0] % 2 == 1,
                })
        gesamt = sum(zaehler.values())
        seiten.append({
            "bild": z["bild"], "datei": z["datei"], "typ": z["typ"], "auswahl": z["auswahl"], "einheiten": gesamt, **zaehler,
            "abweichungen": abweichungen, "stellen": [t.get("stellen", []) for t in transkripte],
            "markiert": [markierungen(t["blocks"]) for t in transkripte],
            "seitenform": [t.get("seitenform") for t in transkripte],
            "hinweise": [t.get("hinweise") for t in transkripte],
        })
        t = typen.setdefault(z["typ"], {"seiten": 0, "einheiten": 0, "markiert_a": 0, "markiert_b": 0, **dict.fromkeys(ARTEN, 0)})
        t["seiten"] += 1
        t["einheiten"] += gesamt
        t["markiert_a"] += seiten[-1]["markiert"][0]
        t["markiert_b"] += seiten[-1]["markiert"][1]
        for art in ARTEN:
            t[art] += zaehler[art]
    with open(os.path.join(pilot, "abgleich.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"laeufe": [lauf_a, lauf_b], "typen": typen, "seiten": seiten}, f, ensure_ascii=False, indent=1)
    for typ, t in sorted(typen.items()):
        inhalt = t["einheiten"] - t["kopf"]
        print(f"{typ:11} Seiten {t['seiten']:2} Einheiten {inhalt:5} | identisch {t['identisch']:5} Leerz. {t['nur_leerzeichen']:3} "
              f"Schreibm. {t['schreibmaschine']:3} Mark. {t['nur_markierung']:3} Strich {t['strich_gegen_leer']:4} anderswo {t['anderswo']:4} | "
              f"beide sicher {t['wert_beide_sicher']:4} einer unsicher {t['wert_einer_unsicher']:4} fehlt {t['fehlt']:4} | "
              f"markiert A {t['markiert_a']} B {t['markiert_b']}")
    faelle = stichprobe_ziehen(seiten)
    # Die Lage der Abweichungen kommt aus einem eigenen Durchgang, siehe pilot/lagen/.
    for bild, liste in faelle.items():
        pfad = os.path.join(pilot, "lagen", bild + ".json")
        if os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as f:
                lagen = json.load(f)
            for x in liste:
                if x["art"] != "stelle":
                    x["lage"] = lagen.get(x["id"])
    with open(os.path.join(pilot, "faelle.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(faelle, f, ensure_ascii=False, indent=1)
    daten = [
        {"bild": s["bild"], "datei": s["datei"], "typ": s["typ"], "w": masse[next(z["sha256"] for z in auswahl if z["bild"] == s["bild"])]["w"],
         "h": masse[next(z["sha256"] for z in auswahl if z["bild"] == s["bild"])]["h"], "faelle": faelle[s["bild"]]}
        for s in seiten if s["bild"] in faelle
    ]
    print("Prüfseite:", sum(len(s["faelle"]) for s in daten), "Fälle auf", len(daten), "Seiten")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pruefseite.html"), encoding="utf-8") as f:
        vorlage = f.read()
    einbetten = json.dumps({"bilder": bilder_url, "seiten": daten}, ensure_ascii=False).replace("</", "<\\/")
    with open(seite, "w", encoding="utf-8", newline="\n") as f:
        f.write(vorlage.replace("/*DATEN*/null", einbetten))


if __name__ == "__main__":
    main()
