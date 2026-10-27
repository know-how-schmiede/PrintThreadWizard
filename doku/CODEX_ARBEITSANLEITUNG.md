# PrintThreadWizard – Arbeitsanleitung für Codex

Stand: 27.10.2026. Grundlage: main, Commit `797bccbfa617edf0b63e929225d8623ecdf147df`, Entwicklungsversion 0.8.4.
Repository: https://github.com/know-how-schmiede/PrintThreadWizard

## Verwendung

Diese Datei als `doku/CODEX_ARBEITSANLEITUNG.md` und die begleitende Roadmap als `doku/ROADMAP.md` im Repository ablegen. Sie beschreiben geplante Entwicklung; enthaltene Funktionen sind keine Zusage über bereits vorhandenes Verhalten. Bestehende AGENTS.md-Regeln beachten; diese Anleitung ersetzt sie nicht. Die Dokumente werden mit dieser Lieferung nicht automatisch ins Repository übertragen.

### Startauftrag zum Einfügen in Codex

```text
Lies zuerst AGENTS.md, README_DE.md, doku/CODEX_ARBEITSANLEITUNG.md,
doku/ROADMAP.md und doku/version-timeline.md. Prüfe den aktuellen Code und
Arbeitsbaum. Beginne mit M0 der Roadmap; bearbeite danach den nächsten
offenen Meilenstein, sofern kein anderer beauftragt wurde.
Implementiere den ausgewählten Meilenstein einschließlich sinnvoller Tests,
Dokumentation und Kompatibilität alter Presets. Arbeite in kleinen,
nachvollziehbaren Schritten und erhalte fremde Änderungen.
Kennzeichne Prüfungen, die nur in Autodesk Fusion möglich sind, als offen.
Berichte am Ende über Änderungen, Prüfungen und verbleibende Grenzen.
Ein abgeschlossener Meilenstein berechtigt nicht automatisch zur
Implementierung aller späteren Meilensteine oder zur Veröffentlichung.
```

## 1. Ziel und Ausgangslage

PrintThreadWizard soll schnell zu reproduzierbar passenden, gedruckten Gewinden führen. Vorrang haben Bedienbarkeit, robuste Geometrie und Kalibrierung.

Vorhanden sind Innen- und Außengewinde auf Zylinderflächen, Rechtsgewinde, ein metrischer Berechnungsmodus, freie Profilparameter, radiales Gesamtspiel, Grundverrundung, optionale Endfasen einschließlich Zusatzgröße, Dokumentationsskizze, Timeline-Gruppierung, lokale Presets und JSON-Transfer. Die Oberfläche unterstützt DE, EN, ES, FR, IT und PL.

Wichtig: Der metrische Berechnungsmodus und eine passende Nenngröße garantieren keine normgerechte Passung oder Kompatibilität mit metallischen Gegenstücken.

## 2. Einstieg in den Code

Alle folgenden Pfade sind relativ zum Repository. Die Zuordnung ist eine Orientierung und muss vor Änderungen überprüft werden.

| Datei / Bereich | Verantwortung |
| --- | --- |
| `Fusion_AddIn/PrintThread Wizard/commands/commandDialog/entry.py` | Dialog, Eingaben, Ergebnisse, Preset-Bedienung |
| `Fusion_AddIn/PrintThread Wizard/core/thread_parameters.py` | Parameter, Validierung, Spielverteilung |
| `Fusion_AddIn/PrintThread Wizard/core/iso_metric.py` | Metrische Profilberechnung |
| `Fusion_AddIn/PrintThread Wizard/core/thread_presets.py` | Preset-Speicherung und Transfer |
| `Fusion_AddIn/PrintThread Wizard/fusion/thread_geometry.py` | Helix, Profil, Sweep, Beschneidung, Dokumentation |
| `Fusion_AddIn/PrintThread Wizard/fusion/face_analysis.py` | Analyse von Zylinderflächen und Komponentenbezügen |
| `Fusion_AddIn/PrintThread Wizard/fusion/chamfer.py` | Fasen |
| `Fusion_AddIn/PrintThread Wizard/localization*.py` | Übersetzungen |
| `Fusion_AddIn/PrintThread Wizard/version.py` | Add-in-Version |
| `tests/test_localization.py` | Bestehende Tests einschließlich einiger Parameter-/Preset-Prüfungen |
| `doku/version-timeline.md`, README-Dateien, `installer/` | Verlauf, Anwenderdokumentation, Installation |

