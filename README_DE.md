# PrintThread Wizard

<img src="images/PrintThreadWizard_Logo.png" alt="PrintThread Wizard Logo" width="420">

Deutsch | [English](README.md)

PrintThread Wizard ist ein Add-in für Autodesk Fusion, das modellierte Außen-
und Innengewinde auf ausgewählten Zylinderflächen erzeugt. Die Geometrie ist
für funktionale FDM-/FFF-Bauteile vorgesehen und kann an das für gedruckte
Gewindepaare erforderliche Spiel angepasst werden.

Aktuelle Entwicklungsversion: **0.7.16**

## Aktueller Funktionsumfang

- Automatische Erkennung von Außenzylindern und Innenbohrungen
- Modellierte Rechtsgewinde mit exakter B-Rep-Helix und Sweep
- Automatischer ISO-Metrisch-Modus mit 60° Flankenwinkel und berechneter
  radialer Gewindetiefe
- Freier Geometriemodus zur manuellen Eingabe von Flankenwinkel und
  Gewindetiefe
- Einstellbare Steigung und Verrundung am Gewindegrund
- Auswählbares radiales Gesamtspiel von 0,00 bis 0,50 mm in 0,05-mm-Schritten;
  persistenter Standardwert: 0,15 mm
- Optionale Fasen an einer oder zwei ausgewählten kreisförmigen Endkanten
- Aus dem halben Flankenwinkel abgeleiteter Fasenwinkel
- Über beide Deckflächen hinausreichende Helix für vollständige
  Gewindeanfänge und -enden
- Zusammenfassung aller erzeugten Konstruktionsschritte in der eingeklappten
  Fusion-Timeline-Gruppe `PrintThread Wizard – Gewinde`
- Ausgeblendete Dokumentationsskizze als erster Gruppeneintrag mit Gewindeart,
  Nenndurchmesser, `P`, `α`, `h`, `r`, Toleranz, `d`, `d2`, `d1`, `T` und
  Anzahl der Fasen-Kanten
- Lokales Speichern der aktuellen Gewindeeinstellungen mit Bezeichner und Notiz
- Alphabetisch sortierte Preset-Auswahl zum Übernehmen aller gespeicherten
  Gewindeparameter
- Getrennte Reiter für Gewindeerstellung einschließlich Speicherfunktion und
  Verwaltung der gespeicherten Einstellungen
- Technische Kurzzeichen und Profildarstellung für Steigung `P`,
  Außendurchmesser `d`, Teilkreisdurchmesser `d2`, Innendurchmesser `d1`,
  Gewindebohrung `T`, Profiltiefe `h` und Profilwinkel `α`
- Kompakte Preset-Tabelle mit Bezeichner, `α`, `h`, `P` und Löschaktion im
  Verwaltungs-Reiter
- Auswahl einer Tabellenzeile zeigt deren vollständige Daten und Notiz an
- JSON-Import und -Export in einem eigenen Dialogbereich mit Statusanzeige
- Eigenes Markenlogo für Fusion-Dialog, GitHub und Webseiten

## Funktionsweise der Toleranz

Die ausgewählte Toleranz bezeichnet das radiale Gesamtspiel eines passenden
Gewindepaars. Wenn für Innen- und Außengewinde derselbe Wert verwendet wird,
wird das Spiel gleichmäßig auf beide Bauteile verteilt:

- Der Radius des Außengewindes wird um die halbe Toleranz verkleinert.
- Der Radius des Innengewindes wird um die halbe Toleranz vergrößert.
- Die Gewindeprofiltiefe bleibt unverändert.
- Flanken, Spitzen, Zylinderflächen und Fasen werden auf dem angepassten Radius
  erzeugt.

Bei 0,2 mm Toleranz wird beispielsweise der Außenradius um 0,1 mm verkleinert
und der Innenradius um 0,1 mm vergrößert. Der passende Wert hängt unter anderem
von Drucker, Material, Schichthöhe, Extrusionskalibrierung und Bauteilausrichtung
ab.

## Installation

1. Repository herunterladen oder klonen.
2. In Fusion **Dienstprogramme > Zusatzmodule > Skripte und Zusatzmodule**
   öffnen.
3. Auf der Registerkarte **Zusatzmodule** den Ordner
   `Fusion_AddIn/PrintThread Wizard` hinzufügen.
4. **PrintThread Wizard** starten und bei Bedarf den automatischen Start
   aktivieren.

Der Befehl wird im Arbeitsbereich **Konstruktion** unter
**Volumenkörper > Erstellen** eingefügt.

## Bedienung

1. Einen zylindrischen Zapfen für ein Außengewinde oder eine zylindrische
   Bohrung für ein Innengewinde vorbereiten. Der ausgewählte Durchmesser wird
   als Gewinde-Nenndurchmesser verwendet, beispielsweise 50 mm für eine
   M50-ähnliche Geometrie.
