import os

import adsk.core
import adsk.fusion

from ... import config
from ...core.thread_parameters import ThreadParameters
from ...fusion.face_analysis import analyze_external_cylinder
from ...fusion.thread_geometry import create_external_thread
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
    inputs = args.command.commandInputs

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
    inputs.addValueInput(
        'flank_angle', 'Flankenwinkel', 'deg', adsk.core.ValueInput.createByString('80 deg')
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

    result_text = inputs.addTextBoxCommandInput(
        'result_text', 'Ergebnis',
        'Neustart der Entwicklung – noch keine Funktion hinterlegt.', 3, True
    )
    result_text.isFullWidth = True

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    try:
        parameters = _read_parameters(args.command.commandInputs)
        errors = _validation_errors(parameters)
        if errors:
            raise ValueError('\n'.join(errors))

        create_external_thread(parameters)
        futil.log(f'{CMD_NAME}: Außengewinde erfolgreich erzeugt.')
    except Exception as error:
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)
        ui.messageBox(f'PrintThread Wizard:\n{error}')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    if args.input.id == 'target_face':
        _update_result_text(args.inputs)


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    parameters = _read_parameters(args.inputs)
    errors = _validation_errors(parameters)
    args.areInputsValid = not errors
    _set_result_text(args.inputs, errors)


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []


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
    )


def _validation_errors(parameters):
    errors = parameters.validation_errors()
    if parameters.face is not None:
        try:
            analyze_external_cylinder(parameters.face)
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
        result.text = '<br>'.join(errors)
        return

    cylinder = analyze_external_cylinder(_read_parameters(inputs).face)
    units = app.activeProduct.unitsManager
    diameter = units.formatInternalValue(
        cylinder.radius * 2, units.defaultLengthUnits, True
    )
    result.text = (
        f'Außengewinde auf Nenndurchmesser {diameter}<br>'
        'Das Gewinde wird radial nach innen geschnitten.'
    )
