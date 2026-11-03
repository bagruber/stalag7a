"""Entpackt die Zugangs-Zips nach originale/ und schreibt das Manifest: je Datei die Herkunft im
Zip, Größe, SHA-256 und was das Bild über seine Entstehung verrät. Dateinamen bleiben unverändert,
auch in macOS-Unicode (NFD), weil sie selbst Quellenangaben sind.

    python -P entpacken.py <archiv> <manifest.jsonl>

Ein zweiter Lauf prüft vorhandene Dateien nur gegen das Zip.
"""
import glob
import hashlib
import io
import json
import os
import pathlib
import re
import sys
import zipfile

from PIL import ExifTags, Image, ImageCms, UnidentifiedImageError

XMP_FELDER = ("xmp:CreatorTool", "exif:UserComment", "photoshop:Source", "dc:creator")
EXIF_FELDER = ("Software", "DateTime", "DateTimeOriginal", "Make", "Model", "Artist", "Copyright", "UserComment")


def eintrag_name(info):
    if info.flag_bits & 0x800:
        return info.filename
    return info.filename.encode("cp437").decode("utf-8")


def bild_angaben(pfad):
    try:
        with Image.open(pfad) as bild:
            angaben = {"format": bild.format, "w": bild.width, "h": bild.height, "modus": bild.mode}
            info = bild.info
            if "dpi" in info:
                angaben["dpi"] = [round(float(wert), 2) for wert in info["dpi"]]
            if "icc_profile" in info:
                profil = ImageCms.ImageCmsProfile(io.BytesIO(info["icc_profile"]))
                angaben["icc"] = ImageCms.getProfileDescription(profil).strip()
            texte = {k: v for k, v in info.items() if isinstance(v, str) and len(v) <= 200}
            if texte:
                angaben["text"] = texte
            xmp = info.get("XML:com.adobe.xmp") or info.get("xmp") or ""
            if isinstance(xmp, bytes):
                xmp = xmp.decode("utf-8", "replace")
            funde = {}
            for feld in XMP_FELDER:
                treffer = re.search(rf"<{feld}[^>]*>(.*?)</{feld}>", xmp, re.S)
                if treffer:
                    funde[feld] = re.sub(r"<[^>]+>", "", treffer.group(1)).strip()
            if funde:
                angaben["xmp"] = funde
            exif = bild.getexif()
            tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
            tags.update({ExifTags.TAGS.get(k, k): v for k, v in exif.get_ifd(0x8769).items()})
            gefunden = {}
            for feld in EXIF_FELDER:
                wert = tags.get(feld)
                if isinstance(wert, bytes):
                    wert = wert.decode("ascii", "replace").strip("\x00 ")
                if wert:
                    gefunden[feld] = str(wert)
            if gefunden:
                angaben["exif"] = gefunden
            return angaben
    except UnidentifiedImageError:
        return {}


def main():
    archiv, manifest = sys.argv[1:3]
    ziel = pathlib.Path(archiv) / "originale"
    zeilen = []
    for zip_pfad in sorted(glob.glob(os.path.join(archiv, "*.zip"))):
        with zipfile.ZipFile(zip_pfad) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                name = eintrag_name(info)
                teile = pathlib.PurePosixPath(name).parts
                if ".." in teile or pathlib.PurePosixPath(name).is_absolute():
                    sys.exit(f"Unsicherer Pfad im Zip: {name!r}")
                pfad = ziel.joinpath(*teile)
                pfad.parent.mkdir(parents=True, exist_ok=True)
                # Beim Lesen prüft zipfile die CRC und bricht bei Abweichung ab.
                sha = hashlib.sha256()
                vorhanden = pfad.exists()
                with z.open(info) as quelle, (open(os.devnull, "wb") if vorhanden else open(pfad, "wb")) as senke:
                    for block in iter(lambda: quelle.read(1 << 20), b""):
                        sha.update(block)
                        senke.write(block)
                sha256 = sha.hexdigest()
                if vorhanden:
                    with open(pfad, "rb") as f:
                        if hashlib.file_digest(f, "sha256").hexdigest() != sha256:
                            sys.exit(f"Vorhandene Datei weicht vom Zip ab: {pfad}")
                zeile = {
                    "pfad": "/".join(teile),
                    "zip": os.path.basename(zip_pfad),
                    "bytes": info.file_size,
                    "sha256": sha256,
                }
                zeile.update(bild_angaben(pfad))
                zeilen.append(zeile)
    pfade = [zeile["pfad"] for zeile in zeilen]
    if len(set(pfade)) != len(pfade):
        sys.exit("Doppelte Pfade über die Zips hinweg")
    zeilen.sort(key=lambda zeile: zeile["pfad"])
    with open(manifest, "w", encoding="utf-8", newline="\n") as f:
        for zeile in zeilen:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    print(len(zeilen), "Dateien")


if __name__ == "__main__":
    main()
