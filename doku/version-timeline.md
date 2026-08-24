# Version Timeline

## 0.7.13 - 2026-08-24

- Dialogbezeichnungen um die technischen Kurzzeichen `P`, `h`, `r` und `α` ergänzt.
- Ergebnisanzeige um Außendurchmesser `d`, Teilkreisdurchmesser `d2`, Innendurchmesser `d1` und Gewindebohrung `T` erweitert.
- Eigene technische Gewindezeichnung mit den Maßbezeichnungen als Dialoggrafik ergänzt.
- Editierbare SVG-Quelle und die von Fusion benötigte PNG-Fassung der Grafik hinterlegt.
- Version in `version.py` und im Fusion-Manifest auf `0.7.13` gesetzt.

## 0.7.12 - 2026-08-24

- Dialog in die Reiter `Gewinde erstellen` und `Einstellungen verwalten` aufgeteilt.
- Alphabetisch sortierte Auswahl der gespeicherten Einstellungen direkt unter den Fasen-Kanten ergänzt.
- Auswahl eines Presets übernimmt Berechnungsmodus, Flankenwinkel, Gewindetiefe, Steigung, Verrundungsradius und Toleranz.
- Speicherfunktion im Reiter `Gewinde erstellen` angeordnet; der Verwaltungs-Reiter zeigt die gespeicherten Einstellungen und ihre Metadaten an.
- Version in `version.py` und im Fusion-Manifest auf `0.7.12` gesetzt.

## 0.7.11 - 2026-08-24

- Dialog um Gewindebezeichner, kurze Notiz und einen Button zum Speichern der aktuellen Einstellungen ergänzt.
- Wiederverwendbare Gewindeeinstellungen als versionierte JSON-Liste im benutzerspezifischen Anwendungsdatenordner gespeichert.
- Persistentes Datenformat für die spätere Verwaltung, Auswahl sowie den Import und Export vorbereitet.
- Speicherbutton greift auch aus seiner Dialoggruppe auf die vollständige Eingabesammlung zu.
- Version in `version.py` und im Fusion-Manifest auf `0.7.11` gesetzt.

## 0.7.10 - 2026-08-23

- Dropdown `Toleranz` mit radialem Gesamtspiel von 0,0 bis 0,5 mm ergänzt; Standardwert ist 0,2 mm.
- Gewählte Toleranz hälftig auf das zusammengehörige Gewindepaar verteilt: Außenzylinder wird radial verkleinert und Innenbohrung radial vergrößert.
- Gesamte Gewindegeometrie einschließlich Flanken, Spitzen und zylindrischer Flächen auf dem tolerierten Radius aufgebaut; Profiltiefe bleibt unverändert.
- Wirksamen Kerndurchmesser einschließlich Toleranz im Ergebnisfeld angezeigt.
- Englische README auf den tatsächlichen Funktionsumfang, Installation, Bedienung, Toleranzmodell und Einschränkungen aktualisiert.
- Vollständige deutsche Dokumentation als `README_DE.md` ergänzt und beide Sprachfassungen miteinander verlinkt.
- Version in `version.py` und im Fusion-Manifest auf `0.7.10` gesetzt.

## 0.7.9 - 2026-08-23

- Fasenwinkel aus dem halben Flankenwinkel abgeleitet; bei 60° Flankenwinkel wird damit eine 30°-Fase erzeugt.
- Radiale Fasenbreite weiterhin aus der Gewindetiefe berechnet und die axiale Länge passend zum Winkel bestimmt.
- Helix des Außengewindes wie beim Innengewinde um je eine volle Windung über beide Deckflächen hinaus verlängert.
- Verlängerte zylindrische Sweep-Führungsfläche nun für Innen- und Außengewinde verwendet.
- Rotierte Außengewinde-Fase spiegelbildlich zur Innengewinde-Fase mit 0,1 mm Schneidüberdeckung ausgeführt.
- Alle von einem Plugin-Aufruf erzeugten Features in der Konstruktionshistorie als eingeklappte Gruppe `PrintThread Wizard – Gewinde` zusammengefasst.
- Version in `version.py` und im Fusion-Manifest auf `0.7.9` gesetzt.

## 0.7.8 - 2026-08-23