2. **PrintThread Wizard** starten.
3. Die Zylinderfläche auswählen.
4. Optional eine oder beide kreisförmigen Endkanten für die Fasen auswählen.
5. Optional eine gespeicherte Einstellung auswählen oder **ISO metrisch
   automatisch** beziehungsweise **Freie Geometrie** manuell auswählen.
6. Die Steigung sowie im freien Modus Flankenwinkel und Gewindetiefe eingeben.
7. Toleranz auswählen und Verrundungsradius festlegen.
8. Optional einen Gewindebezeichner und eine kurze Notiz eintragen und die
   aktuellen Einstellungen über **Aktuelle Einstellungen speichern** ablegen.
9. Die berechneten Werte im Ergebnisfeld prüfen und den Befehl bestätigen.

Für ein zusammengehöriges Gewindepaar müssen Nenndurchmesser, Steigung,
Flankengeometrie und Toleranz bei beiden Bauteilen gleich eingestellt werden.

## Dialogparameter

| Parameter | Beschreibung |
| --- | --- |
| Zylinderfläche | Zielfläche; Innen-/Außengewinde wird automatisch erkannt |
| Fasen-Kanten | Optionale Auswahl von bis zu zwei kreisförmigen Endkanten |
| Gespeicherte Einstellung | Alphabetisch sortierte Preset-Auswahl; übernimmt alle Parameter |
| Berechnung | ISO metrisch automatisch oder freie Geometrie |
| Profilwinkel (α) | Eingeschlossener Profilwinkel; im ISO-Modus fest 60° |
| Gewindetiefe (h) | Radiale Profiltiefe; im ISO-Modus automatisch berechnet |
| Gewindesteigung (P) | Axialer Weg pro Umdrehung |
| Verrundungsradius (r) | Rundet den scharfen Gewindegrund ab |
| Toleranz | Radiales Gesamtspiel des zusammengehörigen Gewindepaars |
| Gewindebezeichner | Name des lokal gespeicherten Parametersatzes |
| Kurze Notiz | Optionale Beschreibung mit bis zu 500 Zeichen |

Die Parametersätze werden benutzerspezifisch in der versionierten JSON-Datei
`PrintThread Wizard/thread-presets.json` im Anwendungsdatenordner des
Betriebssystems gespeichert. Modellabhängige Flächen und Kanten werden nicht
gespeichert.

Im Reiter **Einstellungen verwalten** kann die beim Öffnen des nächsten
Dialogs vorausgewählte Toleranz persistent festgelegt werden. Dort zeigt eine
scrollbare Tabelle außerdem alle gespeicherten Parametersätze mit Bezeichner,
Profilwinkel `α`, Gewindetiefe `h` und Gewindesteigung `P`. Einträge können
zeilenweise gelöscht werden.

Der Bereich **Einstellungen als JSON exportieren / importieren** sichert oder
lädt alle Presets einschließlich Standardtoleranz. Erfolg, Abbruch und Fehler
werden direkt unter den beiden Schaltflächen angezeigt.

Das Ergebnisfeld zeigt Gewindeart, Nenndurchmesser, `P`, `d`, `d2`, `d1`, `T`,
`α`, Toleranz und Berechnungsmodus. Die darunterliegende Skizze ordnet die
Kurzzeichen dem Gewindeprofil zu.

## Bekannte Einschränkungen

- Das Add-in befindet sich in Entwicklung; die erzeugte Geometrie muss vor der
  produktiven Verwendung geprüft werden.
- Derzeit werden nur Zylinderflächen und Rechtsgewinde unterstützt.
- Die Steigung wird manuell eingegeben; eine Tabelle genormter
  Gewindegrößen und Steigungen ist noch nicht enthalten.
- Toleranzwerte sind Ausgangswerte und müssen für Drucker und Material
  kalibriert werden.
- Die erzeugten Gewinde sind nicht für zertifizierte oder sicherheitskritische
  Verbindungen vorgesehen.

## Repository-Struktur

```text
Fusion_AddIn/PrintThread Wizard/
├── PrintThread Wizard.py
├── PrintThread Wizard.manifest
├── config.py
├── version.py
├── commands/
│   └── commandDialog/
├── core/
│   ├── iso_metric.py
│   └── thread_parameters.py
└── fusion/
    ├── chamfer.py
    ├── face_analysis.py
    └── thread_geometry.py
```

Der Entwicklungsverlauf ist unter
[doku/version-timeline.md](doku/version-timeline.md) dokumentiert.

## Lizenz und Haftungsausschluss

Siehe [LICENSE](LICENSE). PrintThread Wizard ist für Prototypen, Hobbyprojekte,
Vorrichtungen und andere nicht sicherheitskritische Anwendungen gedacht.
Passung, Festigkeit und Eignung gedruckter Bauteile müssen für den jeweiligen
Einsatzzweck geprüft werden.
