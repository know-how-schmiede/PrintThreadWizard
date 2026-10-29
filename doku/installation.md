# PrintThread Wizard installieren

Diese Anleitung gilt für Version **0.9.4**. Der Installer ist für Windows;
unter Windows und macOS ist außerdem eine manuelle Installation möglich.

## 1. Den richtigen Fusion-Pfad feststellen

1. Fusion mit dem Benutzerkonto starten, das das Add-in verwenden soll.
2. **Voreinstellungen > API** öffnen.
3. Den Wert bei **Vorgabepfad für Skripte und Zusatzmodule** kopieren oder notieren.
4. Fusion vor der Installation bzw. dem Austausch von Add-in-Dateien schließen.

Dieser Pfad ist der Basisordner. Das Add-in gehört in dessen Unterordner
`AddIns/PrintThread Wizard`. Beispiel:

```text
API-Pfad in Fusion:
C:\Users\Rene\AppData\Roaming\Autodesk\Autodesk Fusion 360\API

Vollständiger Installationsordner:
C:\Users\Rene\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\PrintThread Wizard
```

Je nach Installation kann der Ordner `Autodesk Fusion` oder `Autodesk Fusion 360`
heißen. Auch ein selbst gewählter Pfad ist möglich. Maßgeblich ist die Einstellung
in Fusion. Wenn beide Ordner existieren, lässt sich daraus allein der aktive
Pfad nicht bestimmen. Die Fusion-Einstellung muss für die Installation nicht geändert werden.

## 2. Windows: Installation mit Installer

