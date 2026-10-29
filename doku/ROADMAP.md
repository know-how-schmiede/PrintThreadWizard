# PrintThreadWizard – Roadmap

Stand: 27.10.2026. Ausgangsbasis: Entwicklungsversion 0.8.4, main-Commit `797bccbfa617edf0b63e929225d8623ecdf147df`.
Repository: https://github.com/know-how-schmiede/PrintThreadWizard

## Ziel

Gedruckte Gewinde leichter konstruieren, reproduzierbar auf den eigenen Druckprozess abstimmen und später gezielt verändern können. Die Roadmap ist ein Vorschlag ohne feste Termine oder zugesagte Versionsnummern. Alle Meilensteine sind zunächst geplant; der erste Arbeitsschritt muss den inzwischen aktuellen Stand prüfen.

## Reihenfolge und Umfang

| Meilenstein | Ergebnis | Priorität | Relativer Aufwand | Abhängigkeit |
| --- | --- | --- | --- | --- |
| M0 | Belastbare Ausgangsbasis und Fehlerbehandlung | Sehr hoch | Klein–mittel | Keine |
| M1 | Rechts-/Linksgewinde | Hoch | Klein–mittel | M0 |
| M2 | Gewindelänge und Startversatz | Sehr hoch | Mittel | M0 |
| M3 | Gewindepaar und einseitiger Spielausgleich | Sehr hoch | Mittel–hoch | M1, M2 |
| M4 | Kalibrierungsassistent und Druckprofile | Sehr hoch | Mittel–hoch | M3 |
| M5 | Größenhilfe und schlanke Vorschau | Hoch | Mittel–hoch | M2, M3 |
| M6 | Bestehende Gewinde bearbeiten | Hoch | Hoch | M1–M4 |
| M7 | Mehrgängige Gewinde und alternative Profile | Mittel | Hoch–sehr hoch | M6 |

Aufwand bezeichnet die relative Komplexität einschließlich Integration und Prüfung, keine Arbeitszeitzusage. M1 und M2 sind weitgehend unabhängig; die Tabelle beschreibt eine gut überprüfbare Reihenfolge. Keine automatische Beauftragung paralleler Agentenarbeit.

## M0 – Ausgangsbasis absichern

**Status 27.10.2026 / 0.9.0:** implementiert. Anwender bestätigt, dass das Plugin in Fusion läuft. Detaillierte Fehler-/Undo-Prüfung nicht bestätigt, siehe [Prüfprotokoll](pruefprotokoll-0.9.0.md). M1 wurde als nächster Schritt beauftragt.

**Ziel:** Bestehendes Verhalten verstehen, bevor neue Geometrie hinzukommt.

- [x] Aktuellen Stand und bestehende Regeln mit der Planung abgleichen.
- [x] Tests ausführen; vorhandene Parameter-/Preset-Prüfungen erfassen.
- [x] Fehlende Prüfungen für Spielverteilung, metrische Berechnung, ungültige Zahlen und Preset-Kompatibilität ergänzen.
- [x] Fehler- und Abbruchpfade einschließlich Änderungen am ursprünglichen Körper überprüfen und nötigenfalls korrigieren.
- [x] Wiederverwendbare Fusion-Prüffälle und kurzes Prüfprotokoll dokumentieren.

**Abnahme:** Baseline und bekannte Grenzen sind dokumentiert; relevante automatische Prüfungen bestehen. Erfolgreiche Erzeugung sowie ein gezielt ausgelöster Fehler wurden in Fusion geprüft oder ausdrücklich als noch offen markiert.

## M1 – Linksgewinde

**Status 27.10.2026 / 0.9.1:** implementiert, vollständige Abnahme offen. Anwender bestätigt die Funktion in Fusion nach Korrektur der negativen Umdrehungszahl. Fehlerausgabe lokalisiert; 14 automatische Tests bestanden. Einzelne Prüffälle, insbesondere gedrehte Komponenten und der vollständige Innen-/Außenvergleich, sind nicht separat bestätigt; siehe [Prüfprotokoll](pruefprotokoll-0.9.1.md). Kein Commit/PR erstellt. M2 ist in 0.9.2 implementiert; M3 ist in 0.9.3 implementiert; M4–M7 bleiben geplant.

