import os

import adsk.core
import adsk.fusion

from ... import config
from ...core.iso_metric import ISO_FLANK_ANGLE, radial_thread_depth
from ...core.thread_parameters import ThreadParameters
from ...core.thread_presets import load_thread_presets, save_thread_preset
from ...fusion.face_analysis import analyze_cylinder
from ...fusion.thread_geometry import create_thread
from ...lib import fusionAddInUtils as futil
from ...version import VERSION


app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = f'PrintThread Wizard {VERSION}'
CMD_DESCRIPTION = 'Dialogbasis für die neue Entwicklung des PrintThread Wizard.'

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
IS_PROMOTED = True

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')
THREAD_DIMENSIONS_IMAGE = os.path.join(ICON_FOLDER, 'thread_dimensions.png')

local_handlers = []
updating_calculated_inputs = False
active_command_inputs = None
available_presets = []
loading_preset = False

ISO_MODE_NAME = 'ISO metrisch automatisch'
FREE_MODE_NAME = 'Freie Geometrie'
TOLERANCE_OPTIONS = (
    ('0,0 mm', 0.0),
    ('0,1 mm', 0.01),
    ('0,2 mm', 0.02),
    ('0,3 mm', 0.03),
    ('0,4 mm', 0.04),
    ('0,5 mm', 0.05),
)
DEFAULT_TOLERANCE_NAME = '0,2 mm'


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
        'version_info', 'Version', f'PrintThread Wizard {VERSION}', 1, True
    )
    version_text.isFullWidth = True

    create_tab = inputs.addTabCommandInput('create_tab', 'Gewinde erstellen')
    create_inputs = create_tab.children
    management_tab = inputs.addTabCommandInput('management_tab', 'Einstellungen verwalten')
    management_inputs = management_tab.children

    face_input = create_inputs.addSelectionInput(
        'target_face', 'Zylinderfläche', 'Wählen Sie eine Zylinderfläche aus.'
    )
    face_input.addSelectionFilter('Faces')
    face_input.setSelectionLimits(1, 1)

    edge_input = create_inputs.addSelectionInput(
        'chamfer_edges', 'Fasen-Kanten', 'Optional eine oder zwei Zylinderkanten auswählen.'
    )
    edge_input.addSelectionFilter('Edges')
    edge_input.setSelectionLimits(0, 2)

    preset_selector = create_inputs.addDropDownCommandInput(
        'preset_selector', 'Gespeicherte Einstellung',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )

    default_units = app.activeProduct.unitsManager.defaultLengthUnits
    mode_input = create_inputs.addDropDownCommandInput(
        'calculation_mode', 'Berechnung', adsk.core.DropDownStyles.TextListDropDownStyle
    )
    mode_input.listItems.add(ISO_MODE_NAME, True)
    mode_input.listItems.add(FREE_MODE_NAME, False)

    create_inputs.addValueInput(
        'flank_angle', 'Profilwinkel (α)', 'deg', adsk.core.ValueInput.createByString('60 deg')
    )
    create_inputs.addValueInput(
        'thread_depth', 'Gewindetiefe (h)', default_units,
        adsk.core.ValueInput.createByString(f'5 {default_units}')
    )
    create_inputs.addValueInput(
        'pitch', 'Gewindesteigung (P)', default_units,
        adsk.core.ValueInput.createByString(f'10 {default_units}')
    )
    create_inputs.addValueInput(
        'fillet_radius', 'Verrundungsradius (r)', default_units,
        adsk.core.ValueInput.createByString('0.4 mm')
    )
    tolerance_input = create_inputs.addDropDownCommandInput(
        'tolerance', 'Toleranz', adsk.core.DropDownStyles.TextListDropDownStyle
    )
    for name, _ in TOLERANCE_OPTIONS:
        tolerance_input.listItems.add(name, name == DEFAULT_TOLERANCE_NAME)

    result_text = create_inputs.addTextBoxCommandInput(
        'result_text', 'Ergebnis',
        'Bitte eine Zylinderfläche auswählen.', 9, True
    )
    result_text.isFullWidth = True

    dimensions_group = create_inputs.addGroupCommandInput(
        'dimensions_group', 'Skizze der Gewindeparameter'
    )
    dimensions_image = dimensions_group.children.addImageCommandInput(
        'thread_dimensions_image', '', THREAD_DIMENSIONS_IMAGE
    )
    dimensions_image.isFullWidth = True

    management_selector = management_inputs.addDropDownCommandInput(
        'management_selector', 'Gespeicherte Einstellungen',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    management_details = management_inputs.addTextBoxCommandInput(
        'management_details', 'Details', 'Noch keine Einstellung ausgewählt.', 4, True
    )
    management_details.isFullWidth = True

    preset_group = create_inputs.addGroupCommandInput(
        'preset_group', 'Aktuelle Einstellungen speichern'
    )
    preset_inputs = preset_group.children
    preset_inputs.addStringValueInput('preset_name', 'Gewindebezeichner', '')
    preset_inputs.addTextBoxCommandInput(
        'preset_note', 'Kurze Notiz', '', 2, False
    )
    preset_inputs.addBoolValueInput(
        'save_preset', 'Aktuelle Einstellungen speichern', False, '', False
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
    if args.input.id == 'management_selector':
        _show_selected_preset_details(active_command_inputs)
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
    local_handlers = []
    active_command_inputs = None
    available_presets = []


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
        for selector_id in ('preset_selector', 'management_selector'):
            selector = _input_by_id(inputs, selector_id)
            selector.listItems.clear()
            selector.listItems.add('— Einstellung auswählen —', selected_id is None)
            for preset in available_presets:
                selector.listItems.add(preset['name'], preset.get('id') == selected_id)
        if selected_id is not None:
            _show_selected_preset_details(inputs)
    except Exception as error:
        status = _input_by_id(inputs, 'preset_status')
        if status is not None:
            status.text = str(error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)
    finally:
        loading_preset = previous_loading_state


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
        result.text = f'Die Einstellung „{preset.get("name", "") }“ ist unvollständig: {error}'
    finally:
        loading_preset = False


def _select_dropdown_item(dropdown, item_name):
    for index in range(dropdown.listItems.count):
        item = dropdown.listItems.item(index)
        if item.name == item_name:
            item.isSelected = True
            return


def _show_selected_preset_details(inputs):
    preset = _selected_preset(inputs, 'management_selector')
    details = _input_by_id(inputs, 'management_details')
    if preset is None:
        details.text = 'Noch keine Einstellung ausgewählt.'
        return
    settings = preset.get('settings', {})
    mode = 'ISO metrisch' if settings.get('calculation_mode') == 'iso_metric' else 'Freie Geometrie'
    details.text = (
        f'Bezeichner: {preset.get("name", "")}\n'
        f'Notiz: {preset.get("note", "–") or "–"}\n'
        f'Modus: {mode}\n'
        f'Gespeichert: {preset.get("created_at", "–")}'
    )


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
        else DEFAULT_TOLERANCE_NAME
    )
    return dict(TOLERANCE_OPTIONS)[selected_name]


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
        status.text = f'„{preset["name"]}“ wurde gespeichert.'
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
    mode_text = 'ISO metrisch' if _is_iso_mode(inputs) else 'Freie Geometrie'
    selected_tolerance = next(
        name for name, value in TOLERANCE_OPTIONS if value == parameters.tolerance
    )
    thread_type = 'Außengewinde' if cylinder.is_external else 'Innengewinde'
    bore_diameter = '– (nur Innengewinde)' if cylinder.is_external else core_diameter
    result.text = (
        f'{thread_type} – Nenndurchmesser: {nominal_diameter}\n'
        f'Gewindesteigung (P): {pitch_value}\n'
        f'Außendurchmesser (d): {diameter}\n'
        f'Teilkreisdurchmesser (d2): {pitch_diameter}\n'
        f'Innendurchmesser (d1): {core_diameter}\n'
        f'Gewindebohrung (T): {bore_diameter}\n'
        f'Profilwinkel (α): {angle_value}\n'
        f'Toleranz: {selected_tolerance}\n'
        f'Modus: {mode_text}'
    )
