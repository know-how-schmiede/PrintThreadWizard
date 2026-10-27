# Prüfprotokoll 0.9.1 – M1

Datum: 27.10.2026. Ausgangsversion 0.9.0, Branch main, Arbeitsbaum zu Beginn sauber. Keine AGENTS.md im Repository vorhanden. Anwender bestätigt den Betrieb von 0.9.0 in Fusion; Fusion-Version/Plattform und detaillierte M0-Fehlerprüfung wurden nicht genannt.

## Umsetzung und Kompatibilität

`ThreadParameters.handedness`: `right` (Standard) oder `left`. Eingabesteigung, Umdrehungszahl und Helixüberlauf bleiben positiv. Für links werden die kopierte Helixachse und die Helixsteigung umgekehrt; damit bleibt der axiale Weg gleich und der Drehsinn kehrt sich um. Die Profiltangente verwendet ebenfalls die vorzeichenbehaftete Steigung. Rechts verwendet dieselben geometrischen Werte wie zuvor. Die ursprüngliche Zylinderachse und Komponentenbezüge bleiben unverändert.

Die Richtung erscheint im Dialog, Ergebnis, Preset-Details und in der Dokumentationsskizze. Presets speichern `handedness`; fehlende Werte ergeben rechts. Unbekannte Werte werden vor Speicherung/Import abgewiesen. Schema bleibt 1; keine Änderung der bisherigen Maße oder Spielverteilung. Linksgängige Presets nur mit 0.9.1 oder neuer anwenden: ältere Add-in-Versionen kennen das neue Feld nicht.

API-Grundlage: [Autodesk createHelixWire](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TemporaryBRepManager_createHelixWire.htm). Dort sind Steigung in cm und Umdrehungszahl beschrieben, jedoch keine ausdrückliche Garantie für negative Werte. Anwenderprüfung: teilweise funktionsfähig, Linksgewinde scheiterte mit `ASM_HELIX_NR_TURNS_TOO_SMALL`. Ursache war die negative Umdrehungszahl der ersten Umsetzung. Korrektur innerhalb 0.9.1: positive Umdrehungszahl und umgekehrte Helixachse bei negativer Steigung. API-Ausnahmen dieser Helixerzeugung werden lokalisiert angezeigt; die technische Ursache bleibt im Log. Anwender hat nach der Korrektur am 27.10.2026 mit „funktioniert jetzt“ die Funktion in Fusion bestätigt. Die einzelnen Fälle der vollständigen Prüfmatrix wurden dabei nicht separat beschrieben.

## Automatische Prüfungen

Windows, CPython 3.12.15. Baseline: 11 Tests bestanden. Nach Korrektur: 14 Tests bestanden (`python -m unittest discover -s tests -v`). Neue Fälle: Rechts-Default, umgekehrte Rotation bei gleichem axialem Weg, beide Richtungen im Preset-/JSON-Rundlauf, unbekannte Richtung ohne Änderung der bestehenden Datei. Zusätzlicher Regressionstest führt die echte Helixfunktion bis zu einem injizierten API-Fehler aus: positive Umdrehungszahl, richtige Achskopie/Steigung, ursprüngliche Achse unverändert, lokalisierte Ausgabe in allen sechs Sprachen. Kein B-Rep-Nachweis. Bestehende Tests für alte Presets, Mathematik, Fehlerhandler, Übersetzungen und Versionen bleiben erfolgreich.

## Manuelle Fusion-Prüfung – Funktion bestätigt, Detailprüfungen offen

Anwenderbestätigung: Funktion nach der Linksgewinde-Korrektur erfolgreich. Keine eigene Fusion-Geometrieprüfung durch Codex durchgeführt. Fusion-Version/Build, Plattform, Maße und genaue Testkonfiguration wurden nicht genannt. Die folgenden Detailfälle bleiben daher bis zur gesonderten Bestätigung offen.

| Fall | Erwartung | Ergebnis |
| --- | --- | --- |
| Wiederholung nach Helix-Korrektur | Gewindeerstellung funktioniert ohne den gemeldeten Helixfehler | vom Anwender bestätigt, 27.10.2026 |
| Rechte Innen-/Außengewinde, metrisch und frei | Geometrie und Maße wie 0.9.0 | offen |
| Linke Innen-/Außengewinde, metrisch und frei | Gültiger Körper, umgekehrter Drehsinn bei gleicher Länge/Tiefe | offen |
| Linksgängiges Paar | Beide Partner passen geometrisch zusammen | offen |
| Gedrehte und verschobene Komponenten | Richtige Lage, Richtung und Zielkörper | offen |
| Fasen 0/1/2, Zusatzfase und Verrundung | Vollständige Abschlüsse bei beiden Richtungen | offen |
| Links-Preset speichern/exportieren/importieren | Richtung bleibt links; alte Presets setzen Dialog wieder auf rechts | offen |
| Richtungswechsel im Dialog | Ergebnis und Dokumentationsskizze zeigen die gewählte Richtung | offen |
| Fehler, Abbruch, Undo/Redo, Speichern/Öffnen | Keine Modellreste, Zustand wiederherstellbar | offen |

Status: implementiert, Funktion in Fusion vom Anwender bestätigt; vollständige Abnahme offen. Druckprüfung für M1 nicht gefordert. Kein Installer gebaut, kein Commit/Push/Release. Nächster Entwicklungsschritt: M2 (Gewindelänge und Startversatz) als separater Auftrag. Offene Detailprüfungen bleiben dokumentiert.