- Kontur des rotierten Fasenprofils beim Innengewinde korrigiert: Die Fase beginnt an der Deckfläche am Nenndurchmesser und läuft axial zum Kerndurchmesser aus.
- Innengewinde-Fasenkörper radial und axial um 0,1 mm über den Gewindegrund hinausgeführt, damit keine tangentialen Restflächen entstehen.
- Fehlerbereinigung für unvollständig erzeugte Fasen-Skizzen und Konstruktionsebenen ergänzt.
- Zeilenumbrüche im Ergebnisfeld des Dialogs von HTML-Tags auf echte Zeilenumbrüche umgestellt.
- Veralteten Entwicklungsstatus und die nicht mehr zutreffende Verzeichnisstruktur in der README aktualisiert.
- Repository mit Fusion-Python auf Syntaxfehler sowie Manifest, Versionskonsistenz und Patch-Format geprüft.
- Version in `version.py` und im Fusion-Manifest auf `0.7.8` gesetzt.

## 0.7.7 - 2026-08-23

- Innengewinde-Helix um jeweils eine volle Windung über beide Deckflächen hinaus verlängert.
- Begrenzte Bohrungsfläche durch eine ebenso verlängerte zylindrische Sweep-Führungsfläche ersetzt.
- Innengewinde zunächst als separaten Sweep-Körper erzeugt.
- Empfindliche Trennung an einzelnen Deckflächen durch eine robuste axiale Schnittmenge ersetzt.
- Verlängerten Sweep-Körper mit einem exakt zwischen den Deckflächen liegenden Hilfszylinder begrenzt.
- Erst den vollständig beschnittenen Gewindekörper mit dem Grundkörper verbunden.
- Aufräumen bereits erzeugter Sweep-, Hilfs- und Begrenzungsfeatures im Fehlerfall ergänzt.
- Helixpfad und verlängerte Sweep-Führungsfläche unmittelbar über ihre Browser-Lampen ausgeblendet.
- Vorgelagerte Kantenfase durch einen abschließenden 360°-Rotationsschnitt ersetzt.
- Ausgewählte Kreispositionen vor der Gewindeerzeugung gespeichert und danach als dreieckige Fasenprofile rekonstruiert.
- Rotationsfase schneidet nach Sweep, axialer Begrenzung und Verschmelzung durch den fertigen Körper.
- Mittelpunkte ausgewählter Kreiskanten als verbindliche axiale Schnittpositionen verwendet.
- Version in `version.py` und im Fusion-Manifest auf `0.7.7` gesetzt.

## 0.7.6 - 2026-08-23

- Axiale Ausdehnung des schräg zur Helix stehenden Innengewindeprofils wird berechnet.
- Start und Ende der Innengewinde-Helix werden um die jeweilige Profilhälfte nach innen versetzt.
- Überstehendes Join-Material außerhalb der Deckflächen verhindert.
- Version in `version.py` und im Fusion-Manifest auf `0.7.6` gesetzt.

## 0.7.5 - 2026-08-23

- ISO-Automatikmodus als Standard sowie freie Geometrie als Alternative ergänzt.
- Im ISO-Modus werden Flankenwinkel und Gewindetiefe automatisch aus Steigung und erkannter Gewindeart berechnet.
- Der ausgewählte Zylinder- beziehungsweise Bohrungsdurchmesser wird als Nenndurchmesser verwendet.
- Berechneten Kerndurchmesser im Dialog ergänzt.
- Version in `version.py` und im Fusion-Manifest auf `0.7.5` gesetzt.

## 0.7.4 - 2026-08-23

- Automatische Unterscheidung zwischen Außen- und Innenflächen ergänzt.
- Innengewinde werden auf dem ausgewählten Nenn-/Fertigdurchmesser radial nach innen aufgebaut und mit dem Grundkörper verbunden.
- Fasen, exakte Helix, Zylinderführung, Flankenwinkel, Gewindetiefe und Profilverrundung werden für beide Gewindearten gemeinsam verwendet.
- Dialogausgabe zeigt die erkannte Gewindeart und Modellierungsrichtung an.
- Version in `version.py` und im Fusion-Manifest auf `0.7.4` gesetzt.

## 0.7.3 - 2026-08-23

- Optionale Fasen an den im Dialog ausgewählten Zylinderkanten ergänzt.
- Gewindetiefe wird als gleichmäßiges Fasenmaß verwendet.
- Zylinderfläche wird nach dem Anfasen neu ermittelt, damit Helix und Führungsfläche auf der aktualisierten Geometrie aufbauen.
- Version in `version.py` und im Fusion-Manifest auf `0.7.3` gesetzt.

