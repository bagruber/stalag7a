# Transkriptionsregeln

Das Transkript gibt wieder, was auf der Seite steht, nicht was gemeint ist. Deutung beginnt erst
eine Ebene höher. Wer hier etwas korrigiert, zerstört die Grundlage, auf der sich die Korrektur
später prüfen ließe.

## Zeichentreu

- Schreibweise, Abkürzungen, Groß- und Kleinschreibung, Satzzeichen und Zahlenformat wie im Bild.
  Nichts korrigieren, ergänzen oder auflösen, auch nicht offensichtliche Tippfehler.
- Bekannte Namen und Orte helfen nicht beim Lesen. Steht dort `Muenchn`, wird `Muenchn` geschrieben.
- Wiederholungszeichen bleiben Wiederholungszeichen (`"`), sie werden nicht durch den Wert darüber ersetzt.
- Ein Strich im Feld bleibt `-`. Ein leeres Feld ist `null`. Das sind zwei verschiedene Aussagen.
- Werte bleiben in der Spalte oder dem Feld, in dem sie stehen, auch wenn sie dort falsch wirken.
  Läuft ein Eintrag über mehrere Spalten, gehört er in die Spalte, in der er beginnt, und in `hinweise`.
- Zeilenumbruch innerhalb einer Zelle oder eines Felds: `\n`.
- Kurrent und Sütterlin werden in lateinischen Buchstaben wiedergegeben.
- Zeitgenössische Sprache und NS-Begriffe bleiben wörtlich und unkommentiert.

## Markierungen

| Schreibweise | Bedeutung |
|---|---|
| `[?]` | ein unleserliches Zeichen |
| `[...]` | unleserlicher Abschnitt, Länge unklar |
| `[?Muster]` | unsichere Lesung |
| `[-1917-]` | gestrichen, aber lesbar |
| `[-?-]` | gestrichen, nicht lesbar |
| `[-1917-]1915` | überschrieben: alt, dann neu |
| `[+Muster+]` | zwischen den Zeilen oder am Rand eingefügt |
| `[geschwärzt]` | abgedeckt, zum Beispiel durch einen schwarzen Balken |

Geraten wird nicht. Lieber `[...]` als eine plausible Lesung ohne Markierung.

## Aufbau

Je Bild eine JSON-Datei, UTF-8. Die Blöcke stehen in Leserichtung.

```json
{
  "bild": "a1b2c3d4e5f6",
  "seitenform": "liste",
  "blocks": [
    {"typ": "vordruck", "text": "Kategorie III\nForm. 7"},
    {"typ": "felder", "schrift": "schreibmaschine", "felder": [
      {"etikett": "Gemeinde", "wert": "Musterdorf"}
    ]},
    {"typ": "tabelle", "schrift": "schreibmaschine",
     "spalten": ["Fam.-Name", "Vorname", "Geburtsdat."],
     "zeilen": [
       ["Muster", "Anton", "1.1.11\nMusterstadt"],
       ["\"", null, "-"]
     ]},
    {"typ": "text", "schrift": "hand", "text": "erste Zeile\nzweite Zeile"},
    {"typ": "stempel", "text": "MUSTERSTEMPEL", "wo": "unten rechts"},
    {"typ": "vermerk", "text": "125", "farbe": "rot", "wo": "oben rechts"}
  ],
  "stellen": [
    {"lesung": "[?Muster]", "x": 0.12, "y": 0.34, "b": 0.08, "h": 0.02}
  ],
  "hinweise": "Spalte 3 ist am Rand abgeschnitten."
}
```

`stellen` listet jede Markierung `[?]`, `[...]`, `[?Muster]` und `[-?-]` einzeln mit ihrer ungefähren Lage
im Bild: `x` und `y` für die linke obere Ecke, `b` und `h` für Breite und Höhe, jeweils als Anteil
von Bildbreite und Bildhöhe (0 bis 1). So lässt sich die Stelle später ausschneiden und einem Menschen
vorlegen. Lieber etwas zu groß als zu knapp. Gibt es keine solche Stelle, ist die Liste leer.

| Block | Inhalt |
|---|---|
| `vordruck` | Gedruckter Text, soweit er das Formular kennzeichnet: Titel, Formularnummer, Druckvermerk. Keine Ausfüllhinweise. |
| `felder` | Ausgefüllte Felder eines Formulars oder einer Karte. `etikett` ist die gedruckte Beschriftung. Unausgefüllte Felder entfallen. |
| `tabelle` | `spalten` sind die gedruckten oder geschriebenen Köpfe, jede Zeile hat so viele Zellen wie Spalten. Leere Zellen sind `null`, auch ganz leere Spalten bleiben erhalten. Mehrere Tabellen auf einer Seite sind mehrere Blöcke. |
| `text` | Fließtext oder freie Notizen. |
| `stempel` | Stempelabdruck. |
| `vermerk` | Einzelner Eintrag außerhalb des Formularaufbaus: Randnotiz, Unterschrift, nachträgliche Nummer. Eine Unterschrift, die sich nicht lesen lässt, ist `[...]`. |

`schrift` ist `druck`, `schreibmaschine`, `hand` oder `gemischt`. `wo` und `farbe` sind freie, kurze
Angaben und entfallen, wo sie nichts beitragen.

`seitenform` beschreibt, wie die Seite aussieht: `liste` (vorgedruckte oder getippte Namensliste),
`karte` (Karteikarte oder Ausweis zu einer Person), `bogen` (mehrseitig angelegter Personalbogen),
`register` (Doppelseite eines gebundenen Buchs), `uebersicht` (Tabelle mit Zahlen statt Namen),
`fliesstext` oder `sonstiges`.

`hinweise` hält fest, was beim Lesen schwierig war, ohne den Inhalt zu deuten. Fehlt etwas, bleibt es leer.
