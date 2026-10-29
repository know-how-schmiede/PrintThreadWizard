# Prüfprotokoll 0.9.6 – M6-Datenbasis und Bezugsprüfung

Stand: 29.10.2026. Erste M6-Stufe implementiert, Fusion-Prüfung offen.
Keine nachträgliche Bearbeitungsfunktion freigegeben.

## Automatisch

65 Tests bestanden mit lokal installiertem Fusion-Python. 44 bisherige Tests
plus sechs neue Prüfungen: exakter Metadaten-Rundlauf ohne Live-Objekte,
unbekannte Schemata und ungültige Werte, Erfassen vor Topologieänderungen,
Zuordnung von Skizzen-/Ergebnisattributen, mehrdeutige oder nicht auflösbare
Bezüge, lesende Timeline-Auswertung und isolierte Meldung beschädigter
Datensätze. Lokalisierung in sechs Sprachen und Versionskonsistenz geprüft.

Weitere fünf Tests für den expliziten Ursprungsbezugstest: Marker und
zugeklappte Gruppe wiederherstellen, Wiederherstellung nach Prüfausnahme,
mehrdeutige Fläche ablehnen, fehlgeschlagenes Zurückrollen behandeln und
Testaktion ohne Gewindeerzeugung ausführen. Diese Aktion läuft ausschließlich
in execute, nicht in inputChanged oder executePreview.

Anwenderlauf des Bezugstests: Zielkörper und ursprüngliche Fläche werden
eindeutig gefunden; Komponentenbezug bleibt nicht auflösbar, Timeline wird
wiederhergestellt. Korrektur: Wenn nur der Komponententoken keinen Treffer
liefert, wird die tatsächliche Eigentümerkomponente des eindeutig aufgelösten
Zielkörpers verwendet. Keine pauschale Annahme der Root-Komponente; mehrdeutige
Körper oder Komponententreffer werden nicht automatisch reduziert. Zwei neue
Regressionen prüfen diesen Pfad und die unveränderte Timeline-Wiederherstellung.
Der Anwender bestätigt anschließend den erfolgreichen Bezugstest: Komponente,
Zielkörper und ursprüngliche Fläche werden eindeutig gefunden, Parameter am
ursprünglichen Körper validiert und Timeline wiederhergestellt. Weitere
Varianten einschließlich Teilgewinde/Fasen bleiben separat zu prüfen.

Vier zusätzliche Regressionen für den Test-Neuaufbau: gespeicherte Parameter
unverändert verwenden, keine Timeline-Gruppe über spätere Features bilden,
Erzeugungs-/Validierungsfehler weiterreichen und nach erfolgreichem Aufbau
zwingend executeFailed zur Rücknahme setzen.

Anwender bewertet den Test-Neuaufbau als vorläufig erfolgreich („scheint zu
funktionieren“). Der Screenshot zeigt zwei erfolgreiche Test-Neuaufbau-Meldungen
und anschließend das ursprüngliche Außen-/Innengewindepaar. Die sichtbare
Geometrie ist damit vorläufig bestätigt; identische Timeline-Einträge,
Metadatenbestand und nachfolgende Abhängigkeiten sind nicht separat geprüft.

Nächste Stufe implementiert: optionale Teständerungen an Spiel und Steigung,
bei gespeicherten Teilgewinden zusätzlich Versatz/Länge mit erhaltener
Startkante. Metrische Tiefen werden bei Steigungsänderungen neu berechnet;
freie Tiefe, Richtung und Spielverteilung bleiben erhalten. Vier weitere Tests
prüfen unveränderte Originaldaten, getrennte metrische Innen-/Außentiefe,
Längen-/Wertevalidierung und Weitergabe geänderter Werte an den Generator.
Keine dauerhafte Übernahme; der vollständige Rollback bleibt obligatorisch.

Anwender bewertet den Test mit geänderter Steigung als vorläufig erfolgreich:
Die Steigung wurde kurzfristig sichtbar geändert. Konkrete Werte und
Berechnungsmodus wurden nicht genannt. Die vollständige Rücknahme einschließlich
Timeline und Metadaten sowie Spiel-/Längenänderungen sind separat zu bestätigen.

Die API-Grenztests belegen keine tatsächliche Fusion-Dateipersistenz oder
erfolgreiche Wiederherstellung ursprünglicher Flächen.

## Fusion-Matrix

Lokal installierte Produktversion laut EXE: 2706.1.14, Windows.
Anwender bestätigt: Gewindedaten werden gefunden, auch bei mehreren in
derselben Konstruktion erstellten Gewinden. Speichern/Schließen/Wiederöffnen
und die genaue Prüfung der einzelnen Modellbezüge sind damit noch nicht
separat bestätigt.

