SUPPORTED_LOCALES = ('de', 'en', 'es', 'fr', 'it', 'pl')

_LANGUAGE_ENUM_NAMES = {
    'de': 'GermanLanguage',
    'en': 'EnglishLanguage',
    'es': 'SpanishLanguage',
    'fr': 'FrenchLanguage',
    'it': 'ItalianLanguage',
    'pl': 'PolishLanguage',
}

_EN = {
    'description': 'Creates 3D-printable threads on cylindrical faces.',
    'create_tab': 'Create thread', 'manage_tab': 'Manage settings',
    'target_face': 'Cylindrical face', 'select_face': 'Select a cylindrical face.',
    'chamfer_edges': 'Chamfer edges', 'select_edges': 'Optionally select one or two cylindrical edges.',
    'saved_setting': 'Saved setting', 'choose_setting': '— Select setting —',
    'calculation': 'Calculation', 'iso_mode': 'ISO metric automatic', 'free_mode': 'Free geometry',
    'profile_angle': 'Included angle (α)', 'thread_depth': 'Thread depth (h)',
    'pitch': 'Thread pitch (P)', 'fillet_radius': 'Fillet radius (r)', 'tolerance': 'Tolerance',
    'select_face_result': 'Please select a cylindrical face.',
    'dimensions_group': 'Thread parameter diagram',
    'preset_table_name': 'Saved parameters', 'name': 'Name', 'action': 'Action', 'delete': 'Delete',
    'no_row': 'No table row selected.',
    'json_group': 'Export / import settings as JSON', 'export': 'Export', 'import': 'Import',
    'default_tolerance': 'Default tolerance', 'set_default': 'Set as default',
    'save_group': 'Save current settings', 'thread_name': 'Thread name', 'short_note': 'Short note',
    'save_current': 'Save current settings', 'version': 'Version',
    'saved': '“{name}” was saved.', 'deleted': '“{name}” was deleted.',
    'preset_incomplete': 'The setting “{name}” is incomplete: {error}',
    'confirm_delete': 'Do you really want to delete “{name}”?',
    'default_saved': '{value} was saved as the default tolerance.',
    'export_title': 'Export thread settings as JSON', 'import_title': 'Import thread settings from JSON',
    'export_cancelled': 'Export cancelled.', 'import_cancelled': 'Import cancelled.',
    'export_ok': '{count} setting(s) exported successfully.', 'import_ok': '{count} setting(s) imported successfully.',
    'export_failed': 'Export failed: {error}', 'import_failed': 'Import failed: {error}',
    'details_name': 'Name', 'note': 'Note', 'mode': 'Mode', 'saved_at': 'Saved',
    'external_thread': 'External thread', 'internal_thread': 'Internal thread',
    'nominal_diameter': 'Nominal diameter', 'major_diameter': 'Major diameter (d)',
    'pitch_diameter': 'Pitch diameter (d2)', 'minor_diameter': 'Minor diameter (d1)',
    'tap_drill': 'Tap-drill diameter (T)', 'internal_only': '— (internal threads only)',
    'profile_mode_iso': 'ISO metric', 'profile_mode_free': 'Free geometry',
}

