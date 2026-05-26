# Version Timeline

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