Berechnung und Datenmigration möglichst in `core/` halten, ohne Fusion-Abhängigkeit. Fusion-Zugriffe in `fusion/` kapseln. Nicht jede neue Funktion direkt in den bereits großen Dialog einbauen; zusammenhängende Zuständigkeiten gezielt auslagern, ohne Komplettumbau.

## 3. Verbindliche Regeln

### Einheiten und Bedeutungen

- Fusion-interne Längen sind Zentimeter, Winkel Bogenmaß. Umrechnung nur an definierten Schnittstellen; keine stillschweigenden Millimeterannahmen.
- `tolerance` bedeutet bisher radiales Gesamtspiel des Paars. Bei gleichen Einstellungen wird der Außenradius um die Hälfte verkleinert, der Innenradius um die Hälfte vergrößert.
- Beispiel: 0,20 mm Gesamtspiel → außen −0,10 mm Radius, innen +0,10 mm Radius. Die jeweiligen Durchmesser ändern sich um −0,20 bzw. +0,20 mm. Gesamtspiel nicht als Durchmesseränderung beschriften.
- Dieses Verhalten bleibt Standard. Neue einseitige Verteilung muss ausdrücklich gewählt werden und denselben Gesamtwert erhalten.
- Derzeit bezeichnet `pitch` bei eingängigem Gewinde auch den axialen Weg pro Umdrehung. Mehrgängigkeit später nur mit expliziter Trennung von Teilung P und Leitweg L einführen: L = Gangzahl × P.

### Kompatibilität und Daten

- Neue Parameter benötigen rückwärtskompatible Defaults: Rechtsgewinde, ganze bisherige Gewindelänge, bisheriges Spielverhalten, keine zusätzlichen Profiländerungen.
- Alte Presets und JSON-Dateien müssen dieselbe Geometrie wie zuvor ergeben, soweit nicht ein ausdrücklich dokumentierter Fehler korrigiert wird.
- Vor Schemaänderungen vorhandene Versionierung prüfen. Migrationen zentral implementieren; bei zukünftigem unbekanntem Schema verständlich abbrechen, statt Daten stillschweigend umzudeuten.
- Preset-Import erst vollständig validieren und anschließend übernehmen. Fehler dürfen die bisherige Datei nicht beschädigen.
- Alle Zahlen auf Endlichkeit und Wertebereich prüfen, einschließlich NaN und Unendlich.
- Flächen-/Kantenbezüge nicht als portable Preset-Daten exportieren. Modellbezüge gehören zum Dokument.

### Modell und Bedienung

- Abbrechen, Vorschaufehler und Erstellungsfehler dürfen keine Hilfskörper, Skizzen oder teilweise veränderten Ausgangskörper hinterlassen. Vorhandene Aufräumlogik inklusive Änderungen am Zielkörper prüfen.
- Bei Paaren gilt dies für beide Bauteile gemeinsam. Schlägt das zweite Gewinde fehl, muss auch das erste zurückgenommen werden.
- Komponenteninstanzen, transformierte Vorkommen und lokale Koordinatensysteme berücksichtigen. Mehrere Vorkommen derselben Komponente nicht versehentlich doppelt bearbeiten.
- Neue Texte und Validierungen in allen sechs Sprachen pflegen. Fachbegriffe in Tooltips erklären.
- Bestehende Presets und Dokumentationsskizzen um die neuen fachlichen Parameter ergänzen.

## 4. Vorgehen pro Meilenstein

