"""Pilot der Transkription: Stichprobe ziehen und ausgewählte Bilder bereitstellen.

    python -P pilot.py stichprobe <manifest.jsonl> <originale> <ausgabe> [anzahl] [seed]
    python -P pilot.py bereitstellen <auswahl.jsonl> <originale> <ausgabe>

Die Bilder bekommen beim Bereitstellen einen neutralen Namen (erste 12 Zeichen des SHA-256), weil
der Dateiname Namen und Orte vorgibt und die Lesung sonst nicht mehr nur aus dem Bild käme.
"""
import json
import os
import random
import shutil
import sys

from PIL import Image, ImageDraw, ImageOps

SPALTEN, ZEILEN, BREITE = 5, 4, 300


def lesen(pfad):
    with open(pfad, encoding="utf-8") as f:
        return [json.loads(zeile) for zeile in f]


def stichprobe(manifest, originale, ausgabe, anzahl=120, seed=7):
    os.makedirs(ausgabe, exist_ok=True)
    eindeutig = {z["sha256"]: z for z in lesen(manifest) if z.get("w")}
    zug = random.Random(seed).sample(sorted(eindeutig.values(), key=lambda z: z["sha256"]), anzahl)
    with open(os.path.join(ausgabe, "stichprobe.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for nr, z in enumerate(zug):
            f.write(json.dumps({"nr": nr, "pfad": z["pfad"], "sha256": z["sha256"], "w": z["w"], "h": z["h"]}, ensure_ascii=False) + "\n")
    hoehe = BREITE + 24
    for start in range(0, anzahl, SPALTEN * ZEILEN):
        bogen = Image.new("RGB", (SPALTEN * BREITE, ZEILEN * hoehe), "white")
        zeichnen = ImageDraw.Draw(bogen)
        for i, z in enumerate(zug[start:start + SPALTEN * ZEILEN]):
            x, y = i % SPALTEN * BREITE, i // SPALTEN * hoehe
            with Image.open(os.path.join(originale, *z["pfad"].split("/"))) as bild:
                klein = ImageOps.contain(bild.convert("RGB"), (BREITE - 8, BREITE - 8))
            bogen.paste(klein, (x + 4, y + 22))
            zeichnen.text((x + 6, y + 6), str(start + i), fill="black")
        bogen.save(os.path.join(ausgabe, f"bogen-{start // (SPALTEN * ZEILEN):02d}.jpg"), quality=80)


def bereitstellen(auswahl, originale, ausgabe):
    os.makedirs(ausgabe, exist_ok=True)
    for z in lesen(auswahl):
        shutil.copy2(os.path.join(originale, *z["pfad"].split("/")), os.path.join(ausgabe, z["datei"]))


if __name__ == "__main__":
    befehl, *rest = sys.argv[1:]
    if befehl == "stichprobe":
        stichprobe(*rest[:3], *map(int, rest[3:]))
    elif befehl == "bereitstellen":
        bereitstellen(*rest)
    else:
        sys.exit(__doc__)
