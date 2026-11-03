# stalag7a

Datenstruktur und Werkzeuge zum Stalag VII A in Moosburg a.d. Isar und seinen Arbeitskommandos,
perspektivisch auch zur Internierung nach Kriegsende und zu späteren Nachnutzungen. Jede Angabe soll
bis zum Dokument zurückführen, aus dem sie stammt.

Der Bestand wird zuerst wertfrei digitalisiert. Abgleich und Zusammenführung kommen danach und
überschreiben nichts von dem, was darunter liegt.

## Was wo liegt

| Ort | Inhalt | Sichtbarkeit |
|---|---|---|
| dieses Repo | Modell, Werkzeuge, Regeln, Quellenliste, später erzeugte Veröffentlichungen | öffentlich |
| `bagruber/stalag7a-daten` | Manifest, Transkripte, Aussagen, Zuordnungen | privat |
| `K:\Projekte\Moosburg\stalag7a\` | Zugangs-Zips und Scans | lokal |

Getrennt, weil Git nichts vergisst: Ein privates Repo, das später geöffnet wird, veröffentlicht jede
frühere Version mit. Hier landet deshalb nichts mit Personennamen, auch keine Dateinamen des Bestands,
denn die enthalten Namen.

## Modell

```
4 Entität     Person, Ort, Institution, Arbeitskommando, Betrieb
                ↑ Zuordnung: wer, wann, warum, wie sicher, widerrufbar
3 Aussage     „Diese Zeile sagt: Aufenthalt 1.2.1943 bis 3.4.1944“
                ↑ Regel der Normalisierung
2 Transkript  Zeile 1, Spalte 7: „1.2.43 / 3. 4.44“
                ↑ Werkzeug, Bearbeiter, Bildausschnitt
1 Bestand     Zugang → Datei (SHA-256) → Dokument → Seite
```

Jede Ebene verweist nur auf die darunter. Ein falscher Abgleich kostet eine zurückgenommene Zuordnung,
das Transkript bleibt unberührt. Widersprüche bleiben als zwei Aussagen stehen.

- **Datei und Dokument sind verschieden:** Ein Dokument kann als mehrere Dateien vorliegen (Vorder- und
  Rückseite, Dublette, spätere bessere Fassung aus einem anderen Archiv).
- **Person** trägt selbst keinen Status. Kriegsgefangener, Zivilarbeiter oder Internierter sind
  zeitlich begrenzte Aussagen darüber.
- **Ort** ist Geografie, mit historischer Gemeinde und Landkreis.
- **Institution** ist, was an einem Ort betrieben wurde: gleicher Ort, aber Stalag, Internierung und
  Nachnutzung sind verschiedene Institutionen.
- **Arbeitskommando:** Die Nummer ist kein Schlüssel. Sie gilt je Stalag, wurde mehrfach vergeben und
  ist in den Quellen teils unsicher.
- **Betrieb** reicht vom Großbetrieb bis zum einzelnen Bauern.

Die Trennung von Quelle und Aussage folgt dem Factoid-Modell der Prosopographie.

## Ablauf

```bash
python -P entpacken.py <archiv> <manifest.jsonl>                    # Zips nach originale/, Manifest schreiben
python -P pilot.py stichprobe <manifest> <originale> <ausgabe>      # Zufallsstichprobe mit Kontaktbögen
python -P pilot.py bereitstellen <auswahl.jsonl> <originale> <ziel> # Bilder unter neutralem Namen
python -P abgleich.py <pilot> <manifest> <lauf-a> <lauf-b> <bilder-url> <pruefseite.html>
python -P auswertung.py <pilot> <entscheidungen.json> <einordnung.json>
```

`abgleich.py` vergleicht zwei Transkriptionsläufe und erzeugt aus `pruefseite.html` eine Seite für die
menschliche Prüfung. Sie enthält eine geschichtete Stichprobe, weil der Pilot Fehlerquoten messen soll,
nicht jeden Fehler beheben. Die erzeugte Seite enthält Namen und bleibt lokal.

`auswertung.py` misst die Läufe an den Prüfentscheidungen. Exporte der Prüfseite enthalten Namen und
gehören ins Datenrepo, nicht hierher.

`-P` statt `-I`: Pillow liegt in den User-Site-Packages, die `-I` ausblendet. Skripte bekommen Pfade als
Argument und werden nie aus dem Datenordner gestartet.

Regeln für das Lesen: [TRANSKRIPTION.md](TRANSKRIPTION.md). Wer beigetragen hat: [QUELLEN.md](QUELLEN.md).