1. Aktuellen Branch, Arbeitsbaum, Version, Regeln und Meilenstein prüfen. Fremde Änderungen erhalten.
2. Relevanten Ausführungspfad lesen. Baseline-Tests ausführen und bestehende Fehler getrennt dokumentieren.
3. Kleine Umsetzungsskizze mit betroffenen Modulen und Datenänderungen erstellen. Nur bei einer tatsächlich blockierenden Produktentscheidung nachfragen.
4. Fachliche Berechnung und Validierung zuerst implementieren, danach Fusion-Geometrie, Dialog, Speicherung und Übersetzungen.
5. Aussagekräftige Regressionstests für Berechnung, Migration und Fehlerfälle ergänzen. Keine Tests schreiben, die lediglich die Implementierung nacherzählen.
6. Relevante automatische Prüfungen und die Fusion-Prüfmatrix durchführen, soweit die Umgebung dies erlaubt.
7. README DE/EN, Timeline und Roadmap aktualisieren. Version und Installer nur gemäß bestehendem Release-Prozess konsistent anpassen.
8. Ergebnis mit geändertem Verhalten, Prüfergebnissen und offenen Punkten übergeben. Commit/Push/Release nach dem vereinbarten Repository-Workflow; Veröffentlichung ist ein eigener Schritt.

## 5. Prüfstrategie

### Automatisch, ohne Fusion

Bestehenden Testlauf aus dem Repository-Stamm starten:

```bash
python -m unittest discover -s tests -v
```

Zusätzlich je nach Änderung testen: Einheitenumrechnung, Profilgrenzen, Spielverteilung, Steigungs-/Leitwegbeziehung, unbekannte Enum-Werte, alte Presets mit fehlenden Feldern, Import-/Export-Rundlauf und abgebrochene/fehlerhafte Importe. Fusion-API nicht für reine Mathematik nachbauen. Bei Berechnungsfehlern erwartete Werte unabhängig herleiten.

### Manuell in Autodesk Fusion

| Prüffall | Erwartung |
| --- | --- |
| Innen- und Außengewinde, beide Berechnungsmodi | Gültige Körper, erwartete Maße und Profilform |
| Kleine, mittlere und große Durchmesser | Plausible Grenzen, keine unerklärten Sweepfehler |
| Kurze/lange Gewinde, Spiel 0 und zulässige Randwerte | Validierung und Geometrie stimmen überein |
| Ohne Fase, eine Fase, zwei Fasen, Zusatzfase | Nur gewählte Enden geändert |
| Gedrehte und verschobene Komponenteninstanz | Richtige Lage, Richtung und Zielkörper |
| Abbruch, absichtlicher Fehler, Undo/Redo | Ausgangszustand wiederherstellbar; keine Reste |
| Dokument speichern, schließen, wieder öffnen | Modell und gespeicherte Parameter bleiben nutzbar |
| Alte Presets und JSON-Dateien | Bisheriges Verhalten bleibt erhalten |

Neue Meilensteine ergänzen eigene Prüffälle. Messergebnisse, verwendete Fusion-Version und Plattform im Prüfprotokoll festhalten. Automatische Python-Tests belegen weder gültige B-Rep-Geometrie noch reale Druckpassung. Fehlenden Zugriff auf Fusion ausdrücklich melden; keine erfolgreichen Fusion- oder macOS-Tests behaupten.

### Physische Passungsprüfung

Für Paar- und Kalibrierungsfunktionen mindestens ein dokumentierter FDM-Test: Drucker, Material, Düse, Schichthöhe, Orientierung, Spiel und Ergebnis festhalten. Beispielwerte sind Testreihen, keine allgemeingültigen Materialempfehlungen.

## 6. Abschlusskriterien

Ein Meilenstein ist erst abgeschlossen, wenn seine Abnahmekriterien erfüllt, relevante Prüfungen dokumentiert, alte Daten berücksichtigt und Anwendertexte aktualisiert sind. Bei fehlenden Fusion-/Druckprüfungen lautet der Status „implementiert, Abnahme offen“. Keine normgerechte Passung, Tragfähigkeit oder Sicherheitsfreigabe aus Geometrieprüfungen ableiten.

### Übergabeformat

```text
Meilenstein:
Geändertes Verhalten:
Betroffene Dateien:
Automatische Prüfungen und Ergebnis:
Fusion-Prüfung mit Version/Plattform:
Druckprüfung, falls erforderlich:
Kompatibilität/Migration:
Offene Punkte und nächster Schritt:
```
