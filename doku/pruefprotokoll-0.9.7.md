# Prüfprotokoll 0.9.7 – Kalibrierungspaare und eingeprägte Spielwerte

Stand: 29.10.2026. Implementiert; Fusion- und Druckabnahme offen.

## Geändertes Verhalten

Ein eigener Außen-/Innengewindepartner pro Spielwert statt eines gemeinsamen
Referenzzapfens. Fünf Werte ergeben zehn Körper in zwei Reihen. Standard ist
gleichmäßige Verteilung, alternativ nur innen oder nur außen. Beide Partner
erhalten denselben radialen Gesamtspielwert; die Radiuskorrekturen werden
weiterhin nach der vorhandenen Verteilungsregel berechnet.

Optionale Stirnflächengravur, standardmäßig aktiv: beim Zapfen innerhalb des
Gewindekerns, beim Ring auf dem äußeren Stirnflächenmaterial. Auf beiden steht
z. B. `0.15` für 0,15 mm radiales Gesamtspiel. Vorgaben: 1,2 mm Schrift,
0,3 mm Tiefe. Geplantes Textrechteck und echte Textgrenzen werden gegen einen
konservativen Materialbereich geprüft. Zu große oder zu tiefe Markierungen
werden abgewiesen, nicht auf Passflächen verschoben.

## Automatisch

89 Tests bestanden mit lokalem Fusion-Python. Bestehende Serienprüfungen auf
die neue Paarstruktur aktualisiert; alle übrigen bisherigen Prüfungen erhalten.
Sechs zusätzliche Tests prüfen:

- nicht überlappende Paaranordnung und eindeutige Spielwerttexte,
- sichere Beschriftungsbereiche für beide Arten und alle drei Verteilungen,
- unzulässige Schrift-/Prägetiefen, zu kleine Kerne und nicht unterscheidbare Werte,
- Eingabe mit Punkt/Komma und ungültige Texte,
- Textschnitt nur am Zielkörper und Ablehnung zu großer tatsächlicher Textgrenzen,
- beide Partner pro Wert, identisches Gesamtspiel, gegenseitige Paar-IDs,
  zuerst beide Rohlinge und anschließend beide Gewinde, Prägung auf beiden oder
  Abschaltung der gesamten Beschriftung.

Die Tests erzeugen keine echten Fusion-Körper oder physische Druckproben.

## In Fusion zu prüfen

Fusion-Version/Plattform für diesen Lauf noch zu erfassen.
Kein interaktiver Test der neuen Paarserie oder Prägung durchgeführt.

| Fall | Erwartung | Status |
| --- | --- | --- |
| Ø20, P2, Länge 8, Wand 3 mm, fünf Werte 0,10–0,30 mm | Fünf Zapfen und fünf Ringe, jeweils korrekt zugeordnet | Offen |
| Gleichmäßig / nur innen / nur außen | Radiusdifferenz entspricht Gesamtspiel; beide Partner gemäß Auswahl korrigiert | Offen |
| Rechts und links | Beide Partner gleiche Richtung, passende Profilphase | Offen |
| Prägung Standard | Lesbarer Spielwert auf beiden oberen Stirnflächen, 0,3 mm vertieft | Offen |
| Kleine Schrift / große Schrift / dünne Ringwand | Sichere Erzeugung oder verständliche Ablehnung ohne Gewindeeingriff | Offen |
| Prägung abschalten | Alle Paare ohne Textschnitt; Körpernamen erhalten | Offen |
| Fehler bei Schrift oder zweitem Partner | Keine unvollständige Serie oder Restkomponente | Offen |
| Abbrechen, Undo/Redo | Komplette Serie gemeinsam rücknehmbar/wiederherstellbar | Offen |
| Profil nach Änderung der Serienverteilung speichern | Gleiche Verteilung vorgewählt; alte Profile nicht überschrieben | Offen |
| Slicer-Export | Zehn getrennte Körper und tatsächliche vertiefte Geometrie, nicht nur Skizzentext | Offen |

## Druckversuch

Offen. Drucker, Material, Düse, Schichthöhe, Orientierung, Nenndurchmesser,
Steigung und Spielverteilung festhalten. Jedes Teil mit dem gleich markierten
Partner prüfen. Lesbarkeit und Druckbarkeit der vertieften Ziffern dokumentieren.
Das beste Ergebnis mit derselben Verteilung als Druckprofil speichern. Andere
Druckbedingungen oder Profilgeometrien erneut prüfen.

## API und Kompatibilität

Text wird über `SketchTexts.createInput3` und `setAsMultiLine` definiert und
als `SketchText` in einem Extrusionsschnitt verwendet, mit auf den jeweiligen
Körper begrenzter `participantBodies`-Liste. Die Schnittrichtung wird aus der
tatsächlichen Skizzenorientierung abgeleitet.

Primärquellen:
[SketchTexts](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SketchTexts.htm),
[MultiLine-Text](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SketchTextInput_setAsMultiLine.htm),
[Extrusionsprofil einschließlich SketchText](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_ExtrudeFeatures_createInput.htm).

Preset-/Profilschema 2 bleibt unverändert. Bestehende Innen-Kalibrierprofile
werden nicht umgedeutet; ihre gespeicherte Verteilung bleibt erhalten.
Kalibrierungsproben mit Gravur besitzen zusätzliche nachfolgende Features und
sind damit von der begrenzten Gewindebearbeitung ausgeschlossen; bei Bedarf
die Serie neu erzeugen. Ältere Screenshots sind in README DE/EN als historisch
gekennzeichnet. Version, Manifest und Installer-Konfiguration 0.9.7; kein
Installer gebaut.