**Funktion:** Auswahl „Rechtsgewinde / Linksgewinde“, Standard rechts.

- [x] Gewinderichtung in Parameterdaten, Helix, Profilführung und Dokumentation konsistent berücksichtigen.
- [x] Auswahl in Presets speichern; ältere Datensätze ergeben rechts.
- [ ] Rechte und linke Innen-/Außengewinde testen, auch in gedrehten Komponenten.

**Abnahme:** Passende Linksgewindepaare lassen sich in Fusion erzeugen. Rechtsgewinde bleiben geometrisch unverändert. Richtung steht im Dialog und in der Dokumentationsskizze.

## M2 – Gewindelänge und Startversatz

**Status 27.10.2026 / 0.9.2:** implementiert, Abnahme offen. 19 automatische Tests bestanden. Ganze Länge bleibt Standard; bei Teilgewinden bestimmt eine ausgewählte kreisförmige Endkante die Startseite. Sechs Fusion-Prüffälle vom Anwender bestanden, darunter beide Startseiten, Abschnittsgrenzen, Fasen und alte Presets; restliche Matrix offen, siehe [Prüfprotokoll](pruefprotokoll-0.9.2.md). Kein Commit/PR erstellt.

**Funktion:** „Ganze Länge“ bleibt Standard; alternativ Startseite, axialer Versatz und Gewindelänge wählen.

- [x] Startseite eindeutig über Stirnseite/Endkante wählen oder sichtbar umkehren.
- [x] Achsrichtung unabhängig von interner Flächenorientierung festlegen.
- [x] Gewinde auf den gewählten Abschnitt begrenzen; übrige Oberfläche erhalten (Fusion-Abnahme offen).
- [x] Negativen Versatz, Länge ≤ 0 und Überschreitung der verfügbaren Länge abfangen.
- [x] Fasen nur an tatsächlich geeigneten Endkanten zulassen; künstliche Abschnittsgrenzen nicht automatisch als Stirnkanten behandeln.
- [x] Bestehenden Helixüberlauf von der sichtbaren Gewindelänge trennen.

**Abnahme:** Beispielsweise nur 15 mm Gewinde ab 2 mm Versatz auf einem längeren Zylinder. Beide Startseiten funktionieren. Innen- und Außengewinde, Fasen und Dokumentation stimmen mit dem gewählten Bereich überein.

**Spätere Ergänzung:** Sanfter Profileinlauf, definierter Auslauf und Freistich. Diese gehören nicht zum ersten M2-Umfang und benötigen eigene Kollisions- und Wandstärkenprüfungen.

## M3 – Gewindepaar gemeinsam erstellen

**Status 27.10.2026 / 0.9.3:** implementiert, Fusion- und Druckabnahme offen. Siehe [Prüfprotokoll](pruefprotokoll-0.9.3.md). Windows-Installer 0.9.3 gebaut; kein Release veröffentlicht.

**Funktion:** Ein Außen- und ein Innengewinde in einem Auftrag mit gemeinsamen Parametern erzeugen. Die Körper dürfen nebeneinander liegen; Koaxialität ist keine Voraussetzung.

- [x] Zwei geeignete Flächen auswählen; Art und Nenndurchmesser prüfen.
- [x] Bei ungleichen Nenndurchmessern verständlich abbrechen; automatische Größenänderung zunächst nicht vorsehen.
- [x] Gemeinsame Teilung, Richtung, Profilvorgabe und Spiel verwenden. Innen-/Außentiefe im metrischen Modus weiterhin nach vorhandener Berechnung getrennt ableiten.
- [x] Längen und Startseiten pro Bauteil festlegen.
- [x] Spielverteilung anbieten: gleichmäßig / nur Innengewinde / nur Außengewinde.
- [x] Einseitig den vollen radialen Spielwert am gewählten Bauteil anwenden; die Gegenseite bleibt ohne Spielkorrektur. Nicht versehentlich doppeltes Gesamtspiel erzeugen.
- [x] Paarerstellung vollständig zurücknehmen, wenn ein Teil fehlschlägt.