## 0.7.2 - 2026-08-23

- Ausgewählte Zylinderfläche als Führungsfläche des Gewinde-Sweeps ergänzt.
- Radiale Ausrichtung des Schneidprofils entlang der gesamten Helix stabilisiert.
- Unregelmäßige Außenflächen durch abschnittsweise fehlende Schnittüberlappung behoben.
- Der Sweep bleibt eine direkte Schnittoperation auf dem ausgewählten Körper; ein separater Kombinationskörper wird nicht erzeugt.
- Version in `version.py` und im Fusion-Manifest auf `0.7.2` gesetzt.

## 0.7.1 - 2026-08-23

- Dialog, Parameterlogik, Zylinderanalyse und Zeichenfunktionen in getrennte Module aufgeteilt.
- Der ausgewählte Zylinderdurchmesser wird als fertiger Nenndurchmesser des Außengewindes verwendet.
- Exakte B-Rep-Helix, verrundetes Schneidprofil und Sweep-Cut für frei parametrierbare Außengewinde ergänzt.
- Eingabeprüfung für Außenflächen und geometrisch unzulässige Profilwerte ergänzt.
- Version in `version.py` und im Fusion-Manifest auf `0.7.1` gesetzt.

## 0.7 - 2026-08-23

- Neustart der Entwicklung auf einer sauberen Plugin-Basis.
- Sämtliche bisherige Geometrie-, Coil-, Helix-, Sweep- und Fillet-Logik entfernt.
- Vorhandenen Dialog als Ausgangspunkt beibehalten; das Bestätigen führt bewusst noch keine Aktion aus.
- Nicht verwendete Palette-Beispielmodule aus dem Fusion-Template entfernt.
- Version in `version.py` und im Fusion-Manifest auf `0.7` gesetzt.

## 0.6.3 - 2026-05-26

- Helix-/Gewindeerzeugung auf die native Fusion-Coil-Funktion umgestellt.
- Der bisherige Sketch-Fitted-Spline-Pfad sowie der nachgelagerte Sweep werden nicht mehr verwendet, um den bekannten verzögerten Sweep-Rebuild-Fehler zu vermeiden.
- Die Coil nutzt Steigung und Gewindetiefe aus dem Dialog und wird als neuer Körper erzeugt.
- Die Coil startet weiterhin `2 * Gewindetiefe` vor der Grundfläche und reicht entsprechend über die Deckfläche hinaus.
- Version in `version.py` und im Fusion-Manifest auf `0.6.3` erhöht.

## 0.2.2 - 2026-05-26

- Am Anfang der erzeugten Helix wird eine Konstruktionsebene auf dem Pfad erstellt.
- Auf der Profilebene wird ein geschlossenes Dreieck als späteres Sweep-Profil skizziert.
- Das Dreiecksprofil nutzt Flankenwinkel und Gewindetiefe aus dem Dialog.
- Version in `version.py` und im Fusion-Manifest auf `0.2.2` erhöht.

## 0.2.1 - 2026-05-26

- Dialogparameter für Flankenwinkel, Gewindetiefe und Steigung beibehalten.
- Beim Ausführen wird zusätzlich zur Zylinderachse eine 3D-Helix auf der ausgewählten Zylinderfläche erzeugt.
- Die Helix nutzt die im Dialog angegebene Steigung.
- Die Helix startet `2 * Gewindetiefe` vor der Grundebene und endet `2 * Gewindetiefe` hinter der Deckfläche.
- Version in `version.py` und im Fusion-Manifest auf `0.2.1` erhöht.

## 0.2.0 - 2026-05-26

- Neustart der Konstruktionslogik vorbereitet.
- Helix-, Profil-, Sweep-, Trim- und Timeline-Gruppen-Erzeugung aus dem Command entfernt.
- Dialog auf die Basisfunktion zurückgesetzt: Version anzeigen, Zylinderfläche auswählen, Durchmesser sowie Außen-/Innenfläche anzeigen.
- Version in `version.py` und im Fusion-Manifest auf `0.2.0` erhöht.

## 0.1.6 - 2026-05-26

