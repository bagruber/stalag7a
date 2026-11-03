"""Wertet die Prüfentscheidungen aus: Wie oft liegt welcher Lauf richtig, je Dokumenttyp?

    python -P auswertung.py <pilot-ordner> <entscheidungen.json> <einordnung.json>

Geprüft wurde nur, wo die Läufe abweichen oder ein Lauf unsicher war. Wo beide dasselbe lesen, hat
niemand nachgesehen, die Fehlerzahlen sind deshalb Untergrenzen. Maßstab ist eine prüfende Person
am selben Bild, kein Befund am Original.

Die Entscheidungen bleiben unverändert. Was Freitexte bedeuten, die keine reine Lesung sind, steht
mit Begründung getrennt in der Einordnung.
"""
import collections
import functools
import json
import math
import os
import re
import sys

# python -P nimmt den Skriptordner nicht in den Suchpfad auf.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from abgleich import MARKE, ZU_PRUEFEN, zeichen_normal

LUECKE = "\0"
TYPEN = ("liste", "karte", "hand", "bogen", "fliesstext")
URTEILE = ("richtig", "falsch_still", "falsch_markiert", "offen", "nichts")


def muster(wert):
    """Macht eine Lesung vergleichbar. Unlesbares und `_` werden zur Lücke beliebiger Länge."""
    wert = re.sub(r"\[\?\]|\[\.\.\.\]|\[-\?-\]|\[geschwärzt\]|_+", LUECKE, wert)
    wert = re.sub(r"\[\?([^\]]+)\]", r"\1", wert)
    wert = re.sub(r"\[\+(.*?)\+\]", r"\1", wert)
    wert = re.sub(r"\[-(.*?)-\]", r"\1", wert)
    return re.sub(r"\s+", "", zeichen_normal(wert)).casefold().strip(".,;:")


def vertraeglich(a, b):
    """Können zwei Lesungen mit Lücken denselben Text meinen?"""
    @functools.lru_cache(maxsize=None)
    def passt(i, j):
        if i == len(a) and j == len(b):
            return True
        if i < len(a) and a[i] == LUECKE:
            return passt(i + 1, j) or (j < len(b) and passt(i, j + 1))
        if j < len(b) and b[j] == LUECKE:
            return passt(i, j + 1) or (i < len(a) and passt(i + 1, j))
        return i < len(a) and j < len(b) and a[i] == b[j] and passt(i + 1, j + 1)
    return passt(0, 0)


def urteil(wert, bezug):
    """Ein leerer Bezug heißt: Laut Prüfung steht hier nichts, wer etwas liest, liegt falsch."""
    if wert is None:
        return "richtig" if bezug == "" else "nichts"
    m, b = muster(wert), muster(bezug)
    if not m.replace(LUECKE, ""):
        return "offen"
    if b.replace(LUECKE, "") and vertraeglich(m, b):
        return "richtig"
    return "falsch_markiert" if MARKE.search(wert) else "falsch_still"


def bezug_von(x, e, einordnung):
    """Die Lesung, an der gemessen wird, oder None, wenn der Fall keine Lesung ergibt."""
    if einordnung.get("kommentar"):
        return None
    if "lesung" in einordnung:
        return einordnung["lesung"]
    wahl = einordnung.get("wahl", e["wahl"])
    if wahl in ("a", "b"):
        return x[wahl] if x[wahl] is not None else ""
    if wahl in ("weder", "andere"):
        return e["text"]
    return x["lesung"] if wahl == "stimmt" else None