_TRANSLATIONS = {
    'en': _EN,
    'de': {**_EN,
        'description': 'Erstellt 3D-druckbare Gewinde auf Zylinderflächen.', 'create_tab': 'Gewinde erstellen', 'manage_tab': 'Einstellungen verwalten',
        'target_face': 'Zylinderfläche', 'select_face': 'Wählen Sie eine Zylinderfläche aus.', 'chamfer_edges': 'Fasen-Kanten', 'select_edges': 'Optional eine oder zwei Zylinderkanten auswählen.',
        'saved_setting': 'Gespeicherte Einstellung', 'choose_setting': '— Einstellung auswählen —', 'calculation': 'Berechnung', 'iso_mode': 'ISO metrisch automatisch', 'free_mode': 'Freie Geometrie',
        'profile_angle': 'Profilwinkel (α)', 'thread_depth': 'Gewindetiefe (h)', 'pitch': 'Gewindesteigung (P)', 'fillet_radius': 'Verrundungsradius (r)', 'tolerance': 'Toleranz',
        'select_face_result': 'Bitte eine Zylinderfläche auswählen.', 'dimensions_group': 'Skizze der Gewindeparameter', 'preset_table_name': 'Gespeicherte Parameter',
        'name': 'Bezeichner', 'action': 'Aktion', 'delete': 'Löschen', 'no_row': 'Noch keine Tabellenzeile ausgewählt.',
        'json_group': 'Einstellungen als JSON exportieren / importieren', 'export': 'Export', 'import': 'Import', 'default_tolerance': 'Standardtoleranz', 'set_default': 'Als Standard festlegen',
        'save_group': 'Aktuelle Einstellungen speichern', 'thread_name': 'Gewindebezeichner', 'short_note': 'Kurze Notiz', 'save_current': 'Aktuelle Einstellungen speichern',
        'saved': '„{name}“ wurde gespeichert.', 'deleted': '„{name}“ wurde gelöscht.', 'confirm_delete': 'Soll die Einstellung „{name}“ wirklich gelöscht werden?',
        'preset_incomplete': 'Die Einstellung „{name}“ ist unvollständig: {error}',
        'default_saved': '{value} wurde als Standardtoleranz gespeichert.', 'export_title': 'Gewindeeinstellungen als JSON exportieren', 'import_title': 'Gewindeeinstellungen aus JSON importieren',
        'export_cancelled': 'Export abgebrochen.', 'import_cancelled': 'Import abgebrochen.', 'export_ok': '{count} Einstellung(en) erfolgreich exportiert.', 'import_ok': '{count} Einstellung(en) erfolgreich importiert.',
        'export_failed': 'Export fehlgeschlagen: {error}', 'import_failed': 'Import fehlgeschlagen: {error}', 'details_name': 'Bezeichner', 'note': 'Notiz', 'mode': 'Modus', 'saved_at': 'Gespeichert',
        'external_thread': 'Außengewinde', 'internal_thread': 'Innengewinde', 'nominal_diameter': 'Nenndurchmesser', 'major_diameter': 'Außendurchmesser (d)',
        'pitch_diameter': 'Teilkreisdurchmesser (d2)', 'minor_diameter': 'Innendurchmesser (d1)', 'tap_drill': 'Gewindebohrung (T)', 'internal_only': '– (nur Innengewinde)', 'profile_mode_iso': 'ISO metrisch', 'profile_mode_free': 'Freie Geometrie'},
    'es': {**_EN, 'create_tab':'Crear rosca','manage_tab':'Gestionar ajustes','target_face':'Cara cilíndrica','select_face':'Seleccione una cara cilíndrica.','chamfer_edges':'Aristas de chaflán','saved_setting':'Ajuste guardado','choose_setting':'— Seleccionar ajuste —','calculation':'Cálculo','iso_mode':'ISO métrica automática','free_mode':'Geometría libre','profile_angle':'Ángulo de perfil (α)','thread_depth':'Profundidad de rosca (h)','pitch':'Paso de rosca (P)','fillet_radius':'Radio de redondeo (r)','tolerance':'Tolerancia','dimensions_group':'Esquema de parámetros de rosca','name':'Nombre','action':'Acción','delete':'Eliminar','no_row':'No hay ninguna fila seleccionada.','json_group':'Exportar / importar ajustes como JSON','export':'Exportar','import':'Importar','default_tolerance':'Tolerancia predeterminada','set_default':'Establecer como predeterminada','save_group':'Guardar ajustes actuales','thread_name':'Nombre de rosca','short_note':'Nota breve','save_current':'Guardar ajustes actuales','note':'Nota','mode':'Modo','saved_at':'Guardado','saved':'“{name}” se ha guardado.','deleted':'“{name}” se ha eliminado.','confirm_delete':'¿Eliminar realmente “{name}”?','export_cancelled':'Exportación cancelada.','import_cancelled':'Importación cancelada.','export_ok':'{count} ajuste(s) exportado(s).','import_ok':'{count} ajuste(s) importado(s).','external_thread':'Rosca exterior','internal_thread':'Rosca interior','nominal_diameter':'Diámetro nominal','major_diameter':'Diámetro exterior (d)','pitch_diameter':'Diámetro de paso (d2)','minor_diameter':'Diámetro interior (d1)','tap_drill':'Taladro de rosca (T)'},
    'fr': {**_EN, 'create_tab':'Créer un filetage','manage_tab':'Gérer les réglages','target_face':'Face cylindrique','select_face':'Sélectionnez une face cylindrique.','chamfer_edges':'Arêtes de chanfrein','saved_setting':'Réglage enregistré','choose_setting':'— Sélectionner un réglage —','calculation':'Calcul','iso_mode':'ISO métrique automatique','free_mode':'Géométrie libre','profile_angle':'Angle de profil (α)','thread_depth':'Profondeur du filet (h)','pitch':'Pas du filet (P)','fillet_radius':'Rayon de congé (r)','tolerance':'Tolérance','dimensions_group':'Schéma des paramètres du filetage','name':'Désignation','action':'Action','delete':'Supprimer','no_row':'Aucune ligne sélectionnée.','json_group':'Exporter / importer les réglages en JSON','export':'Exporter','import':'Importer','default_tolerance':'Tolérance par défaut','set_default':'Définir par défaut','save_group':'Enregistrer les réglages actuels','thread_name':'Désignation du filetage','short_note':'Note courte','save_current':'Enregistrer les réglages actuels','note':'Note','mode':'Mode','saved_at':'Enregistré','saved':'« {name} » a été enregistré.','deleted':'« {name} » a été supprimé.','confirm_delete':'Supprimer réellement « {name} » ?','export_cancelled':'Exportation annulée.','import_cancelled':'Importation annulée.','export_ok':'{count} réglage(s) exporté(s).','import_ok':'{count} réglage(s) importé(s).','external_thread':'Filetage extérieur','internal_thread':'Filetage intérieur','nominal_diameter':'Diamètre nominal','major_diameter':'Diamètre extérieur (d)','pitch_diameter':'Diamètre sur flancs (d2)','minor_diameter':'Diamètre intérieur (d1)','tap_drill':'Perçage de filetage (T)'},
    'it': {**_EN, 'create_tab':'Crea filettatura','manage_tab':'Gestisci impostazioni','target_face':'Faccia cilindrica','select_face':'Selezionare una faccia cilindrica.','chamfer_edges':'Spigoli smusso','saved_setting':'Impostazione salvata','choose_setting':'— Seleziona impostazione —','calculation':'Calcolo','iso_mode':'ISO metrica automatica','free_mode':'Geometria libera','profile_angle':'Angolo profilo (α)','thread_depth':'Profondità filetto (h)','pitch':'Passo filetto (P)','fillet_radius':'Raggio raccordo (r)','tolerance':'Tolleranza','dimensions_group':'Schema parametri filettatura','name':'Nome','action':'Azione','delete':'Elimina','no_row':'Nessuna riga selezionata.','json_group':'Esporta / importa impostazioni JSON','export':'Esporta','import':'Importa','default_tolerance':'Tolleranza predefinita','set_default':'Imposta come predefinita','save_group':'Salva impostazioni correnti','thread_name':'Nome filettatura','short_note':'Nota breve','save_current':'Salva impostazioni correnti','note':'Nota','mode':'Modalità','saved_at':'Salvato','saved':'“{name}” è stato salvato.','deleted':'“{name}” è stato eliminato.','confirm_delete':'Eliminare davvero “{name}”?','export_cancelled':'Esportazione annullata.','import_cancelled':'Importazione annullata.','export_ok':'{count} impostazione/i esportata/e.','import_ok':'{count} impostazione/i importata/e.','external_thread':'Filettatura esterna','internal_thread':'Filettatura interna','nominal_diameter':'Diametro nominale','major_diameter':'Diametro esterno (d)','pitch_diameter':'Diametro primitivo (d2)','minor_diameter':'Diametro interno (d1)','tap_drill':'Foro di maschiatura (T)'},
    'pl': {**_EN, 'create_tab':'Utwórz gwint','manage_tab':'Zarządzaj ustawieniami','target_face':'Powierzchnia cylindryczna','select_face':'Wybierz powierzchnię cylindryczną.','chamfer_edges':'Krawędzie fazowania','saved_setting':'Zapisane ustawienie','choose_setting':'— Wybierz ustawienie —','calculation':'Obliczenia','iso_mode':'Automatyczny ISO metryczny','free_mode':'Geometria dowolna','profile_angle':'Kąt profilu (α)','thread_depth':'Głębokość gwintu (h)','pitch':'Skok gwintu (P)','fillet_radius':'Promień zaokrąglenia (r)','tolerance':'Tolerancja','dimensions_group':'Schemat parametrów gwintu','name':'Nazwa','action':'Akcja','delete':'Usuń','no_row':'Nie wybrano wiersza tabeli.','json_group':'Eksport / import ustawień JSON','export':'Eksport','import':'Import','default_tolerance':'Tolerancja domyślna','set_default':'Ustaw jako domyślną','save_group':'Zapisz bieżące ustawienia','thread_name':'Nazwa gwintu','short_note':'Krótka notatka','save_current':'Zapisz bieżące ustawienia','note':'Notatka','mode':'Tryb','saved_at':'Zapisano','saved':'Zapisano „{name}”.','deleted':'Usunięto „{name}”.','confirm_delete':'Czy na pewno usunąć „{name}”?','export_cancelled':'Anulowano eksport.','import_cancelled':'Anulowano import.','export_ok':'Wyeksportowano ustawienia: {count}.','import_ok':'Zaimportowano ustawienia: {count}.','external_thread':'Gwint zewnętrzny','internal_thread':'Gwint wewnętrzny','nominal_diameter':'Średnica nominalna','major_diameter':'Średnica zewnętrzna (d)','pitch_diameter':'Średnica podziałowa (d2)','minor_diameter':'Średnica wewnętrzna (d1)','tap_drill':'Otwór pod gwint (T)'},
}


def detect_locale(adsk_core, app) -> str:
    language = app.preferences.generalPreferences.userLanguage
    for locale, enum_name in _LANGUAGE_ENUM_NAMES.items():
        enum_value = getattr(adsk_core.UserLanguages, enum_name, None)
        if enum_value is not None and language == enum_value:
            return locale
    return 'en'


def translator(locale: str):
    strings = _TRANSLATIONS.get(locale, _EN)

    def translate(key: str, **values) -> str:
        return strings.get(key, _EN.get(key, key)).format(**values)

    return translate
