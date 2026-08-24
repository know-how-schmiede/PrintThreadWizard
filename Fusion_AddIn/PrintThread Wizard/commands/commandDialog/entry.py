import os

import adsk.core
import adsk.fusion

from ... import config
from ...core.iso_metric import ISO_FLANK_ANGLE, radial_thread_depth
from ...core.thread_parameters import ThreadParameters
from ...core.thread_presets import (
    delete_thread_preset,
    export_thread_presets,
    import_thread_presets,
    load_default_tolerance,
    load_thread_presets,
    save_default_tolerance,
    save_thread_preset,
)
from ...fusion.face_analysis import analyze_cylinder
from ...fusion.thread_geometry import create_thread
from ...lib import fusionAddInUtils as futil
from ...localization import detect_locale, translator
from ...version import VERSION


app = adsk.core.Application.get()
ui = app.userInterface
LOCALE = detect_locale(adsk.core, app)
tr = translator(LOCALE)

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = f'PrintThread Wizard {VERSION}'
CMD_DESCRIPTION = tr('description')

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
IS_PROMOTED = True

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')
THREAD_DIMENSIONS_IMAGE = os.path.join(ICON_FOLDER, 'thread_dimensions.png')
BRAND_LOGO_IMAGE = os.path.join(ICON_FOLDER, 'PrintThreadWizard_DialogLogo.png')

local_handlers = []
updating_calculated_inputs = False
active_command_inputs = None
available_presets = []
loading_preset = False
table_refresh_serial = 0
table_delete_actions = {}
table_row_presets = {}

ISO_MODE_NAME = tr('iso_mode')
FREE_MODE_NAME = tr('free_mode')
TOLERANCE_OPTIONS = tuple(
    (f'{step * 0.05:.2f}'.replace('.', ',') + ' mm', step * 0.005)
    for step in range(11)
)
FALLBACK_TOLERANCE_NAME = '0,15 mm'