**Abnahme:** Gesamtspiel entspricht rechnerisch der Eingabe bei allen drei Verteilungen. Ein gemeinsam erzeugtes Paar besteht die Fusion-Prüfung und mindestens einen dokumentierten Druckversuch. „Gleiche Profilvorgabe“ darf nicht mit identischen Innen-/Außentiefen verwechselt werden.

## M4 – Kalibrierungsassistent und Druckprofile

**Erweiterung 29.10.2026 / 0.9.7:** ein eigenes Außen-/Innengewindepaar pro Spielwert, wählbare Verteilung (Standard gleichmäßig) und optionale vertiefte Stirnflächenmarkierung auf beiden Partnern. 89 automatische Tests bestanden. Fusion- und Druckabnahme offen; siehe [Prüfprotokoll 0.9.7](pruefprotokoll-0.9.7.md). Die folgende 0.9.4-Beschreibung dokumentiert den früheren Umfang.

**Status 29.10.2026 / 0.9.4:** implementiert im eigenen Dialogreiter **Kalibrierung**, Fusion- und Druckabnahme offen. 30 automatische Tests bestanden. Erste Probengeometrie: metrisches 60°-Profil ohne Verrundung/Fasen. Zuordnung über Komponente und Körpernamen; keine erhabenen Beschriftungen. Druckprofile getrennt von Geometrie-Presets, gemeinsamer Schema-2-Transfer mit Schema-1-Migration. Siehe [Prüfprotokoll](pruefprotokoll-0.9.4.md).

**Funktion:** Kleine Gewindeproben mit variierendem Spiel erzeugen und das beste Ergebnis wiederverwenden.

- [x] Nenndurchmesser, Teilung, Richtung, kurze Testlänge und Spielreihe festlegen.
- [x] Ersten Umfang begrenzen: ein Referenzzapfen ohne Spielkorrektur plus mehrere Prüfringe mit vollständigem Spiel auf der Innenseite. Übertragung auf andere Verteilungen dokumentiert; praktische Prüfung offen.
- [x] Proben platzieren, sinnvoll benennen und mit Spielwert/ID zuordnen; Beschriftung darf die Passflächen nicht beeinflussen.
- [x] Druckprofile getrennt von Geometrie-Presets verwalten: Name, Drucker, Material, Düse, Schichthöhe, Orientierung, Spielverteilung, Spiel und Notiz.
- [x] Optionalen Gültigkeitsbereich für Durchmesser/Teilung erfassen; keine universelle Passung aus einem Test ableiten.
- [x] Druckprofil anwenden, ohne unbemerkt Profilform oder Teilung eines Gewinde-Presets zu ersetzen.
- [x] Profil-Import/-Export in die bestehende versionierte Datenverwaltung integrieren.

**Abnahme:** Eine Serie, beispielsweise mit 0,10 / 0,15 / 0,20 / 0,25 / 0,30 mm radialem Gesamtspiel, ist eindeutig zuordenbar. Ein getestetes Profil lässt sich speichern und erneut anwenden. Dokumentierter Druckversuch belegt den Workflow; Beispielwerte sind keine garantierten Empfehlungen.

## M5 – Größenhilfe und Vorschau

**Status 29.10.2026 / 0.9.5:** implementiert, vollständige Fusion-Abnahme offen. Anwender bestätigt Anzeige und Aktualisierung der Vorschau bei Formularänderungen sowie die Funktion „Metrische Größe übernehmen“ und das Entfernen der Vorschau beim Abbrechen. Auch die Paarvorschau ist durch den Anwender bestätigt und mit Screenshots dokumentiert. Begrenzte metrische Auswahl M3–M36 mit Regel-/Feingewindesteigungen aus Bossard-Tabellen, Durchmesserwarnung ohne Skalierung und optionale temporäre Linienvorschau. 44 automatische Tests bestanden. Vollständige Sweep-Vorschau nicht enthalten. Siehe [Umfang und Quelle](groessenhilfe-0.9.5.md) und [Prüfprotokoll](pruefprotokoll-0.9.5.md). Kein Installer gebaut.

