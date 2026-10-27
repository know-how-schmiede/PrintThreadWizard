# Prüfprotokoll 0.9.2 – M2

Datum: 27.10.2026. Branch main. Ausgangsversion 0.9.1. Bereits vorhandene Änderung an `pruefprotokoll-0.9.1.md` erhalten. Keine AGENTS.md im Repository gefunden.

## Geändertes Verhalten

Ganze Länge bleibt Standard. Für Teilgewinde eine kreisförmige Endkante der Zielfläche als Startseite wählen; durch Auswahl der anderen Kante wird die Seite umgekehrt. Die Position des gewählten Endes entscheidet über die Abschnittsberechnung, nicht das Vorzeichen der internen Zylinderachse. Es gibt keine stillschweigende Startseite für Teilgewinde.

Versatz und Gewindelänge werden in Fusion-internen cm validiert. Beispiel: 40 mm Zylinder, 2 mm Versatz, 15 mm Gewinde ergibt 2–17 mm ab dem ersten bzw. 23–38 mm ab dem gegenüberliegenden Ende. Negative Werte, Länge 0, NaN/Unendlich und Überschreitung der verfügbaren Länge werden abgewiesen. Numerische Grenztoleranz: 1e-7 cm, ohne sichtbaren Überstand.

Die Spielkorrektur verwendet den begrenzten Abschnitt. Die Helix reicht weiterhin eine Steigung über beide Abschnittsgrenzen hinaus. Innengewinde und Außen-Teilgewinde werden als eigener Sweepkörper erzeugt und axial mit einem Zylinder auf die sichtbare Länge beschnitten. Erst danach wird innen verbunden bzw. außen geschnitten. Ganze Außenlänge nutzt den bisherigen direkten Sweep-Schnitt.

Fasenkanten müssen echte kreisförmige Endkanten der ausgewählten Zielfläche sein. Bei Teilgewinden muss der Abschnitt dieses Bauteilende erreichen und die axiale Fasengröße aufnehmen können. Keine Fasen an künstlichen Abschnittsgrenzen. Mehrere, sich gegenseitig überschneidende Fasen bleiben geometrisch in Fusion zu prüfen.

Dialog, Ergebnis, Preset-Details und Dokumentationsskizze zeigen die neuen Parameter. Ergebnis und Skizze enthalten zusätzlich die Abschnittsgrenzen in lokalen Komponentenkoordinaten. Eine grafische Bereichsvorschau gehört weiterhin zu M5.

## Kompatibilität

Neue portable Felder: `full_length` (Default true), `start_offset_cm` (Default 0), `thread_length_cm` (Default 1 cm, bei ganzer Länge ohne geometrische Wirkung). Schema bleibt 1. Alte Presets erzeugen weiterhin ganze Länge und ihre bisherige Richtung. Die Startkante bleibt ausschließlich ein aktueller Modellbezug und wird nicht exportiert; sie muss für das Zielbauteil gewählt werden. Teilgewinde-Presets nur mit 0.9.2 oder neuer anwenden, da frühere Versionen diese Felder ignorieren.

## Prüfungen

Nachtrag zur Kantenauswahl: `Command.hasDistinctSelectionSets = True` aktiviert getrennte Auswahlsätze für Fasen-Kanten und Startseite. Der zuvor gesetzte Wert `False` behielt die gemeinsame Auswahl bei und löste den gemeldeten Fehler nicht. Die API-Referenz beschreibt die booleschen Werte umgekehrt zu den [Autodesk-Release-Hinweisen vom November 2024](https://www.autodesk.com/products/fusion-360/blog/november-2024-product-update-whats-new/). Beide Auswahlreihenfolgen wurden vom Anwender in Fusion als bestanden bestätigt.

Windows, CPython 3.12.15 aus lokaler uv-Installation. Baseline: 14 Tests bestanden. Nach Umsetzung: 19 Tests bestanden mit `python -m unittest discover -s tests -v`.

Neue Regressionen: Bereiche von beiden Enden und unveränderte ganze Länge; ungültige Zahlen und Bereichsgrenzen; Preset-/JSON-Rundlauf und Ablehnung ungültiger Werte ohne Änderung der Zieldatei; Auflösung der gewählten Startseite, fehlende Startkante und Fasengrenzen; Außen-Teilgewinde verwendet einen Sweep-Werkzeugkörper statt eines unbeschnittenen direkten Schnitts. Tests der API-Grenzen verwenden Aufrufaufzeichnung, keine nachgebaute B-Rep-Geometrie.

API-Grundlage: [SweepFeatures.createInput](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SweepFeatures_createInput.htm) und [CombineFeatureInput.operation](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_CombineFeatureInput_operation.htm).

## Fusion-Prüfmatrix – teilweise bestanden

Anwender-Rückmeldung vom 27.10.2026: Die sechs markierten Fälle haben in Fusion bestanden. Keine eigene Fusion- oder macOS-Prüfung durch Codex. Fusion-Version/Build, Plattform und einzelne Messwerte wurden nicht angegeben. Nicht bestätigte Fälle bleiben offen.

| Fall | Erwartung | Ergebnis |
| --- | --- | --- |
| 40 mm Zylinder, Versatz 2 mm, Länge 15 mm | Exakt 15 mm Gewinde; übrige Fläche und Durchmesser unverändert | bestanden (Anwender) |
| Andere Start-Endkante wählen | Entsprechender Abschnitt vom anderen Ende | bestanden (Anwender) |
| Dieselbe Kante als Fasen-Kante und Startseite, beide Auswahlreihenfolgen | Beide Felder behalten ihre Auswahl; Wechsel und Abwahl bleiben unabhängig | bestanden (Anwender) |
| Innen/außen, rechts/links, metrisch/frei | Gültiger Körper und richtiger Bereich | offen |
| Ganze Länge und alte Presets | Verhalten und Maße wie 0.9.1 | bestanden (Anwender) |
| Offset 0, bis zum Ende, sehr kurze/lange Bereiche | Grenzen korrekt, keine Helixreste außerhalb des Abschnitts | bestanden (Anwender) |
| Spiel 0 und 0,15 mm | Spiel nur im Gewindeabschnitt, keine Änderung außerhalb | offen |
| Fasen 0/1/2, Zusatzfase | Nur erreichte echte Enden; unzulässige Fasen vor Modelländerung abweisen | bestanden (Anwender) |
| Fremde/innere/ungeeignete Endkante | Verständliche Validierung, kein Modellrest | offen |
| Gedrehte/verschobene Komponenteninstanz | Richtige Seite und Lage; lokale Koordinaten plausibel | offen |
| Fehler bei Sweep/Beschneidung/Combine | Gesamte Befehlstransaktion zurückgenommen | offen |
| Abbruch, Undo/Redo, Speichern/Öffnen | Modellzustand und Parameter nachvollziehbar | offen |
| Teilgewinde-Preset exportieren/importieren | Maße bleiben erhalten; Startkante am Zielbauteil wählen | offen |

Status: implementiert, sechs Fusion-Prüffälle durch den Anwender bestanden; übrige Abnahme offen. Druckprüfung für M2 nicht gefordert. Einlauf, Auslauf und Freistich sind nicht Teil dieser Umsetzung. Kein Commit/Push/Release, kein Installer gebaut. Nächster Schritt: Fusion-Abnahme von M2; danach M3 als eigener Auftrag.
