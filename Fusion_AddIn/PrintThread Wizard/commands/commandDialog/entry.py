import os

import adsk.core
import adsk.fusion

from ... import config
from ...core.iso_metric import ISO_FLANK_ANGLE, radial_thread_depth
from ...core.thread_parameters import ThreadParameters
from ...core.thread_presets import save_thread_preset
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

local_handlers = []
updating_calculated_inputs = False
active_command_inputs = None

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

    face_input = inputs.addSelectionInput(
        'target_face', 'Zylinderfläche', 'Wählen Sie eine Zylinderfläche aus.'
    )
    face_input.addSelectionFilter('Faces')
    face_input.setSelectionLimits(1, 1)

    edge_input = inputs.addSelectionInput(
        'chamfer_edges', 'Fasen-Kanten', 'Optional eine oder zwei Zylinderkanten auswählen.'
    )
    edge_input.addSelectionFilter('Edges')
    edge_input.setSelectionLimits(0, 2)

    default_units = app.activeProduct.unitsManager.defaultLengthUnits
    mode_input = inputs.addDropDownCommandInput(
        'calculation_mode', 'Berechnung', adsk.core.DropDownStyles.TextListDropDownStyle
    )
    mode_input.listItems.add(ISO_MODE_NAME, True)
    mode_input.listItems.add(FREE_MODE_NAME, False)

    inputs.addValueInput(
        'flank_angle', 'Flankenwinkel', 'deg', adsk.core.ValueInput.createByString('60 deg')
    )
    inputs.addValueInput(
        'thread_depth', 'Gewindetiefe', default_units,
        adsk.core.ValueInput.createByString(f'5 {default_units}')
    )
    inputs.addValueInput(
        'pitch', 'Steigung', default_units,
        adsk.core.ValueInput.createByString(f'10 {default_units}')
    )
    inputs.addValueInput(
        'fillet_radius', 'Verrundungsradius', default_units,
        adsk.core.ValueInput.createByString('0.4 mm')
    )
    tolerance_input = inputs.addDropDownCommandInput(
        'tolerance', 'Toleranz', adsk.core.DropDownStyles.TextListDropDownStyle
    )
    for name, _ in TOLERANCE_OPTIONS:
        tolerance_input.listItems.add(name, name == DEFAULT_TOLERANCE_NAME)

    result_text = inputs.addTextBoxCommandInput(
        'result_text', 'Ergebnis',
        'Neustart der Entwicklung – noch keine Funktion hinterlegt.', 5, True
    )
    result_text.isFullWidth = True

    preset_group = inputs.addGroupCommandInput('preset_group', 'Einstellungen speichern')
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
        _apply_calculation_mode(args.inputs)
        _update_result_text(args.inputs)


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    _apply_calculation_mode(args.inputs)
    parameters = _read_parameters(args.inputs)
    errors = _validation_errors(parameters)
    args.areInputsValid = not errors
    _set_result_text(args.inputs, errors)


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers, active_command_inputs
    local_handlers = []
    active_command_inputs = None


def _read_parameters(inputs):
    face_input = inputs.itemById('target_face')
    face = face_input.selection(0).entity if face_input and face_input.selectionCount else None

    edge_input = inputs.itemById('chamfer_edges')
    edges = tuple(
        edge_input.selection(index).entity for index in range(edge_input.selectionCount)
    ) if edge_input else ()

    return ThreadParameters(
        face=face,
        chamfer_edges=edges,
        flank_angle=inputs.itemById('flank_angle').value,
        thread_depth=inputs.itemById('thread_depth').value,
        pitch=inputs.itemById('pitch').value,
        fillet_radius=inputs.itemById('fillet_radius').value,
        tolerance=_selected_tolerance(inputs),
    )


def _selected_tolerance(inputs):
    tolerance_input = inputs.itemById('tolerance')
    selected_name = (
        tolerance_input.selectedItem.name
        if tolerance_input and tolerance_input.selectedItem
        else DEFAULT_TOLERANCE_NAME
    )
    return dict(TOLERANCE_OPTIONS)[selected_name]


def _save_current_preset(inputs):
    status = inputs.itemById('preset_status')
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
            inputs.itemById('preset_name').value,
            inputs.itemById('preset_note').text,
            settings,
        )
        status.text = f'„{preset["name"]}“ wurde gespeichert.'
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
    mode_input = inputs.itemById('calculation_mode')
    return bool(mode_input and mode_input.selectedItem.name == ISO_MODE_NAME)


def _apply_calculation_mode(inputs):
    global updating_calculated_inputs
    if updating_calculated_inputs:
        return

    angle_input = inputs.itemById('flank_angle')
    depth_input = inputs.itemById('thread_depth')
    pitch_input = inputs.itemById('pitch')
    is_iso = _is_iso_mode(inputs)
    angle_input.isEnabled = not is_iso
    depth_input.isEnabled = not is_iso
    if not is_iso or pitch_input.value <= 0:
        return

    is_external = True
    face_input = inputs.itemById('target_face')
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
    result = inputs.itemById('result_text')
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
    mode_text = 'ISO metrisch' if _is_iso_mode(inputs) else 'Freie Geometrie'
    selected_tolerance = next(
        name for name, value in TOLERANCE_OPTIONS if value == parameters.tolerance
    )
    if cylinder.is_external:
        result.text = (
            f'Außengewinde auf Nenndurchmesser {nominal_diameter}\n'
            f'Tolerierter Durchmesser: {diameter}\n'
            f'Kerndurchmesser: {core_diameter}\n'
            f'Toleranz: {selected_tolerance}\n'
            f'Modus: {mode_text}'
        )
    else:
        result.text = (
            f'Innengewinde auf Nenndurchmesser {nominal_diameter}\n'
            f'Tolerierter Durchmesser: {diameter}\n'
            f'Kerndurchmesser: {core_diameter}\n'
            f'Toleranz: {selected_tolerance}\n'
            f'Modus: {mode_text}'
        )