| Fall | Erwartung | Status |
| --- | --- | --- |
| Mehrere Gewinde in derselben Konstruktion | Gespeicherte Gewindedaten werden gefunden | Durch Anwender bestätigt |
| Ursprungsbezüge mit OK prüfen | Ursprungsfläche vor der Erzeugung auflösen, Parameter validieren, Timeline wiederherstellen | Durch Anwender bestätigt; zusätzliche Kanten-/Instanzfälle offen |
| Neuaufbau mit OK testen und zurücknehmen | Temporären Neuaufbau erzeugen; Befehl auch nach Erfolg vollständig zurücknehmen; altes Gewinde erhalten | Vorläufig durch Anwender bestätigt; sichtbares Gewindepaar erhalten, Detailprüfung offen |
| Test-Neuaufbau mit geänderter Steigung | Neue Steigung im temporären Aufbau sichtbar | Vorläufig durch Anwender bestätigt; konkrete Werte/Modus nicht erfasst |
| Geändertes Spiel und metrische Tiefenberechnung | Geänderte Werte korrekt anwenden, Tiefe passend zur neuen Steigung | Offen |
| Rücknahme nach geändertem Test-Neuaufbau | Originalgeometrie, Timeline und Metadaten vollständig wiederhergestellt | Offen |
| Test-Neuaufbau eines Teilgewindes mit geänderter Länge / Versatz | Bestehende Startkante behalten, Abschnittsgrenzen und Fasen prüfen, danach zurücknehmen | Offen |
| Anderen Datensatz auswählen | Originalwerte laden; Teständerungen deaktivieren | Offen |
| Test-Neuaufbau bei mehreren Gewinden | Nur ausgewählten Ursprungskörper vorübergehend ändern; nach Rücknahme alle ursprünglichen Features und Datensätze erhalten | Offen |
| Bezugstest bei mehreren Gewinden und nachfolgenden Features | Nur gewählten Datensatz prüfen; Konstruktion nach dem Test unverändert | Offen |
| Bezugstest mit geschlossenem Timeline-Ordner / Marker nicht am Ende | Gruppen und ursprüngliche Markerposition nach Erfolg und Fehler wiederhergestellt | Offen |
| Neues metrisches und freies Gewinde | Datensatz vorhanden, Modus und Parameter exakt | Offen |
| Alte Gewinde aus 0.9.5 oder früher | Keine automatische Rekonstruktion oder Bearbeitbarkeitsmarkierung | Offen |
| Neues Paar und Kalibrierungsserie | Datensatz pro Gewinde einschließlich korrektem Modus | Offen |
| Teilgewinde, Fasen, Linksgewinde und einseitiges Spiel | Einstellungen und zugehörige Tokens erfasst | Offen |
| Speichern, schließen, erneut öffnen | Parameter, ID und Ergebnisbezug bleiben auffindbar | Offen |
| Instanz verschieben/drehen | Komponenten-/Instanzbezüge bleiben nachvollziehbar | Offen |
| Zusätzliche nachfolgende Features | Neue Timeline-Positionen werden gelesen; spätere Einträge werden gemeldet | Offen |
| Ausgangsfläche nach Gewindeschnitt nicht auflösbar | Klare Meldung, kein automatischer Neuaufbau | Offen |
| Geteilte Fläche, mehrere Token-Treffer | Mehrdeutigkeit statt willkürlicher Auswahl | Offen |
| Beschädigter/zu neuer Datensatz | Meldung nur für diesen Eintrag; übrige Einträge bleiben lesbar | Offen |
| Aktualisieren, Prüfen, Abbrechen | Modell und Timeline-Marker unverändert | Offen |
| Erstellungsfehler, Undo/Redo | Metadaten und Features gemeinsam zurückgenommen/wiederhergestellt | Offen |

Ein temporärer Test-Neuaufbau mit gespeicherten oder geänderten Testparametern ist implementiert.
Er übernimmt keine Bearbeitung: Nach jedem Versuch wird die gesamte
Befehls-Transaktion zurückgenommen. Ein dauerhaft übernehmbarer Neuaufbau und
sein Fehler-/Undo-Verhalten sind **noch nicht implementiert**.
Dafür sind die Nachweise im
[Machbarkeitsdokument](bearbeitung-machbarkeit-0.9.6.md) erforderlich.

Version, Manifest und Installer-Konfiguration: 0.9.6. Kein Installer gebaut.
