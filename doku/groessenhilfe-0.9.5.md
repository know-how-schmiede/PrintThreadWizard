# Größenhilfe und leichte Vorschau – 0.9.5

## Herkunft und Umfang der Auswahl

Quelle: Bossard, **Metric ISO threads**, F-en-2023.05,
[technische Übersicht](https://www.bossard.com/sg-en/knowledge-hub/resources/technical-information/metric-iso-threads/),
[Tabellen als PDF](https://media.bossard.com/-/media/bossard-group/website/documents/technical-resources/en/f_079_en.pdf).
Abgeglichen am 29.10.2026: Auswahlreihe für Regelgewinde und Tabellen der
Feingewinde. Die Implementierung übernimmt nur Nenndurchmesser und Steigung,
keine Grenzmaße oder Toleranzklassen. Es handelt sich um eine begrenzte Auswahl
M3–M36, nicht um eine vollständige Normtabelle. Die angebotenen Kombinationen
stehen zentral in `core/thread_sizes.py`.

**Größe übernehmen** setzt den metrischen Berechnungsmodus und die Steigung.
Der Durchmesser stammt weiterhin aus der ausgewählten Zylinderfläche.
Abweichungen über 0,01 mm werden für beide Partner als Warnung angezeigt;
dieser Schwellwert ist keine Passungstoleranz. Kein Körper wird skaliert.
Andere Einstellungen wie Spiel, Länge, Richtung und Verrundung bleiben
erhalten. Ein für kleine Steigungen zu großer Verrundungsradius muss manuell
korrigiert werden. Manuelle Eingaben und freie Profile bleiben möglich.

Auswahl und Vorschau sind Bedienhilfen. Sie garantieren weder normgerechte
Gewinde noch eine Passung mit metallischen Gegenstücken. Die Größenhilfe ist
kein Druckprofil. Presets speichern weiterhin die tatsächlich angewendeten
Geometrieparameter; die Auswahlhilfe selbst ist kein zusätzlicher gespeicherter
Parameter. Beim Laden eines Presets wechselt sie auf manuelle Eingabe.

## Darstellung

Dialog und zugehörige Ansicht aus Version 0.9.5:

<img src="../images/29-10-2026_12-38-01.png" alt="Gewindedialog mit aktivierter leichter Vorschau und Linksgewinde" width="641">

<img src="../images/29-10-2026_12-38-17.png" alt="Vorschau mit cyanfarbenem Bereich, orangem Richtungspfeil und magentafarbener Profilhülle" width="892">

Vom Anwender bestätigte Paarvorschau mit Linksgewinde und 10 mm Steigung,
gefolgt vom erzeugten Außen-/Innengewindepaar:

<img src="../images/29-10-2026_12-47-57.png" alt="Paarvorschau für beide gewählten Zylinderflächen mit Bereich, Richtung und Profilhülle" width="1000">

<img src="../images/29-10-2026_12-51-17.png" alt="Erzeugtes Gewindepaar nach Bestätigen des Dialogs" width="1000">

Die optionale **Leichte Vorschau** erzeugt ausschließlich temporäre
Custom-Graphics-Linien, keine Skizzen, Timeline-Features oder Körper:

- Cyan: gewählter Bereich, Endkreise und Achse einschließlich Startversatz.
- Orange: bis zu eine Helixumdrehung und Richtungspfeil; bei kürzeren Bereichen
  entsprechend weniger als eine Umdrehung.
- Magenta: scharfe Profilhülle. Verrundungen und Fasen werden nicht dargestellt;
  passt das Dreieck axial nicht in den Bereich, wird es weggelassen.

Für Paare werden beide gewählten Bereiche dargestellt. Komponenteninstanzen
werden über deren Transformationsmatrix berücksichtigt. Die Anzeige ist nicht
selektierbar. Änderungen aktualisieren sie; Abschalten, ungültige Eingaben,
Wechsel in den Kalibrierungsmodus, Ausführen und Abbrechen entfernen sie.
Bei Darstellungsfehlern wird die Vorschau entfernt und eine Meldung gezeigt;
die eigentliche Erstellung bleibt unabhängig davon nutzbar.

Eine vollständige Sweep-Vorschau ist in 0.9.5 nicht enthalten. Die Linienzahl
ist unabhängig von Gewindelänge und Gangzahl der gezeigten Beispielhelix auf
höchstens 170 Segmente je Bauteil begrenzt. Der Dialog zeigt die gemessene
API-Aufbauzeit der letzten Aktualisierung an, einschließlich Parameteranalyse
und Grafikaufbau, jedoch ohne die spätere GPU-Darstellung. Es gibt keine
allgemeine Laufzeitzusage. Fusion-Referenzmessungen stehen im Prüfprotokoll
noch aus.
