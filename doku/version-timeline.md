# Version Timeline

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
