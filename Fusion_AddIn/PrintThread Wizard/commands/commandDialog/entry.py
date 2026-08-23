import os

import adsk.core

from ... import config
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
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    """Version 0.7 führt bewusst noch keine Modelloperation aus."""
    futil.log(f'{CMD_NAME}: Dialog bestätigt; noch keine Operation implementiert.')


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    args.areInputsValid = True


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