1. `PrintThreadWizard_Setup_0.9.4.exe` aus den
   [Releases des Projekts](https://github.com/know-how-schmiede/PrintThreadWizard/releases) herunterladen, sobald dort verfügbar.
2. Den Installer als normaler Windows-Benutzer starten. Administratorrechte
   sind nicht erforderlich.
3. Auf der Seite zur Zielordnerauswahl den vollständigen Installationsordner
   anhand des in Schritt 1 ermittelten API-Pfades prüfen und gegebenenfalls ändern.
   Hinter dem API-Pfad muss `\AddIns\PrintThread Wizard` stehen.
4. Den Zielpfad in der Zusammenfassung prüfen und die Installation starten.
5. Fusion starten und das Add-in wie unten beschrieben aktivieren.

Der Installer prüft diese beiden Basisordner:

```text
%APPDATA%\Autodesk\Autodesk Fusion\API
%APPDATA%\Autodesk\Autodesk Fusion 360\API
```

Wenn genau einer existiert, wird dieser vorgeschlagen. Existieren beide oder
keiner, zeigt der Installer einen entsprechenden Hinweis; der angezeigte
`Fusion 360`-Pfad ist dann lediglich ein Vorschlag. Einen benutzerdefinierten
API-Pfad erkennt der Installer nicht automatisch. Die Zielordnerauswahl bleibt
auch bei Updates sichtbar. Frühere Installationspfade werden nicht automatisch
übernommen; einen eigenen Pfad daher bei jedem Update prüfen.

Für eine unbeaufsichtigte Installation muss der vollständige Zielordner explizit
angegeben werden. Beispiel für die Windows-Eingabeaufforderung, wenn Fusion
genau diesen API-Pfad verwendet:

```bat
PrintThreadWizard_Setup_0.9.4.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\PrintThread Wizard"
```

## 3. Installation von Hand

### Windows

1. Den Quellcode der gewünschten Version herunterladen und das ZIP entpacken.
2. Im entpackten Projekt den Ordner `Fusion_AddIn/PrintThread Wizard` öffnen.
3. Den vollständigen Ordner **PrintThread Wizard** in den Unterordner **AddIns**
   des zuvor ermittelten API-Pfades kopieren. `AddIns` bei Bedarf anlegen.
4. Fusion starten und das Add-in aktivieren.

Nicht das gesamte Repository und nicht nur die Python-Datei kopieren. Die
Ordnerstruktur muss anschließend beispielsweise so aussehen:

```text
API/
└── AddIns/
    └── PrintThread Wizard/
        ├── PrintThread Wizard.py
        ├── PrintThread Wizard.manifest
        ├── version.py
        ├── commands/
        └── ... weitere Dateien und Unterordner des Add-ins
```

Eine zusätzliche Verschachtelung wie
`PrintThread Wizard/PrintThread Wizard/PrintThread Wizard.manifest` ist falsch.

### macOS

> **Hinweis des Entwicklers:** Ich kann die Installation und Funktion unter macOS
> nicht selbst testen, da mir kein Mac zur Verfügung steht. Die folgenden Schritte
> dienen als Anleitung, sind aber von mir nicht praktisch auf macOS geprüft.
> Rückmeldungen von Mac-Nutzern sind willkommen.

Für macOS steht kein Installer zur Verfügung. Die Windows-Datei
`PrintThreadWizard_Setup_0.9.4.exe` ist für diese Installation nicht geeignet.
Das Add-in wird von Hand kopiert:

1. Den Quellcode der gewünschten Version von der
   [Release-Seite](https://github.com/know-how-schmiede/PrintThreadWizard/releases)
   als ZIP herunterladen und im Finder durch Doppelklick entpacken.
2. Fusion öffnen und unter **Voreinstellungen > API** den
   **Vorgabepfad für Skripte und Zusatzmodule** kopieren. Anschließend Fusion
   vollständig beenden.
3. Im Finder **Gehe zu > Gehe zum Ordner …** wählen oder **⇧⌘G** drücken.
   Den kopierten API-Pfad einfügen und den Ordner öffnen.
4. Darin den Unterordner `AddIns` öffnen. Falls er fehlt, über
   **Ablage > Neuer Ordner** einen Ordner mit genau diesem Namen anlegen.
5. Im entpackten Download den Ordner `Fusion_AddIn` öffnen und den darin
   enthaltenen vollständigen Ordner **PrintThread Wizard** nach `AddIns` kopieren.
   Alle enthaltenen Dateien und Unterordner müssen mitkopiert werden.
6. Prüfen, dass `PrintThread Wizard.py` und `PrintThread Wizard.manifest`
   unmittelbar in `AddIns/PrintThread Wizard` liegen. Nicht das ganze Repository
   kopieren und keinen zweiten gleichnamigen Ordner dazwischen anlegen.
7. Fusion neu starten. Unter **Dienstprogramme > Zusatzmodule > Skripte und
   Zusatzmodule** das Add-in **PrintThread Wizard** auswählen und starten.
   Die Bezeichnungen können je nach Fusion-Version abweichen.
8. Bei Bedarf **Beim Start ausführen** aktivieren. Der Befehl befindet sich im
   Arbeitsbereich **Konstruktion** unter **Volumenkörper > Erstellen**.

Ein möglicher vollständiger Zielpfad ist:

```text
~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/PrintThread Wizard
```

`~` steht für den persönlichen Benutzerordner. Der Ordner `Library` ist meist
ausgeblendet; über **Gehe zum Ordner …** lässt er sich trotzdem direkt öffnen.
Der tatsächlich in Fusion angegebene Pfad hat Vorrang vor diesem Beispiel:
Auch `Autodesk Fusion` statt `Autodesk Fusion 360` oder ein eigener Pfad ist möglich.

Falls das Add-in nicht erscheint, den Pfad und die Ordnerstruktur nochmals prüfen.
Alternativ im Dialog **Skripte und Zusatzmodule** die Funktion zum Hinzufügen
eines vorhandenen Add-ins verwenden und den kopierten Ordner **PrintThread Wizard**
auswählen. Bei einem Update Fusion zuvor beenden und die alte Add-in-Kopie durch
den vollständigen Ordner der neuen Version ersetzen; eigene Änderungen vorher sichern.

## 4. Add-in in Fusion aktivieren

1. **Dienstprogramme > Zusatzmodule > Skripte und Zusatzmodule** öffnen
   (die Bezeichnungen können je nach Fusion-Version abweichen).
2. Unter den Zusatzmodulen **PrintThread Wizard** auswählen und starten.
3. Bei Bedarf **Beim Start ausführen** aktivieren.
4. Der Befehl steht im Arbeitsbereich **Konstruktion**, Register **Volumenkörper**,
   im Bereich **Erstellen** zur Verfügung. Im Add-in-Dialog muss Version **0.9.4**
   angezeigt werden.

Falls der Eintrag fehlt, zunächst den Installationspfad prüfen. Über die Funktion
zum Hinzufügen eines vorhandenen Add-ins lässt sich der Ordner auch manuell
registrieren.

## 5. Update oder bisher falschen Installationspfad korrigieren

Bei einem regulären Update Fusion schließen und Version 0.9.4 in denselben,
mit den Fusion-Voreinstellungen abgeglichenen Zielordner installieren bzw. die
Add-in-Dateien dort durch die neue Version ersetzen.

Wenn die bisherige Version im falschen Ordner liegt:

1. Den korrekten API-Pfad in Fusion notieren und Fusion schließen.
2. Wurde die alte Version mit dem Installer installiert, diese zunächst über die
   Windows-Einstellungen unter **Apps** deinstallieren.
3. Bei einer manuellen Installation den alten Ordner `PrintThread Wizard` außerhalb
   der Fusion-Add-in-Ordner sichern und anschließend die alte Kopie entfernen.
   Keine anderen Add-ins oder ganzen Autodesk-Ordner löschen.
4. Version 0.9.4 im richtigen Zielordner installieren.
5. Fusion starten, gegebenenfalls einen alten verknüpften Eintrag aus der Liste
   entfernen und das Add-in aus dem richtigen Ordner hinzufügen.

Der Installer verschiebt oder entfernt alte Kopien in anderen Ordnern nicht
automatisch. Nicht gleichzeitig mehrere Kopien registriert lassen. Eigene
gespeicherte Parametersätze bei Bedarf vor dem Update über die JSON-Exportfunktion sichern.

## 6. Wenn das Add-in nicht erscheint

- Entspricht der Basisordner der Einstellung unter **Voreinstellungen > API**?
- Liegen Python-Datei und Manifest direkt in `AddIns/PrintThread Wizard`?
- Wurde Fusion nach der Installation neu gestartet?
- Wurde für denselben Windows-Benutzer installiert, der Fusion ausführt?
- Zeigt ein bereits vorhandener verknüpfter Eintrag noch auf einen alten Ordner?

Die Bedeutung des API-Basisordners und seiner Unterordner beschreibt Autodesk in
der [Dokumentation zum Skript- und Add-in-Pfad](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/APIPreferences_defaultPathForScriptsAndAddIns.htm).
