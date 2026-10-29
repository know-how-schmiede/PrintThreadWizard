# Prüfprotokoll 0.9.4 – Kalibrierung und Druckprofile

Stand: 29.10.2026. Status: implementiert, Fusion- und Druckabnahme offen.

## Automatisch

36 Tests bestanden mit dem lokal installierten Fusion-Python, einschließlich
aller 24 bisherigen Tests. Neue Prüfungen: Spielwerte und kollisionsfreie
Probenpositionen, ungültige Serien, Profilgrenzen und ungültige Zahlen,
Schema-1-Migration, Schema-2-Rundlauf, atomarer Import, Kalibrierung ohne
Modellflächenauswahl, Abbruchanforderung bei Serienfehler und Anwenden eines
Profils ohne Änderung der Geometrievorgaben.

Zusätzliche Regressionen nach Anwenderprüfung: keine native Pflichtauswahl
blockiert den Kalibrierungsmodus; die gemeldeten Maße 30/4/20/3 mm sind gültig;
alle editierbaren Kalibrierungs- und Druckprofilfelder haben lokalisierte
Tooltips. Die Zielfläche wird für Modellgewinde weiterhin fachlich validiert.

Anwender bestätigt das Formularlayout und zeigt ein erfolgreich gespeichertes
Druckprofil. OK blieb trotz gültiger Serie deaktiviert. Die native
Pflichtauswahl im anderen Reiter wurde entfernt; erneute Prüfung des
OK-Buttons und der tatsächlichen Erzeugung in Fusion steht aus.

Weiterer Anwenderlauf: OK löst die Erstellung aus, diese scheitert mit
`InternalValidationError: Utils::getObjectPath(edge, objPath, nullptr, contextPath)`.
Vermutete Ursache ist die native Helixkante ohne Baugruppenkontext beim
Anlegen der Profilebene in der neuen Unterkomponente. Die Kalibrierung
übergibt jetzt ihre Instanz explizit; die Profilebene verwendet den passenden
Kantenproxy und Erzeugungskontext. Bei Serienfehlern wird die ausschließlich
dafür angelegte Komponente explizit entfernt. Fehlerlogs enthalten den
vollständigen Python-Traceback. Zwei weitere Regressionstests prüfen die
API-Argumente und das Aufräumen; erneute Fusion-Erzeugung bleibt offen.

Weiterer Lauf mit gleichem Fehler: Der lokale Fusion-Logeintrag vom
29.10.2026, 11:52:55, zeigt den konkreten Abbruch in
`_create_thread_sweep` bei `adsk.fusion.Path.create`, nicht mehr bei der
Profilebene. Die erste Korrektur allein war deshalb unvollständig. Auch der
Sweep-Pfad erhält jetzt den Kantenproxy der Kalibrierungsinstanz. Der neue
Regressionstest prüft diese API-Grenze mit einem Resolver, der die native
Unterkomponentenkante ablehnt. 36 Tests bestanden; tatsächlicher Sweep in
Fusion weiterhin zu bestätigen. Kein neuer Installer für diese Korrektur
erstellt, gemäß Anwenderwunsch.

Die Tests prüfen keine echten Fusion-Körper oder gedruckte Passung.

Windows-Installer mit Inno Setup 6.7.0 erfolgreich gebaut:
`dist/PrintThreadWizard_Setup_0.9.4.exe`, mit SHA-256-Datei daneben.
Nicht installiert oder veröffentlicht.

## In Fusion auszuführen

Fusion-Version/Plattform: noch nicht erfasst. Kein interaktiver Fusion-Test
durchgeführt.

| Fall | Erwartung | Status |
| --- | --- | --- |
| Reiter Kalibrierung, keine ausgewählte Fläche | Serie mit OK erzeugbar; Gewindereiter weiterhin separat nutzbar | Offen |
| 20 mm Durchmesser, 2 mm Steigung, 8 mm Länge, 3 mm Wand, 0,10–0,30 mm Spiel | REF und fünf benannte Ringe nebeneinander, gültige Volumenkörper | Offen |
| Rechts und links | Gegenseitig passende Richtung und Profilphase | Offen |
| Abbruch, Fehler beim dritten Ring, Undo/Redo | Gesamte Serie einschließlich neuer Komponente wird zurückgenommen; vorhandenes Modell unverändert | Offen |
| Aktive transformierte Komponente | Serie in eigener Root-Komponente korrekt platziert | Offen |
| Leere Liste, doppelte/negative/nichtendliche Werte, über zwölf Werte | Verständliche Ablehnung ohne Modelländerung | Offen |
| Zu dünne Wand, Länge unter zwei Steigungen, unpassender Durchmesser | Ablehnung | Offen |
| Profil speichern, Dialog neu öffnen, laden, löschen | Prozessdaten erhalten; Laden allein ändert keine Gewindegeometrie | Offen |
| Profil mit 0,23 mm Spiel anwenden | Exakter Wert, keine Rundung auf die bisherige Auswahlliste; nur Spiel/Verteilung geändert | Offen |
| Paar außerhalb des Profilbereichs | Anwendung vor Parameteränderungen abgewiesen | Offen |
| Schema 1 laden, Schema 2 exportieren/importieren | Presets, Standardspiel und Druckprofile erhalten | Offen |
| Speichern/Öffnen, Slicer-Export | Körpernamen und Zuordnung nachvollziehbar | Offen |
| DE, EN, ES, FR, IT, PL | Neuer Reiter und Meldungen vollständig lesbar | Offen |

## Druckabnahme

Offen. Drucker, Material, Düse, Schichthöhe, Orientierung, Durchmesser,
Steigung, gewähltes Spiel und Ergebnis für REF/R01–R05 dokumentieren.
Ringe im Slicer anhand der Körpernamen zuordnen und nach Entnahme markieren.
Profil mit Verteilung nur innen speichern und an einem weiteren Paar unter
denselben Bedingungen anwenden. Übertragung auf andere Verteilungen oder
Geometrien ist ohne erneute Prüfung nicht als abgenommen zu bewerten.