- Sweep-Führungsfläche auf die ausgewählte Zylinderfläche umgestellt, damit der Sweep den kompletten Helixpfad zuverlässig verwendet.
- Erfolgsmeldung von modaler MessageBox auf Textbefehle-Logging umgestellt, damit der Fusion-Mauszeiger nach dem Command wieder korrekt freigegeben wird.
- UI-Reset nach Sweep und Command-Ende ergänzt.
- Abschneidelogik für überstehende Gewindeenden auf einen temporären Schnittkörper und `Combine Intersect` umgestellt, damit der Sweepkörper auf die echte Zylinderhöhe begrenzt wird.
- Trim-Logging erweitert, inklusive Schnittkörperdaten und Boolean-Ergebnis.
- Version in `version.py` und im Fusion-Manifest auf `0.1.6` erhöht.

## 0.1.5 - 2026-05-26

- Optionsfeld `Ganze Fläche` ergänzt.
- Wenn `Ganze Fläche` aktiv ist, wird die eingegebene Gewindelänge ignoriert und die Helix über die komplette Zylinderfläche erzeugt.
- Die Helix startet um eine Steigung vor der Grund- bzw. Deckfläche und endet um eine Steigung hinter der gegenüberliegenden Fläche, damit der Sweepkörper später vollständig abgeschnitten werden kann.
- Version in `version.py` und im Fusion-Manifest auf `0.1.5` erhöht.

## 0.1.4 - 2026-05-26

- Profilebene robuster erzeugt und anschließend auf eine Ebene am Helixpfad umgestellt.
- Fehlerausgabe für die Profil-Erzeugung ergänzt, damit Fusion-API-Probleme im Dialog sichtbar werden.
- Vorgabewerte für den Dialog angepasst: Steigung `10`, Gewindelänge `30`, Öffnungswinkel `80 deg`, Gewindetiefe `5`.
- Dreiecksprofil entlang der Helix gesweept.
- Grund- oder Deckfläche des Zylinders als Führungsfläche für den Sweep ergänzt, damit sich das Profil entlang der Helix nicht verdreht.
- Erzeugte Arbeitsschritte in einer Timeline-Gruppe zusammengefasst. Gruppenname nach Schema `3DG<Durchmesser>x<Steigung>`.
- Profilposition bei Innenflächen/Bohrungen auf die gegenüberliegende Zylinderseite verschoben; die Ausrichtung des Dreiecks bleibt gleich.
- Robuste Profilüberlagerung ergänzt: Das Dreiecksprofil startet mit internem radialem Überstand von `0.2 mm`, damit spätere Körperoperationen nicht nur tangential berühren.
- Version in `version.py` und im Fusion-Manifest auf `0.1.4` erhöht.

## 0.1.3 - 2026-05-26

- Dialog um Öffnungswinkel und Gewindetiefe für das spätere Sweep-Profil erweitert.
- Konstruktionsebene am Helix-Startpunkt ergänzt, senkrecht zur Helix-Bahn.
- Dreiecksprofil auf der Profilebene erzeugt; die Gewindetiefe zeigt bei Außenflächen nach außen und bei Innenflächen nach innen.
- Version in `version.py` und im Fusion-Manifest auf `0.1.3` erhöht.

## 0.1.2 - 2026-05-26

- Dialog um Startseite, Steigung und Gewindelänge für eine erste Helix-Erzeugung erweitert.
- Erzeugung einer berechneten 3D-Helix entlang der ausgewählten Zylinderfläche ergänzt.
- Version in `version.py` und im Fusion-Manifest auf `0.1.2` erhöht.

## 0.1.1 - 2026-05-26

- Erkennung für Außenflächen und Innenflächen bei ausgewählten Zylinderflächen ergänzt.
- Dialogausgabe erweitert: Neben dem Durchmesser wird nun der Flächentyp (`Außenfläche` oder `Innenfläche`) angezeigt.
- Version in `version.py` und im Fusion-Manifest auf `0.1.1` erhöht.

## 0.1.0 - 2026-05-26

- Zentrale Add-In-Version in `Fusion_AddIn/PrintThread Wizard/version.py` ergänzt.
- Fusion-Manifest-Version auf `0.1.0` gesetzt.
- Command-Button in den Bereich Konstruktion / Erstellen verschoben (`FusionSolidEnvironment` / `SolidCreatePanel`).
- Dialogtitel auf `PrintThread Wizard 0.1.0` umgestellt.
- Ersten Installationstest ergänzt: Eine Fläche auswählen, bei Zylinderflächen den Durchmesser anzeigen und bei anderen Flächen einen Hinweis ausgeben.
- Template-Palette-Sample-Commands deaktiviert, damit nur der PrintThread-Wizard-Command registriert wird.