def wilson(treffer, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = treffer / n
    mitte = (p + z * z / (2 * n)) / (1 + z * z / n)
    rand = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(mitte - rand, 0.0), min(mitte + rand, 1.0)


def neu_typ():
    return {"faelle": 0, "unlesbar": 0, "verschieden": 0, "kommentar": 0, "geprueft": 0, "phantom": 0,
            "a": dict.fromkeys(URTEILE, 0), "b": dict.fromkeys(URTEILE, 0),
            "beide": 0, "nur_a": 0, "nur_b": 0, "keiner": 0}


def main():
    pilot, pfad_entscheidungen, pfad_einordnung = sys.argv[1:4]
    def lies(pfad):
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    faelle, abgleich = lies(os.path.join(pilot, "faelle.json")), lies(os.path.join(pilot, "abgleich.json"))
    entscheidungen, einordnung = lies(pfad_entscheidungen), lies(pfad_einordnung)
    typ_von = {s["bild"]: s["typ"] for s in abgleich["seiten"]}

    typen = {t: neu_typ() for t in TYPEN}
    stellen = {lauf: collections.Counter() for lauf in "ab"}
    marken = {lauf: collections.Counter() for lauf in "ab"}
    blind = collections.Counter()
    je_fall = {}
    for bild, liste in faelle.items():
        t = typen[typ_von[bild]]
        for x in liste:
            e, eo = entscheidungen[x["id"]], einordnung.get(x["id"], {})
            bezug = bezug_von(x, e, eo)
            if x["art"] == "stelle":
                lauf = x["id"].split("-stelle-")[1][0]
                stellen[lauf]["faelle"] += 1
                stellen[lauf]["ausschnitt_falsch"] += e["wahl"] == "ausschnitt_falsch"
                if eo.get("kommentar"):
                    stellen[lauf]["kommentar"] += 1
                elif bezug is None:
                    stellen[lauf]["unlesbar" if e["wahl"] == "unlesbar" else "ohne_lesung"] += 1
                else:
                    stellen[lauf][urteil(x["lesung"], bezug)] += 1
                je_fall[x["id"]] = {"typ": typ_von[bild], "art": "stelle", "wahl": e["wahl"],
                                    "urteil": None if bezug is None else urteil(x["lesung"], bezug)}
                continue
            t["faelle"] += 1
            if e["wahl"] in ("a", "b"):
                blind["links" if (e["wahl"] == "b") == x["tausch"] else "rechts"] += 1
            if eo.get("kommentar"):
                t["kommentar"] += 1
                je_fall[x["id"]] = {"typ": typ_von[bild], "art": x["art"], "wahl": e["wahl"], "urteil": "kommentar"}
                continue
            if bezug is None and "urteil" not in eo:
                t[e["wahl"]] += 1
                je_fall[x["id"]] = {"typ": typ_von[bild], "art": x["art"], "wahl": e["wahl"], "urteil": e["wahl"]}
                continue
            t["geprueft"] += 1
            t["phantom"] += bezug == ""
            if "urteil" in eo:
                ua, ub = eo["urteil"]["a"], eo["urteil"]["b"]
            else:
                ua, ub = urteil(x["a"], bezug), urteil(x["b"], bezug)
            t["a"][ua] += 1
            t["b"][ub] += 1
            t["beide" if ua == ub == "richtig" else "nur_a" if ua == "richtig" else "nur_b" if ub == "richtig" else "keiner"] += 1
            for lauf, wert, u in (("a", x["a"], ua), ("b", x["b"], ub)):
                if u in ("richtig", "falsch_still", "falsch_markiert") and wert is not None:
                    marken[lauf][("markiert" if MARKE.search(wert) else "unmarkiert", "richtig" if u == "richtig" else "falsch")] += 1
            je_fall[x["id"]] = {"typ": typ_von[bild], "art": x["art"], "wahl": e["wahl"], "a": ua, "b": ub}

    hochrechnung = {}
    for name, t in typen.items():
        g = abgleich["typen"][name]
        einheiten = g["einheiten"] - g["kopf"]
        abweichend = sum(g[a] for a in ZU_PRUEFEN)
        anteil = abweichend / einheiten
        hochrechnung[name] = {"einheiten": einheiten, "abweichend": abweichend}
        for lauf in "ab":
            for art in ("falsch_still", "nichts"):
                n, k = t["geprueft"], t[lauf][art]
                unten, oben = wilson(k, n)
                hochrechnung[name][f"{lauf}_{art}_je_100"] = [round(100 * anteil * k / n, 1) if n else 0, round(100 * anteil * unten, 1), round(100 * anteil * oben, 1)]

    with open(os.path.join(pilot, "auswertung.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"typen": typen, "hochrechnung": hochrechnung, "stellen": {k: dict(v) for k, v in stellen.items()},
                   "marken": {k: {" ".join(s): w for s, w in v.items()} for k, v in marken.items()},
                   "blindung": dict(blind), "faelle": je_fall}, f, ensure_ascii=False, indent=1)

    print("Abweichungen je Typ: Fälle | geprüft | nicht lesbar | verschiedene Stellen | Kommentar | laut Prüfung leer")
    for name, t in typen.items():
        print(f"  {name:11}{t['faelle']:4}{t['geprueft']:5}{t['unlesbar']:5}{t['verschieden']:5}{t['kommentar']:5}{t['phantom']:5}")
    print("\nUrteile je Lauf (geprüfte Fälle): richtig | falsch still | falsch markiert | offen markiert | nichts gelesen")
    for name, t in typen.items():
        for lauf in "ab":
            print(f"  {name:11}{lauf.upper()} " + "".join(f"{t[lauf][u]:5}" for u in URTEILE) + f"   richtig {100 * t[lauf]['richtig'] / max(t['geprueft'], 1):3.0f} %")
    print("\nWer liegt richtig: beide | nur A | nur B | keiner")
    for name, t in typen.items():
        print(f"  {name:11}{t['beide']:5}{t['nur_a']:5}{t['nur_b']:5}{t['keiner']:5}")
    print("\nHochrechnung je 100 Einheiten, nur abweichende Einheiten (Wert [95-%-Bereich]): stille Fehler A | stille Fehler B | nichts A | nichts B")
    for name, h in hochrechnung.items():
        print(f"  {name:11}Einh. {h['einheiten']:5} abw. {h['abweichend']:4} | " + " | ".join(f"{h[k][0]:4} [{h[k][1]}-{h[k][2]}]" for k in ("a_falsch_still_je_100", "b_falsch_still_je_100", "a_nichts_je_100", "b_nichts_je_100")))
    print("\nTaugt die Markierung? (Werte, die etwas lesen)")
    for lauf in "ab":
        m = marken[lauf]
        print(f"  {lauf.upper()} markiert: {m[('markiert', 'richtig')]} richtig, {m[('markiert', 'falsch')]} falsch | unmarkiert: {m[('unmarkiert', 'richtig')]} richtig, {m[('unmarkiert', 'falsch')]} falsch")
    print("\nUnsichere Stellen je Lauf:")
    for lauf in "ab":
        print(f"  {lauf.upper()} {dict(stellen[lauf])}")
    print("\nBlindung, gewählte Seite:", dict(blind))


if __name__ == "__main__":
    main()
