# M6 – Machbarkeitsstand 0.9.6

Stand: 29.10.2026. Erster M6-Schritt implementiert: Daten erfassen und
Bezüge prüfen. Der Machbarkeitsnachweis für einen sicheren Neuaufbau ist
noch nicht abgeschlossen. Es gibt bewusst keinen Befehl, der vorhandene
Gewinde überschreibt oder alte Timeline-Features entfernt.

## Untersuchte API und Mechanismen

Die lokal installierte Fusion-Ausgabe meldet Produktversion **2706.1.14**.
Ihre Python-API wurde auf die benötigten Schnittstellen geprüft; dies ist
kein erfolgreicher interaktiver Funktionstest.

- Attribute an Skizzen und Features speichern Daten mit dem Dokument.
- `entityToken` und `Design.findEntityByToken` dienen zum Wiederfinden von
  Entitäten. Tokenzeichenfolgen dürfen nicht als Identität verglichen werden.
  Auflösung kann mehrere Entitäten liefern, etwa nach einer Flächenteilung.
- Timeline-Objekte stellen Position und `rollTo` bereit. Die neue Prüfung liest
  Positionen; sie verschiebt den Marker nicht.
- `CustomFeatureDefinition`, Abhängigkeiten, benutzerdefinierte Parameter und
  `setStartAndEndFeatures` sind in der lokalen API vorhanden. Ein Custom Feature
  ist ein möglicher späterer Bearbeitungsmechanismus, noch keine Entscheidung
  zugunsten einer fertigen Lösung.

Primärquellen:
[Autodesk: Custom Features](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CustomFeatures_UM.htm),
[BaseFeature und Entity-Tokens](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_BaseFeature.htm),
[Design](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_Design.htm).

Der bestehende Generator erzeugt persistente Helix-/Führungskörper, Profil,
Sweep, Beschnitt, Spielkorrektur und gegebenenfalls Fasen. Eine Änderung der
Steigung erfordert mehr als das Ändern eines einzelnen Sweep-Parameters.
Ein kontrollierter Neuaufbau muss ursprüngliche Geometrie wiederherstellen
und danach neue Features aufbauen; abhängige spätere Features dürfen dabei
nicht versehentlich entfernt oder auf andere Flächen umgebogen werden.

## Implementierter Datenpfad

`core/thread_records.py` definiert Dokument-Metadatenschema 1 mit strikter
Versions- und Parameterprüfung, getrennt vom unveränderten Presetschema 2.
Ungültige Zahlen, unvollständige Teilgewindebezüge und unbekannte Versionen
werden abgewiesen.

`fusion/thread_records.py` erfasst ursprüngliche Modellbezüge vor dem ersten
Geometrieeingriff. Nach erfolgreicher Erzeugung werden die Daten an der
Dokumentationsskizze gespeichert und eine gemeinsame ID am Ergebnisfeature
abgelegt. Der erste und letzte Feature-Bezug werden per Token gespeichert,
nicht als dauerhaft angenommene Timeline-Indizes. Die neuen Attribute gehören
zur bestehenden Erstellungs-Transaktion; ein Fehler wird nicht verschluckt.

Alle neu erzeugten Modellgewinde, Partner und Kalibrierungsproben werden
erfasst. Alte Gewinde erhalten keine erfundenen Ursprungsdaten. Unbekannte oder
beschädigte Datensätze werden in der Liste angezeigt, ohne andere gültige
Datensätze auszublenden. Die Prüfung verwendet nur Lesezugriffe. Mehrdeutige
Bezüge werden niemals automatisch auf den ersten Treffer reduziert.

## Nächster Machbarkeitsschritt in Fusion

Die Prüfroutine für Schritt 2 ist jetzt als **Ursprungsbezüge mit OK prüfen**
implementiert. Auswahl eines Datensatzes und Aktivieren dieser Option machen
OK zur ausschließlichen Testaktion. Der Test läuft innerhalb der Execute-
Transaktion, öffnet gegebenenfalls zugeklappte Timeline-Gruppen und rollt vor
das erste Erzeugungsfeature. Nur eindeutig aufgelöste Bezüge werden an die
bestehende Parameter-/Bereichsvalidierung übergeben. Im finally-Pfad werden
Gruppenansicht und ursprünglicher Marker wiederhergestellt. Es entstehen keine
neuen Features. Eine fehlgeschlagene Wiederherstellung führt zum Abbruch der
gesamten Befehls-Transaktion. Der Anwender bestätigt den erfolgreichen Test
für Komponente, Zielkörper, ursprüngliche Fläche und Parameter sowie die
Wiederherstellung der Timeline. Weitere Bezugsvarianten bleiben offen.

Für Schritt 3 ist **Neuaufbau mit OK testen und zurücknehmen** implementiert:
Während der Execute-Transaktion vor die erste alte Erzeugung rollen und den
vorhandenen Generator mit unveränderten Parametern ausführen. Die alten
Features werden dabei nicht gelöscht. Die automatische Timeline-Gruppierung
ist für diese Einfügung deaktiviert, damit keine nachfolgenden ursprünglichen
Features in eine neue Gruppe geraten. Anschließend wird executeFailed auch
nach erfolgreicher Erzeugung gesetzt. Fusion muss dadurch alle temporären
Geometrie- und Metadatenänderungen zurücknehmen. Es wird nicht zum Timeline-Ende
gerollt, um die alten späteren Features nicht am temporär veränderten Körper
auszuwerten. Die Gruppenansicht wird vor der Rücknahme zurückgestellt.

Dieser Test beweist noch keinen sicheren Austausch alter Features oder Erhalt
nachgelagerter Referenzen. Optional lassen sich jetzt im Test Spiel und Steigung
ändern; gespeicherte Teilgewinde erlauben auch Versatz und Länge bei gleicher
Startkante. Die Anpassung erfolgt mit unveränderlichen Parameterobjekten,
ohne den Datensatz zu verändern. Im metrischen Modus wird die Tiefe mit der
tatsächlichen Innen-/Außenart des Ursprungskörpers neu berechnet. Der geänderte
Abschnitt wird am wiederhergestellten Originalkörper geprüft. Es bleibt bei
einem ausschließlich temporären Test mit obligatorischer Rücknahme. Die
dauerhafte Übernahme einer Bearbeitung ist noch nicht implementiert.

1. Neues Gewinde erzeugen, speichern, schließen und öffnen. Parameter und
   Ergebnisbezüge müssen erhalten sein.
2. An einem separaten Testdokument nachweisen, dass ursprüngliche Fläche und
   Kanten beim Rollen vor die erste Erzeugung wieder eindeutig gefunden werden.
   Danach die ursprüngliche Markerposition wiederherstellen.
3. Einen begrenzten Neuaufbau im Command-Transaktionsmodell erproben und einen
   absichtlichen Fehler auslösen: altes Gewinde muss erhalten bleiben.
4. Erst nach diesem Nachweis einen Bearbeitungsdialog und gegebenenfalls einen
   Custom-Feature-Mechanismus integrieren. Paare, Fasen, Komponenteninstanzen,
   nachfolgende Features und Undo/Redo benötigen eigene Referenzfälle.

Der Reiter heißt deshalb **Gewindedaten prüfen**, nicht „Gewinde bearbeiten“.
Ein Datensatz oder erfolgreich aufgelöster Token allein kennzeichnet noch kein
sicher bearbeitbares Gewinde.
