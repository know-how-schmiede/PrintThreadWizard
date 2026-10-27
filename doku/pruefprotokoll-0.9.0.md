# Prüfprotokoll 0.9.0 – M0

Datum: 27.10.2026. Branch: main. Ausgangsstand: 797bccbfa617edf0b63e929225d8623ecdf147df. Arbeitsbaum zu Beginn sauber; keine AGENTS.md im Repository gefunden. Kein Commit/PR und keine Veröffentlichung erstellt.

## Umsetzung

Parameter- und Preset-Validierung bleiben in core/, Fusion-Geometrie unverändert. Vorhandene partielle Aufräumlogik kann Änderungen durch Sweep, Join und Fasen nicht vollständig garantieren. Deshalb markiert der Execute-Handler jeden Fehler als fehlgeschlagene Befehlstransaktion. Dies umfasst auch Fehler bei Dokumentationsskizze und Timeline-Gruppierung. Kein Vorschauhandler vorhanden; Abbruch vor OK erzeugt keine Gewindegeometrie.

API-Grundlage: [Autodesk executeFailed](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/core_CommandEventArgs_executeFailed.htm) und [Command-Transaktionen](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Commands_UM.htm). Der Handler-Test prüft das Anfordern der Rücknahme, nicht deren B-Rep-Ergebnis.

Schema bleibt 1. Vollständige alte Parametersätze ohne tolerance_cm/chamfer_extra_cm behalten ihre bisherigen Defaults. Unvollständige oder ungültige Parametersätze werden jetzt bewusst zurückgewiesen; sie konnten bisher gespeichert, aber nicht zuverlässig angewendet werden. Kein neuer Geometrieparameter. Import prüft alle Einträge und Voreinstellungen vor atomarem Dateiersatz.

## Automatische Prüfungen

Windows, CPython 3.12.15 aus lokaler uv-Installation. Der Windows-Store-Aufruf python.exe scheitert an einer fehlenden Anmeldesitzung. Keine Installation zusätzlicher Pakete nötig.

- Baseline HEAD separat in temporäres Verzeichnis extrahiert: 6 Tests bestanden.
- `python -m unittest discover -s tests -v`: 11 Tests bestanden.
- Abdeckung: sechs Sprachen und Platzhalter, Syntax der Add-in-Module, Versionen, radiales Gesamtspiel mit Faktor 2 für Durchmesser, getrennte metrische Tiefen, NaN/Unendlich und Profilgrenzen, alte Presets, Rundlauf, unbekanntes Schema/Berechnungsmodus, ungültige Importe ohne Änderung der Zieldatei, Transaktionsabbruch im Fehlerhandler.

## Wiederverwendbare Fusion-Prüfmatrix – offen

Keine Fusion- oder macOS-Prüfung durchgeführt. Fusion-Version/Build: offen. Plattform des manuellen Tests: offen. Je Fall Modell, Eingaben, Ergebnis und Messwerte dokumentieren.

| Fall | Prüfung / Erwartung | Ergebnis |
| --- | --- | --- |
| Außen/innen, metrisch/frei | Kleine/mittlere/große Durchmesser; gültiger Körper, erwartete Tiefe und Spiel | offen |
| Kurze/lange Zylinder | Spiel 0 sowie Randwerte; vollständige Enden | offen |
| Fasen 0/1/2, Zusatzfase | Nur ausgewählte Enden ändern; Geometrie messen | offen |
| Gedrehte/verschobene Instanz | Lage und Zielkörper stimmen; zweite Instanz unverändert wie vorgesehen | offen |
| Abbruch vor OK | Keine neuen Features/Körper/Skizzen | offen |
| Absichtlicher Fehler nach Sweep/Join/Fase | In Testkopie Ausnahme nach jeweiligem Schritt auslösen; Ausgangskörper, Volumen und Timeline vollständig wiederhergestellt | offen |
| Fehler beim Anlegen der Notiz/Gruppierung | Gesamte Transaktion zurückgenommen, keine Reste | offen |
| Erfolg, Undo/Redo | Gesamtes Gewinde gemeinsam rückgängig/wiederherstellbar | offen |
| Speichern/Schließen/Öffnen | Modell und Presets weiter nutzbar | offen |
| Alte Schema-1-Datei | Identische Einstellungen und Geometrie wie 0.8.4 | offen |

Druckprüfung für M0 nicht erforderlich. Python-Tests belegen keine B-Rep-Gültigkeit oder reale Druckpassung. M0 bleibt implementiert/Abnahme offen; nächster Schritt ist diese Fusion-Matrix, anschließend M1 als eigener Auftrag gemäß Arbeitsanleitung.
