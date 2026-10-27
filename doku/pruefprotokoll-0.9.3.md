# Prüfprotokoll 0.9.3 – M3

Datum: 27.10.2026. Ausgangsversion 0.9.2. Bestehende Änderungen erhalten.

## Geändertes Verhalten

„Gewindepaar erstellen“ ergänzt ein zweites Bauteil mit eigener Flächenauswahl,
Fasen-Kanten, Längenmodus, Start-Endkante, Versatz und Länge. Gemeinsame Eingaben:
Teilung, Richtung, Profilwinkel, Verrundung, Zusatzfase und radiales Gesamtspiel.
Der metrische Modus berechnet die Innen-/Außentiefe weiterhin getrennt; im freien
Modus gilt dieselbe eingegebene Tiefe für beide Bauteile.

Vor Modelländerungen werden beide Parametersätze und Abschnitte validiert.
Das Paar erfordert eine Außen- und eine Innenzylinderfläche mit gleichem
Nenndurchmesser auf verschiedenen nativen Körpern. Radiusvergleich in cm:
relative Toleranz 1e-6, absolute Toleranz 1e-7. Keine automatische Skalierung.
Die Körper müssen nicht koaxial sein. Zwei Vorkommen desselben nativen Körpers
werden abgewiesen, da eine Bearbeitung beide Instanzen verändern würde.

Spielverteilung ist auch für Einzelgewinde verfügbar:

| Verteilung | Außenradius bei 0,20 mm Gesamtspiel | Innenradius | Radiale Differenz |
| --- | --- | --- | --- |
| Gleichmäßig | −0,10 mm | +0,10 mm | 0,20 mm |
| Nur Innengewinde | 0 | +0,20 mm | 0,20 mm |
| Nur Außengewinde | −0,20 mm | 0 | 0,20 mm |

Die Erstellung beider Gewinde erfolgt innerhalb desselben Fusion-Befehls.
Eine Ausnahme beim ersten oder zweiten Gewinde setzt `executeFailed = True`;
Fusion soll dadurch die gesamte Befehlstransaktion zurücknehmen. Der
automatische Test belegt diesen Fehlerpfad, keine tatsächliche B-Rep-Rücknahme.

Ergebnisanzeige enthält beide Abschnitte, die Tiefe des zweiten Bauteils und
die Spielverteilung. Pro Bauteil wird eine Dokumentationsskizze mit den
jeweiligen Parametern einschließlich Spielverteilung erzeugt.

## Kompatibilität und Presets

Schema bleibt 1. Neue Felder: `pair_mode` (Default false),
`clearance_distribution` (balanced / internal / external, Default balanced),
`partner_full_length` (Default true), `partner_start_offset_cm` (Default 0),
`partner_thread_length_cm` (Default 1 cm). Alte Presets bleiben Einzelgewinde
mit bisheriger Spielverteilung. Zweite Startkante, Flächen und Fasen-Kanten
sind Modellbezüge und werden nicht exportiert. Presets mit neuen Funktionen
nur mit 0.9.3 oder neuer anwenden: Ältere Versionen ignorieren diese Felder.
Ungültige Verteilungen und zweite Längeneinstellungen werden vor Import abgewiesen.

## Automatische Prüfungen

Windows, CPython 3.12.15 aus lokaler uv-Installation. Baseline: 19 Tests bestanden.
Nach Umsetzung: 24 Tests bestanden mit `python -m unittest discover -s tests -v`.
`git diff --check` ohne Fehler.

Neue Regressionen prüfen unabhängig erwartete radiale Korrekturen aller drei
Verteilungen, Paar-Kompatibilität und Ablehnung desselben nativen Körpers,
getrennte Abschnittsparameter und metrische Innentiefe, Abbruchanforderung bei
Fehler im zweiten Gewinde sowie Preset-/JSON-Rundlauf und unveränderten Speicher
bei ungültigen Importen. Syntax und Übersetzungsschlüssel aller Python-Dateien
sowie neue Texte in allen sechs Sprachen werden durch bestehende Tests geprüft.

## Fusion-Prüfmatrix – offen

Keine eigene Fusion-/macOS-Prüfung durch Codex. Fusion-Version/Build und
Plattform für M3: offen. M2-Anwenderergebnisse siehe
[Prüfprotokoll 0.9.2](pruefprotokoll-0.9.2.md); diese ersetzen keine M3-Abnahme.

| Fall | Erwartung | Ergebnis |
| --- | --- | --- |
| Nebeneinanderliegende Außen-/Innenzylinder mit gleichem Nenndurchmesser | Beide Gewinde entstehen mit gemeinsamer Teilung und Richtung | offen |
| Innenfläche zuerst, Außenfläche als zweites Bauteil | Korrekte metrische Tiefe für beide Gewindetypen | offen |
| Rechts/links, metrisch/frei | Gültige, zusammenpassende Profilgeometrie | offen |
| Alle drei Spielverteilungen, Spiel 0 und 0,20 mm | Radiale Korrekturen entsprechen obiger Tabelle; kein doppeltes Gesamtspiel | offen |
| Unterschiedliche Längen, Versätze und Startseiten | Jeder Abschnitt entspricht seinen eigenen Eingaben | offen |
| Fasen je Bauteil 0/1/2, Zusatzfase | Nur geeignete erreichte Endkanten erhalten Fasen | offen |
| Gleiche Gewindeart, ungleiche Nenndurchmesser, gleiche native Körper/Instanzen | Abbruch vor Modelländerungen mit verständlicher Meldung | offen |
| Gedrehte/verschobene Komponenten | Korrekte lokale Lage beider Gewinde | offen |
| Fehler bei Erstellung des zweiten Gewindes | Auch erstes Gewinde und alle Hilfsobjekte vollständig zurückgenommen | offen |
| Abbruch, Undo/Redo, Speichern/Öffnen | Beide Bauteile gemeinsam nachvollziehbar wiederherstellbar | offen |
| Paar-Preset/JSON mit einseitigem Spiel laden | Modus, Verteilung und beide Längeneinstellungen übernommen; Modellbezüge neu wählen | offen |
| Altes Preset / Einzelgewinde mit gleichmäßiger Verteilung | Bisheriges Verhalten und Maße | offen |

## Druckprüfung – offen

Mindestens ein Paar drucken und Drucker, Material, Düse, Schichthöhe,
Orientierung, Nenndurchmesser, Teilung, Längen, Spielverteilung, Gesamtspiel
und Passungsergebnis dokumentieren. Keine Druckpassung aus Python-Tests ableiten.

Status: implementiert, Fusion- und Druckabnahme offen. Version, Manifest und
Installer-Konfiguration auf 0.9.3. Kein Installer gebaut, kein Commit/Push/Release.
Nächster Schritt: M3-Abnahme; M4 nur als eigener Auftrag.