**Funktion:** Weniger Eingabefehler und bessere Kontrolle vor dem Erzeugen.

- [x] Metrische Nenngrößen mit Regel-/Feingewindesteigungen aus nachvollziehbarer Quelle anbieten.
- [x] Flächendurchmesser mit der gewählten Größe vergleichen; bei Abweichungen warnen, nicht stillschweigend skalieren.
- [x] Auswahlhilfe klar von einer Zusicherung normgerechter Gewinde unterscheiden.
- [x] Zuerst leichte Vorschau für Bereich, Richtung und Profil; vollständige Sweep-Vorschau bleibt eine spätere Option.
- [x] Vorschau aktualisieren/verwerfen, ohne das Modell dauerhaft zu verändern (Fusion-Abnahme offen).

**Abnahme:** Gültige Größen-/Steigungskombinationen werden konsistent übernommen. Richtungs- und Bereichsfehler sind vor der Erstellung erkennbar. Referenzfälle mit Laufzeiten dokumentieren; keine erfundene allgemeine Zeitgrenze verwenden.

## M6 – Nachträgliche Bearbeitung

**Status 29.10.2026 / 0.9.6:** in Arbeit. Erste Stufe implementiert: Dokument-Metadaten für neue Gewinde und eigener Reiter **Gewindedaten prüfen** mit lesender Parameter-, Referenz- und Timeline-Prüfung. 83 automatische Tests bestanden. Richtungswechsel und kompakter Dialog vom Anwender bestätigt. Stabile Gewinde-IDs, neue gegenseitige Paarzuordnung und gemeinsame Bearbeitung des finalen Paares implementiert und vom Anwender bestätigt; Speichern/Öffnen, Undo/Redo und konkrete Parameterkombinationen bleiben separat zu prüfen. Begrenzte dauerhafte Bearbeitung des letzten Gewindes mit vollständigem Feature-Nachweis implementiert; Fusion-Abnahme einschließlich Undo/Redo offen. Optionale Teständerungen an Spiel/Steigung und Teilgewindelänge/-versatz implementiert, stets mit vollständiger Rücknahme; Anwender bestätigt vorläufig die kurzfristig sichtbare Steigungsänderung. Vollständige Rücknahme und weitere Parameteränderungen bleiben separat zu prüfen. Ursprungsbezugstest einschließlich Parameterprüfung und Timeline-Wiederherstellung durch Anwender bestätigt. Temporärer Test-Neuaufbau mit unveränderten Parametern und absichtlicher vollständiger Rücknahme implementiert und vom Anwender vorläufig als erfolgreich bewertet; das ursprüngliche Gewindepaar ist anschließend sichtbar. Detailprüfungen von Timeline, Metadaten und Folgeabhängigkeiten bleiben offen. Anwender bestätigt das Finden der Gewindedaten auch bei mehreren Gewinden in derselben Konstruktion. Ältere Datensätze ohne Feature-Nachweis und Gewinde mit späteren Features bleiben von dauerhafter Bearbeitung ausgeschlossen. Der Machbarkeitsnachweis für Bezugserhaltung und kontrollierten Neuaufbau in Fusion bleibt offen. Siehe [Machbarkeitsstand](bearbeitung-machbarkeit-0.9.6.md) und [Prüfprotokoll](pruefprotokoll-0.9.6.md). Kein Installer gebaut.

**Funktion:** „PrintThread-Gewinde bearbeiten“ lädt ursprüngliche Einstellungen und baut das Gewinde kontrolliert neu auf.