def start():
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    if command_definition is None:
        command_definition = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
        )

    futil.add_handler(command_definition.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
    if panel is None:
        ui.messageBox('PrintThread Wizard: Der Bereich Konstruktion / Erstellen wurde nicht gefunden.')
        return

    control = panel.controls.itemById(CMD_ID)
    if control is None:
        control = panel.controls.addCommand(command_definition)
    control.isPromoted = IS_PROMOTED


def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
    control = panel.controls.itemById(CMD_ID) if panel else None
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    if control:
        control.deleteMe()
    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    global active_command_inputs
    inputs = args.command.commandInputs
    active_command_inputs = inputs

    version_text = inputs.addTextBoxCommandInput(
        'version_info', tr('version'), f'PrintThread Wizard {VERSION}', 1, True
    )
    version_text.isFullWidth = True

    brand_logo = inputs.addImageCommandInput('brand_logo', '', BRAND_LOGO_IMAGE)
    brand_logo.isFullWidth = True

    create_tab = inputs.addTabCommandInput('create_tab', tr('create_tab'))
    create_inputs = create_tab.children
    management_tab = inputs.addTabCommandInput('management_tab', tr('manage_tab'))
    management_inputs = management_tab.children

    face_input = create_inputs.addSelectionInput(
        'target_face', tr('target_face'), tr('select_face')
    )
    face_input.addSelectionFilter('Faces')
    face_input.setSelectionLimits(1, 1)

    edge_input = create_inputs.addSelectionInput(
        'chamfer_edges', tr('chamfer_edges'), tr('select_edges')
    )
    edge_input.addSelectionFilter('Edges')
    edge_input.setSelectionLimits(0, 2)

    preset_selector = create_inputs.addDropDownCommandInput(
        'preset_selector', tr('saved_setting'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )

    default_units = app.activeProduct.unitsManager.defaultLengthUnits
    mode_input = create_inputs.addDropDownCommandInput(
        'calculation_mode', tr('calculation'), adsk.core.DropDownStyles.TextListDropDownStyle
    )
    mode_input.listItems.add(ISO_MODE_NAME, True)
    mode_input.listItems.add(FREE_MODE_NAME, False)

    create_inputs.addValueInput(
        'flank_angle', tr('profile_angle'), 'deg', adsk.core.ValueInput.createByString('60 deg')
    )
    create_inputs.addValueInput(
        'thread_depth', tr('thread_depth'), default_units,
        adsk.core.ValueInput.createByString(f'5 {default_units}')
    )
    create_inputs.addValueInput(
        'pitch', tr('pitch'), default_units,
        adsk.core.ValueInput.createByString(f'10 {default_units}')
    )
    create_inputs.addValueInput(
        'fillet_radius', tr('fillet_radius'), default_units,
        adsk.core.ValueInput.createByString('0.4 mm')
    )
    tolerance_input = create_inputs.addDropDownCommandInput(
        'tolerance', tr('tolerance'), adsk.core.DropDownStyles.TextListDropDownStyle
    )
    default_tolerance_name = _tolerance_name(load_default_tolerance())
    for name, _ in TOLERANCE_OPTIONS:
        tolerance_input.listItems.add(name, name == default_tolerance_name)

    result_text = create_inputs.addTextBoxCommandInput(
        'result_text', 'Ergebnis',
        tr('select_face_result'), 9, True
    )
    result_text.isFullWidth = True

    dimensions_group = create_inputs.addGroupCommandInput(
        'dimensions_group', tr('dimensions_group')
    )
    dimensions_group.isExpanded = False
    dimensions_image = dimensions_group.children.addImageCommandInput(
        'thread_dimensions_image', '', THREAD_DIMENSIONS_IMAGE
    )
    dimensions_image.isFullWidth = True

    preset_table = management_inputs.addTableCommandInput(
        'preset_table', '', 5, '3:1:1:1:1'
    )
    preset_table.isFullWidth = True
    preset_table.minimumVisibleRows = 3
    preset_table.maximumVisibleRows = 8
    preset_table.tablePresentationStyle = (
        adsk.core.TablePresentationStyles.itemBorderTablePresentationStyle
    )
    preset_table.hasGrid = False

    management_details = management_inputs.addTextBoxCommandInput(
        'management_details', '', tr('no_row'), 7, True
    )
    management_details.isFullWidth = True

    transfer_group = management_inputs.addGroupCommandInput(
        'transfer_group', tr('json_group')
    )
    transfer_inputs = transfer_group.children
    transfer_buttons = transfer_inputs.addTableCommandInput(
        'transfer_buttons', '', 2, '1:1'
    )
    transfer_buttons.minimumVisibleRows = 1
    transfer_buttons.maximumVisibleRows = 1
    transfer_buttons.hasGrid = False
    transfer_buttons.isFullWidth = True
    transfer_buttons.tablePresentationStyle = (
        adsk.core.TablePresentationStyles.itemBorderTablePresentationStyle
    )
    export_button = transfer_inputs.addBoolValueInput(
        'export_presets', tr('export'), False, '', False
    )
    import_button = transfer_inputs.addBoolValueInput(
        'import_presets', tr('import'), False, '', False
    )
    transfer_buttons.addCommandInput(export_button, 0, 0)
    transfer_buttons.addCommandInput(import_button, 0, 1)
    transfer_status = transfer_inputs.addTextBoxCommandInput(
        'transfer_status', '', '', 2, True
    )
    transfer_status.isFullWidth = True

    default_tolerance_input = management_inputs.addDropDownCommandInput(
        'default_tolerance', tr('default_tolerance'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    for name, _ in TOLERANCE_OPTIONS:
        default_tolerance_input.listItems.add(name, name == default_tolerance_name)
    management_inputs.addBoolValueInput(
        'save_default_tolerance', tr('set_default'), False, '', False
    )
    default_status = management_inputs.addTextBoxCommandInput(
        'default_tolerance_status', '', '', 2, True
    )
    default_status.isFullWidth = True

    preset_group = create_inputs.addGroupCommandInput(
        'preset_group', tr('save_group')
    )
    preset_group.isExpanded = False
    preset_inputs = preset_group.children
    preset_inputs.addStringValueInput('preset_name', tr('thread_name'), '')
    preset_inputs.addTextBoxCommandInput(
        'preset_note', tr('short_note'), '', 2, False
    )
    preset_inputs.addBoolValueInput(
        'save_preset', tr('save_current'), False, '', False
    )
    preset_status = preset_inputs.addTextBoxCommandInput(
        'preset_status', '', '', 2, True
    )
    preset_status.isFullWidth = True

    _refresh_preset_selectors(inputs)
    _apply_calculation_mode(inputs)

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    try:
        _apply_calculation_mode(args.command.commandInputs)
        parameters = _read_parameters(args.command.commandInputs)
        errors = _validation_errors(parameters)
        if errors:
            raise ValueError('\n'.join(errors))

        create_thread(parameters)
        futil.log(f'{CMD_NAME}: Gewinde erfolgreich erzeugt.')
    except Exception as error:
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)
        ui.messageBox(f'PrintThread Wizard:\n{error}')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    global loading_preset
    if loading_preset:
        return
    if args.input.id == 'preset_selector':
        _load_selected_preset(active_command_inputs, 'preset_selector')
        return
    if args.input.id == 'preset_table' or args.input.id.startswith('preset_table_'):
        _show_selected_table_details(active_command_inputs)
        return
    if args.input.id in table_delete_actions:
        if args.input.value:
            args.input.value = False
            _delete_preset(active_command_inputs, table_delete_actions[args.input.id])
        return
    if args.input.id == 'export_presets':
        if args.input.value:
            args.input.value = False
            _export_presets(active_command_inputs)
        return
    if args.input.id == 'import_presets':
        if args.input.value:
            args.input.value = False
            _import_presets(active_command_inputs)
        return
    if args.input.id == 'save_default_tolerance':
        if args.input.value:
            _save_default_tolerance(active_command_inputs)
            args.input.value = False
        return
    if args.input.id == 'save_preset':
        if args.input.value:
            _save_current_preset(active_command_inputs)
            args.input.value = False
        return
    if args.input.id in (
        'target_face',
        'pitch',
        'calculation_mode',
        'flank_angle',
        'thread_depth',
        'fillet_radius',
        'tolerance',
    ):
        _apply_calculation_mode(active_command_inputs)
        _update_result_text(active_command_inputs)


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    _apply_calculation_mode(active_command_inputs)
    parameters = _read_parameters(active_command_inputs)
    errors = _validation_errors(parameters)
    args.areInputsValid = not errors
    _set_result_text(active_command_inputs, errors)


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers, active_command_inputs, available_presets
    global table_delete_actions, table_row_presets
    local_handlers = []
    active_command_inputs = None
    available_presets = []
    table_delete_actions = {}
    table_row_presets = {}


def _input_by_id(inputs, input_id):
    """Sucht auch in Gruppen und Tabs nach einer Dialogeingabe."""
    direct_input = inputs.itemById(input_id)
    if direct_input is not None:
        return direct_input
    for index in range(inputs.count):
        command_input = inputs.item(index)
        children = getattr(command_input, 'children', None)
        if children is not None:
            nested_input = _input_by_id(children, input_id)
            if nested_input is not None:
                return nested_input
    return None


def _refresh_preset_selectors(inputs, selected_id=None):
    global available_presets, loading_preset
    previous_loading_state = loading_preset
    loading_preset = True
    try:
        available_presets = load_thread_presets()
        for selector_id in ('preset_selector',):
            selector = _input_by_id(inputs, selector_id)
            selector.listItems.clear()
            selector.listItems.add(tr('choose_setting'), selected_id is None)
            for preset in available_presets:
                selector.listItems.add(preset['name'], preset.get('id') == selected_id)
        _populate_preset_table(inputs)
    except Exception as error:
        status = _input_by_id(inputs, 'preset_status')
        if status is not None:
            status.text = str(error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)
    finally:
        loading_preset = previous_loading_state


def _populate_preset_table(inputs):
    global table_refresh_serial, table_delete_actions, table_row_presets
    table = _input_by_id(inputs, 'preset_table')
    if table is None:
        return
    table.clear()
    table_delete_actions = {}
    table_row_presets = {}
    table_refresh_serial += 1
    cell_inputs = table.commandInputs
    units = app.activeProduct.unitsManager
    length_units = units.defaultLengthUnits

    rows = [(tr('name'), 'α', 'h', 'P', tr('action'))]
    for preset in available_presets:
        settings = preset.get('settings', {})
        rows.append((
            str(preset.get('name', '')),
            _format_table_value(units, settings.get('flank_angle_rad'), 'deg'),
            _format_table_value(units, settings.get('thread_depth_cm'), length_units),
            _format_table_value(units, settings.get('pitch_cm'), length_units),
            '',
        ))

    for row_index, row_values in enumerate(rows):
        if row_index > 0:
            table_row_presets[row_index] = available_presets[row_index - 1]['id']
        for column_index, value in enumerate(row_values):
            if row_index > 0 and column_index == 4:
                input_id = f'delete_preset_{table_refresh_serial}_{row_index}'
                delete_button = cell_inputs.addBoolValueInput(
                    input_id, tr('delete'), False, '', False
                )
                table.addCommandInput(delete_button, row_index, column_index)
                table_delete_actions[input_id] = available_presets[row_index - 1]['id']
                continue
            text_value = f'<b>{value}</b>' if row_index == 0 else value
            cell = cell_inputs.addTextBoxCommandInput(
                f'preset_table_{table_refresh_serial}_{row_index}_{column_index}',
                '', text_value, 1, True
            )
            table.addCommandInput(cell, row_index, column_index)


def _format_table_value(units, value, unit_name):
    if value is None:
        return '–'
    try:
        return units.formatInternalValue(float(value), unit_name, True)
    except (TypeError, ValueError):
        return '–'


def _save_default_tolerance(inputs):
    status = _input_by_id(inputs, 'default_tolerance_status')
    try:
        dropdown = _input_by_id(inputs, 'default_tolerance')
        selected_name = dropdown.selectedItem.name
        value = dict(TOLERANCE_OPTIONS)[selected_name]
        save_default_tolerance(value)
        _select_dropdown_item(_input_by_id(inputs, 'tolerance'), selected_name)
        status.text = tr('default_saved', value=selected_name)
        _update_result_text(inputs)
    except Exception as error:
        status.text = str(error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)


def _selected_preset(inputs, selector_id):
    selector = _input_by_id(inputs, selector_id)
    if selector is None or selector.selectedItem is None:
        return None
    preset_index = selector.selectedItem.index - 1
    if preset_index < 0 or preset_index >= len(available_presets):
        return None
    return available_presets[preset_index]


def _load_selected_preset(inputs, selector_id):
    global loading_preset
    preset = _selected_preset(inputs, selector_id)
    if preset is None:
        return

    loading_preset = True
    try:
        settings = preset['settings']
        mode_name = (
            ISO_MODE_NAME if settings['calculation_mode'] == 'iso_metric' else FREE_MODE_NAME
        )
        _select_dropdown_item(_input_by_id(inputs, 'calculation_mode'), mode_name)
        _input_by_id(inputs, 'flank_angle').value = float(settings['flank_angle_rad'])
        _input_by_id(inputs, 'thread_depth').value = float(settings['thread_depth_cm'])
        _input_by_id(inputs, 'pitch').value = float(settings['pitch_cm'])
        _input_by_id(inputs, 'fillet_radius').value = float(settings['fillet_radius_cm'])

        tolerance_value = float(settings.get('tolerance_cm', 0.0))
        tolerance_name = min(
            TOLERANCE_OPTIONS, key=lambda option: abs(option[1] - tolerance_value)
        )[0]
        _select_dropdown_item(_input_by_id(inputs, 'tolerance'), tolerance_name)
        _apply_calculation_mode(inputs)
        _update_result_text(inputs)
    except (KeyError, TypeError, ValueError) as error:
        result = _input_by_id(inputs, 'result_text')
        result.text = tr(
            'preset_incomplete', name=preset.get('name', ''), error=error
        )
    finally:
        loading_preset = False


def _select_dropdown_item(dropdown, item_name):
    for index in range(dropdown.listItems.count):
        item = dropdown.listItems.item(index)
        if item.name == item_name:
            item.isSelected = True
            return


def _show_selected_table_details(inputs):
    table = _input_by_id(inputs, 'preset_table')
    details = _input_by_id(inputs, 'management_details')
    preset_id = table_row_presets.get(table.selectedRow) if table is not None else None
    preset = next(
        (item for item in available_presets if item.get('id') == preset_id), None
    )
    if preset is None:
        details.text = tr('no_row')
        return
    settings = preset.get('settings', {})
    mode = tr('profile_mode_iso') if settings.get('calculation_mode') == 'iso_metric' else tr('profile_mode_free')
    units = app.activeProduct.unitsManager
    length_units = units.defaultLengthUnits
    details.text = (
        f'{tr("details_name")}: {preset.get("name", "")}\n'
        f'{tr("note")}: {preset.get("note", "–") or "–"}\n'
        f'{tr("mode")}: {mode}\n'
        f'{tr("profile_angle")}: {_format_table_value(units, settings.get("flank_angle_rad"), "deg")}\n'
        f'{tr("thread_depth")}: {_format_table_value(units, settings.get("thread_depth_cm"), length_units)}\n'
        f'{tr("pitch")}: {_format_table_value(units, settings.get("pitch_cm"), length_units)}\n'
        f'{tr("saved_at")}: {preset.get("created_at", "–")}'
    )


def _delete_preset(inputs, preset_id):
    global available_presets
    preset = next((item for item in available_presets if item.get('id') == preset_id), None)
    if preset is None:
        return
    answer = ui.messageBox(
        tr('confirm_delete', name=preset.get('name', '')),
        'PrintThread Wizard',
        adsk.core.MessageBoxButtonTypes.YesNoButtonType,
        adsk.core.MessageBoxIconTypes.QuestionIconType,
    )
    if answer != adsk.core.DialogResults.DialogYes:
        return
    if delete_thread_preset(preset_id):
        table = _input_by_id(inputs, 'preset_table')
        row = next(
            (row_index for row_index, row_id in table_row_presets.items() if row_id == preset_id),
            None,
        )
        if table is not None and row is not None:
            for column in range(5):
                cell_input = table.getInputAtPosition(row, column)
                if cell_input is not None:
                    cell_input.isVisible = False
        table_row_presets.pop(row, None)
        available_presets = load_thread_presets()
        _refresh_quick_selector(inputs)
        _input_by_id(inputs, 'management_details').text = (
            tr('deleted', name=preset.get('name', ''))
        )


def _refresh_quick_selector(inputs):
    global loading_preset
    previous_loading_state = loading_preset
    loading_preset = True
    try:
        selector = _input_by_id(inputs, 'preset_selector')
        selector.listItems.clear()
        selector.listItems.add(tr('choose_setting'), True)
        for preset in available_presets:
            selector.listItems.add(preset['name'], False)
    finally:
        loading_preset = previous_loading_state


def _export_presets(inputs):
    status = _input_by_id(inputs, 'transfer_status')
    try:
        dialog = ui.createFileDialog()
        dialog.title = tr('export_title')
        dialog.filter = 'JSON-Dateien (*.json)'
        dialog.initialFilename = 'PrintThreadWizard-Einstellungen.json'
        if dialog.showSave() != adsk.core.DialogResults.DialogOK:
            status.text = tr('export_cancelled')
            return
        filename = dialog.filename
        if not filename.lower().endswith('.json'):
            filename += '.json'
        count = export_thread_presets(filename)
        status.text = tr('export_ok', count=count)
    except Exception as error:
        status.text = tr('export_failed', error=error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)


def _import_presets(inputs):
    status = _input_by_id(inputs, 'transfer_status')
    try:
        dialog = ui.createFileDialog()
        dialog.title = tr('import_title')
        dialog.filter = 'JSON-Dateien (*.json)'
        dialog.isMultiSelectEnabled = False
        if dialog.showOpen() != adsk.core.DialogResults.DialogOK:
            status.text = tr('import_cancelled')
            return
        count = import_thread_presets(dialog.filename)
        _refresh_preset_selectors(inputs)
        default_name = _tolerance_name(load_default_tolerance())
        _select_dropdown_item(_input_by_id(inputs, 'default_tolerance'), default_name)
        status.text = tr('import_ok', count=count)
    except Exception as error:
        status.text = tr('import_failed', error=error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)


def _read_parameters(inputs):
    face_input = _input_by_id(inputs, 'target_face')
    face = face_input.selection(0).entity if face_input and face_input.selectionCount else None

    edge_input = _input_by_id(inputs, 'chamfer_edges')
    edges = tuple(
        edge_input.selection(index).entity for index in range(edge_input.selectionCount)
    ) if edge_input else ()

    return ThreadParameters(
        face=face,
        chamfer_edges=edges,
        flank_angle=_input_by_id(inputs, 'flank_angle').value,
        thread_depth=_input_by_id(inputs, 'thread_depth').value,
        pitch=_input_by_id(inputs, 'pitch').value,
        fillet_radius=_input_by_id(inputs, 'fillet_radius').value,
        tolerance=_selected_tolerance(inputs),
    )


def _selected_tolerance(inputs):
    tolerance_input = _input_by_id(inputs, 'tolerance')
    selected_name = (
        tolerance_input.selectedItem.name
        if tolerance_input and tolerance_input.selectedItem
        else FALLBACK_TOLERANCE_NAME
    )
    return dict(TOLERANCE_OPTIONS)[selected_name]


def _tolerance_name(value):
    return min(TOLERANCE_OPTIONS, key=lambda option: abs(option[1] - value))[0]


def _save_current_preset(inputs):
    status = _input_by_id(inputs, 'preset_status')
    try:
        _apply_calculation_mode(inputs)
        parameters = _read_parameters(inputs)
        parameter_errors = [
            error for error in parameters.validation_errors()
            if error != 'Eine Zylinderfläche muss ausgewählt werden.'
        ]
        if parameter_errors:
            raise ValueError('\n'.join(parameter_errors))

        context = _preset_face_context(parameters.face)
        settings = {
            'calculation_mode': 'iso_metric' if _is_iso_mode(inputs) else 'free',
            'flank_angle_rad': parameters.flank_angle,
            'thread_depth_cm': parameters.thread_depth,
            'pitch_cm': parameters.pitch,
            'fillet_radius_cm': parameters.fillet_radius,
            'tolerance_cm': parameters.tolerance,
            'display_length_units': app.activeProduct.unitsManager.defaultLengthUnits,
            **context,
        }
        preset = save_thread_preset(
            _input_by_id(inputs, 'preset_name').value,
            _input_by_id(inputs, 'preset_note').text,
            settings,
        )
        status.text = tr('saved', name=preset['name'])
        _refresh_preset_selectors(inputs, preset['id'])
        futil.log(f'{CMD_NAME}: Gewindeeinstellung „{preset["name"]}“ gespeichert.')
    except Exception as error:
        status.text = str(error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)


def _preset_face_context(face):
    if face is None:
        return {}
    try:
        cylinder = analyze_cylinder(face)
        return {
            'thread_type': 'external' if cylinder.is_external else 'internal',
            'nominal_diameter_cm': cylinder.radius * 2,
        }
    except ValueError:
        return {}


def _is_iso_mode(inputs):
    mode_input = _input_by_id(inputs, 'calculation_mode')
    return bool(mode_input and mode_input.selectedItem.name == ISO_MODE_NAME)


def _apply_calculation_mode(inputs):
    global updating_calculated_inputs
    if updating_calculated_inputs:
        return

    angle_input = _input_by_id(inputs, 'flank_angle')
    depth_input = _input_by_id(inputs, 'thread_depth')
    pitch_input = _input_by_id(inputs, 'pitch')
    is_iso = _is_iso_mode(inputs)
    angle_input.isEnabled = not is_iso
    depth_input.isEnabled = not is_iso
    if not is_iso or pitch_input.value <= 0:
        return

    is_external = True
    face_input = _input_by_id(inputs, 'target_face')
    if face_input and face_input.selectionCount:
        try:
            is_external = analyze_cylinder(face_input.selection(0).entity).is_external
        except ValueError:
            pass

    updating_calculated_inputs = True
    try:
        angle_input.value = ISO_FLANK_ANGLE
        depth_input.value = radial_thread_depth(pitch_input.value, is_external)
    finally:
        updating_calculated_inputs = False


def _validation_errors(parameters):
    errors = parameters.validation_errors()
    if parameters.face is not None:
        try:
            cylinder = analyze_cylinder(parameters.face)
            effective_radius = (
                cylinder.radius
                + parameters.tolerance_radius_offset(cylinder.is_external)
            )
            if effective_radius <= 0:
                errors.append('Die Toleranz ist für diesen Zylinderdurchmesser zu groß.')
            if parameters.sharp_profile_depth >= effective_radius:
                errors.append('Die Gewindetiefe muss kleiner als der Zylinderradius sein.')
        except ValueError as error:
            errors.append(str(error))
    return errors


def _update_result_text(inputs):
    parameters = _read_parameters(inputs)
    errors = _validation_errors(parameters)
    _set_result_text(inputs, errors)


def _set_result_text(inputs, errors):
    result = _input_by_id(inputs, 'result_text')
    if result is None:
        return
    if errors:
        result.text = '\n'.join(errors)
        return

    cylinder = analyze_cylinder(_read_parameters(inputs).face)
    units = app.activeProduct.unitsManager
    nominal_diameter = units.formatInternalValue(
        cylinder.radius * 2, units.defaultLengthUnits, True
    )
    parameters = _read_parameters(inputs)
    effective_radius = (
        cylinder.radius + parameters.tolerance_radius_offset(cylinder.is_external)
    )
    diameter = units.formatInternalValue(
        effective_radius * 2, units.defaultLengthUnits, True
    )
    core_value = effective_radius * 2 - 2 * parameters.thread_depth
    core_diameter = units.formatInternalValue(
        core_value, units.defaultLengthUnits, True
    )
    pitch_diameter = units.formatInternalValue(
        effective_radius * 2 - parameters.thread_depth,
        units.defaultLengthUnits,
        True,
    )
    pitch_value = units.formatInternalValue(
        parameters.pitch, units.defaultLengthUnits, True
    )
    angle_value = units.formatInternalValue(parameters.flank_angle, 'deg', True)
    mode_text = tr('profile_mode_iso') if _is_iso_mode(inputs) else tr('profile_mode_free')
    selected_tolerance = next(
        name for name, value in TOLERANCE_OPTIONS if value == parameters.tolerance
    )
    thread_type = tr('external_thread') if cylinder.is_external else tr('internal_thread')
    bore_diameter = tr('internal_only') if cylinder.is_external else core_diameter
    result.text = (
        f'{thread_type} – {tr("nominal_diameter")}: {nominal_diameter}\n'
        f'{tr("pitch")}: {pitch_value}\n'
        f'{tr("major_diameter")}: {diameter}\n'
        f'{tr("pitch_diameter")}: {pitch_diameter}\n'
        f'{tr("minor_diameter")}: {core_diameter}\n'
        f'{tr("tap_drill")}: {bore_diameter}\n'
        f'{tr("profile_angle")}: {angle_value}\n'
        f'{tr("tolerance")}: {selected_tolerance}\n'
        f'{tr("mode")}: {mode_text}'
    )
