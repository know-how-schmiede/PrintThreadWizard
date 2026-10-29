# Prüfprotokoll 0.9.5 – M5 Größenhilfe und Vorschau

Stand: 29.10.2026. Implementiert, Fusion-Abnahme offen.

## Automatisch

44 Tests bestanden mit lokalem Fusion-Python. Die 36 bisherigen Tests bleiben
erhalten. Neue Prüfungen: nachvollziehbare Größen-/Steigungskombinationen und
cm-Umrechnung, Warnschwellwert, Vorschaugrenzen und Profilkoordinaten,
gespiegelte Richtung, begrenzte Geometriekosten auch bei langen Gewinden,
Größenanwendung ohne Änderung anderer Eingaben und Entfernen der temporären
Grafiken bei Fehlern, Dialogende und erfolgreichem Abschluss. Auch die Warnung
für einen abweichenden zweiten Partner wird geprüft. Texte und Platzhalter werden
weiterhin in allen sechs Sprachen geprüft.

Die Tests belegen weder die tatsächliche Sichtbarkeit der Custom Graphics
noch deren korrekte Darstellung in einer laufenden Fusion-Sitzung.

Anwenderlauf: Vorschau wird kurz gezeichnet und verschwindet nach etwa einer
halben Sekunde, obwohl der Dialog weiterhin Erfolg meldet. Korrektur: Aufbau
aus inputChanged in executePreview verschoben, passend zu Fusions
Vorschau-Transaktion. isValidResult bleibt False, damit OK weiterhin die echte
Geometrie erstellt. Linien verwenden einen Show-through-Farbeffekt, damit
spielkorrigierte Radien unterhalb der ursprünglichen Fläche sichtbar bleiben.
Zusätzlicher Regressionstest prüft die Trennung von Eingabe und Grafikaufbau
sowie die weiterhin erforderliche echte Ausführung. Anwender bestätigt nach
der Korrektur: Vorschau wird angezeigt und bei Änderungen im Formular
aktualisiert. Kein Installer erstellt.

## In Fusion zu prüfen

Anwenderprüfung in Fusion: Anzeige und Aktualisierung der Vorschau bestätigt.
Auch „Metrische Größe übernehmen“ funktioniert laut Anwender. Die konkret
geprüften Größen und Steigungen wurden nicht genannt.
Der Anwender bestätigt außerdem: Beim Abbrechen wird die Vorschau entfernt.
Die paarweise Vorschau wurde ebenfalls bestätigt. Die Screenshots zeigen die
[Vorschau beider Partner](../images/29-10-2026_12-47-57.png) mit Linksgewinde,
metrischem Modus und 10 mm Steigung sowie das
[erzeugte Gewindepaar](../images/29-10-2026_12-51-17.png).
Genaue Fusion-Version noch nicht erfasst; die übrigen Prüffälle bleiben offen.

| Fall | Erwartung | Status |
| --- | --- | --- |
| Vorschau anzeigen und Formularwerte ändern | Vorschau bleibt sichtbar und wird aktualisiert | Durch Anwender bestätigt |
| Metrische Größe übernehmen | Gewählte metrische Vorgabe wird übernommen | Durch Anwender bestätigt; konkrete Kombination nicht erfasst |
| M8 × 1,25 / M8 × 1,0 übernehmen | Metrischer Modus und gewählte Steigung; Durchmesser unverändert | Offen |
| 10-mm-Fläche mit M8-Auswahl | Warnung, keine Skalierung; Erstellung mit tatsächlichem Durchmesser möglich | Offen |
| Paar, nur zweiter Durchmesser abweichend | Auch zweite Fläche erzeugt Warnung | Offen |
| Preset laden / manuelle Steigung ändern | Gespeicherte Werte bleiben maßgeblich; Auswahlhilfe manuell bzw. Abweichung gemeldet | Offen |
| Vorschau, 40-mm-Zylinder, 2-mm-Versatz, 15-mm-Länge | Cyan zeigt genau den gewählten Bereich | Offen |
| Beide Startseiten, Innen/Außen, links/rechts | Bereich und Richtung erkennbar; magenta Profilhülle plausibel | Offen |
| Gedrehte/verschobene sowie verschachtelte Instanz | Linien liegen auf der gewählten Instanz | Offen |
| Paarvorschau | Beide Partner korrekt dargestellt | Durch Anwender bestätigt; Screenshots dokumentiert |
| Vorschau abschalten / ungültige Werte / Kalibrierung aktivieren | Keine Grafiken bleiben stehen | Offen |
| Abbrechen | Vorschau wird entfernt | Durch Anwender bestätigt |
| Erstellen, absichtlicher Grafikfehler | Keine Vorschauhilfen in Modell oder Timeline | Offen |
| Vorschaufehler | Nur Vorschau betroffen; Erstellung weiterhin möglich | Offen |
| Kleine Steigung mit bisher großem Radius | Bestehende Profilvalidierung meldet Fehler; nichts stillschweigend geändert | Offen |

## Laufzeit-Referenzfälle

Für jeden Fall Fusion-Version, Rechner, Grafik und angezeigte API-Aufbauzeit
erfassen. Die Zeit schließt die spätere GPU-Darstellung nicht ein. Noch keine
Messungen aus Fusion verfügbar; keine erfundenen Laufzeiten angeben.

| Fall | Parameter | API-Aufbauzeit |
| --- | --- | --- |
| Einzelgewinde | Ø20, P2, Länge 8 mm | Offen |
| Langes Gewinde | Ø20, P2, Länge 100 mm | Offen |
| Teilgewindepaar | Ø30, P3, Länge je 15 mm, Versatz 2 mm | Offen |

## Kompatibilität und Auslieferung

Schema 2 bleibt unverändert. Alte Presets laden weiterhin ohne Größenhilfe
und mit ausgeschalteter Vorschau. Version, Manifest und Installer-Konfiguration
sind 0.9.5; gemäß Anwenderwunsch kein Installer gebaut.
M4-Dialog und Profilverwaltung bleiben verfügbar; eine vollständige
Fusion-/Druckabnahme der Kalibrierung wird daraus nicht abgeleitet.