- [ ] Zunächst Machbarkeitsnachweis erstellen: Dokumentattribute, Bezugserhaltung, Timeline-Position und geeigneter Fusion-Feature-Mechanismus untersuchen.
- [ ] API-Verfügbarkeit und Verhalten in der eingesetzten Fusion-Version prüfen, bevor ein bestimmter Mechanismus festgelegt wird.
- [x] Parameter maschinenlesbar am Dokument/Feature speichern, zusätzlich zur lesbaren Dokumentationsskizze (implementiert; Fusion-Persistenzprüfung offen).
- [ ] Erst neue Gewinde als bearbeitbar kennzeichnen. Alte Gewinde ohne verlässliche Metadaten nicht automatisch rekonstruieren.
- [ ] Referenzen nach Speichern/Öffnen und Komponentenänderungen wiederfinden oder verständlich als ungültig melden.
- [ ] Scheiternden Neuaufbau zurücknehmen; ursprüngliches Gewinde erhalten.
- [ ] Abhängige spätere Features berücksichtigen und Grenzen dokumentieren.

**Abnahme:** Spiel, Teilung und Länge lassen sich in einem Referenzmodell nach Speichern und erneutem Öffnen ändern. Nachfolgende Features, Undo/Redo und fehlerhafter Neuaufbau sind geprüft. Ein PoC allein gilt nicht als vollständige Bearbeitungsfunktion.

## M7 – Erweiterte Gewinde

### M7a: Mehrgängigkeit

- [ ] Gangzahl als positive ganze Zahl; Standard 1.
- [ ] Teilung P und Leitweg L in Daten, UI und Dokumentation trennen: L = n × P.
- [ ] Gänge mit Winkelversatz 360°/n erstellen; Selbstüberschneidung und Stirnabschlüsse prüfen.
- [ ] Alte Daten migrieren, ohne `pitch` stillschweigend umzudeuten.

**Abnahme:** Zwei- und dreigängige Paare sind geometrisch korrekt; beispielsweise n=3, P=2 mm, L=6 mm. Mindestens ein gedruckter Verschluss wird getestet.

### M7b: Alternative Profile

- [ ] Zunächst eine klar definierte Trapezprofil-Vorgabe implementieren.
- [ ] Profiltyp von einzelnen Profilmaßen trennen; freies bisheriges Profil erhalten.
- [ ] Flanken-, Kopf- und Grundbreiten sowie Verrundungen validieren.
- [ ] Sägezahn-/Rundprofile erst anschließend aufnehmen; bei asymmetrischem Profil Belastungsrichtung und Einbaurichtung sichtbar machen.

**Abnahme:** Passendes Innen-/Außenprofil und Grenzen sind dokumentiert. Tragfähigkeit wird nicht aus der Profilbezeichnung abgeleitet.

## Backlog nach den Kernfunktionen

| Idee | Voraussetzung / Abgrenzung |
| --- | --- |
| Mehrfachauswahl gleichartiger Flächen | Stabile Fehlerbehandlung, Komponentenbezüge, gemeinsame und individuelle Parameter |
| Konische Gewinde | Eigene Geometrie- und Referenzdefinition; kein kleiner Zusatz zur Zylinderunterstützung |
| Verschluss-/Behältervorlagen | Auf Paarerstellung aufbauen; separater Assistent |
| Einstellbare Startphase | Winkelbezug für definierte Deckelstellung; Endlage zusätzlich von Einschraubtiefe abhängig |
| Passungsprüfung in Fusion | Geometrische Überschneidung ist kein Nachweis der Druckpassung |
| Druckorientierungs-Hinweise | Konkrete geometrische Hinweise, keine Festigkeitsgarantie |

## Fortschritt pflegen

Zu jedem Meilenstein Status, zugehörigen Commit/PR, automatische Prüfungen, Fusion-Version/Plattform und gegebenenfalls Drucktest ergänzen. Zulässige Zustände: geplant, in Arbeit, implementiert/Abnahme offen, abgeschlossen, zurückgestellt. Ein Meilenstein wird erst nach seinen Abnahmekriterien abgeschlossen. Nächster Schritt ist die Fusion- und Druckabnahme von M3; übrige M2-Prüffälle bleiben offen. M4 benötigt einen eigenen Auftrag; noch offene M0-/M1-Prüffälle bleiben im jeweiligen Prüfprotokoll erfasst.
