import os
import adsk.core
import adsk.fusion
from ...lib import fusionAddInUtils as futil
from ... import config
from ...version import VERSION

app = adsk.core.Application.get()
ui = app.userInterface


CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = f'PrintThread Wizard {VERSION}'
CMD_Description = 'Select a cylindrical face and show its basic thread input data.'

IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
COMMAND_BESIDE_ID = ''

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

local_handlers = []


def start():
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def is None:
        cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    futil.add_handler(cmd_def.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace is None:
        ui.messageBox('PrintThread Wizard: Der Arbeitsbereich Konstruktion konnte nicht gefunden werden.')
        return

    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    if panel is None:
        ui.messageBox('PrintThread Wizard: Der Bereich Erstellen konnte nicht gefunden werden.')
        return

    control = panel.controls.itemById(CMD_ID)
    if control is None:
        if COMMAND_BESIDE_ID:
            control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
        else:
            control = panel.controls.addCommand(cmd_def)

    control.isPromoted = IS_PROMOTED


def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
    command_control = panel.controls.itemById(CMD_ID) if panel else None
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    if command_control:
        command_control.deleteMe()

    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} Command Created Event')

    inputs = args.command.commandInputs

    version_text = inputs.addTextBoxCommandInput(
        'version_info',
        'Version',
        f'PrintThread Wizard {VERSION}',
        1,
        True
    )
    version_text.isFullWidth = True

    selection_input = inputs.addSelectionInput(
        'target_face',
        'Zylinderfläche',
        'Wählen Sie eine Zylinderfläche aus.'
    )
    selection_input.addSelectionFilter('Faces')
    selection_input.setSelectionLimits(1, 1)

    edge_input = inputs.addSelectionInput(
        'chamfer_edges',
        'Fasen-Kanten',
        'Optional eine oder zwei Zylinderkanten auswählen.'
    )
    edge_input.addSelectionFilter('Edges')
    edge_input.setSelectionLimits(0, 2)

    result_text = inputs.addTextBoxCommandInput(
        'result_text',
        'Ergebnis',
        'Noch keine Fläche ausgewählt.',
        4,
        True
    )
    result_text.isFullWidth = True

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Execute Event')
    _update_result_text(args.command.commandInputs)
    _create_cylinder_axis(args.command.commandInputs)


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {args.input.id}')

    if args.input.id in ('target_face', 'chamfer_edges'):
        _update_result_text(args.inputs)


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    futil.log(f'{CMD_NAME} Validate Input Event')
    _update_result_text(args.inputs)
    args.areInputsValid = _get_selected_cylinder_face(args.inputs) is not None


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []


def _update_result_text(inputs: adsk.core.CommandInputs):
    result_text: adsk.core.TextBoxCommandInput = inputs.itemById('result_text')
    if result_text is None:
        return

    selection_input: adsk.core.SelectionCommandInput = inputs.itemById('target_face')
    if selection_input is None or selection_input.selectionCount == 0:
        result_text.text = 'Noch keine Fläche ausgewählt.'
        return

    result = _get_selected_cylinder_info_text(inputs)
    if result:
        result_text.text = result
    else:
        result_text.text = 'Die ausgewählte Fläche ist keine Zylinderfläche.'


def _get_selected_cylinder_info_text(inputs: adsk.core.CommandInputs):
    face = _get_selected_cylinder_face(inputs)
    if face is None:
        return None

    cylinder = face.geometry
    radius = getattr(cylinder, 'radius', None)
    if radius is None:
        return None

    units_manager = app.activeProduct.unitsManager
    default_units = units_manager.defaultLengthUnits
    diameter_text = units_manager.formatInternalValue(radius * 2, default_units, True)
    side_type = _get_cylinder_side_type(face)
    edge_count = _get_selected_edge_count(inputs)
    edge_text = _format_selected_edge_count(edge_count)

    return f'Durchmesser der Zylinderfläche: {diameter_text}<br>Typ: {side_type}<br>Ausgewählte Fasen-Kanten: {edge_text}'


def _create_cylinder_axis(inputs: adsk.core.CommandInputs):
    face = _get_selected_cylinder_face(inputs)
    if face is None:
        return

    axis_points = _get_cylinder_axis_points(face)
    if axis_points is None:
        ui.messageBox('Die Zylinderachse konnte nicht ermittelt werden.')
        return

    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        ui.messageBox('Aktives Fusion-Design konnte nicht gelesen werden.')
        return

    component = design.activeComponent if design.activeComponent else design.rootComponent
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = f'PrintThread Wizard Achse {VERSION}'
    sketch.is3D = True
    line = sketch.sketchCurves.sketchLines.addByTwoPoints(axis_points[0], axis_points[1])
    line.isConstruction = True


def _get_cylinder_axis_points(face: adsk.fusion.BRepFace):
    centers = _get_cylinder_edge_centers(face)
    if len(centers) >= 2:
        return _farthest_point_pair(centers)

    cylinder = face.geometry
    origin = getattr(cylinder, 'origin', None)
    axis = getattr(cylinder, 'axis', None)
    if origin is None or axis is None:
        return None

    axis_vector = axis.copy()
    if not axis_vector.normalize():
        return None

    distances = []
    box = face.boundingBox
    for x in (box.minPoint.x, box.maxPoint.x):
        for y in (box.minPoint.y, box.maxPoint.y):
            for z in (box.minPoint.z, box.maxPoint.z):
                point = adsk.core.Point3D.create(x, y, z)
                distances.append(origin.vectorTo(point).dotProduct(axis_vector))

    if not distances:
        return None

    start_point = origin.copy()
    start_offset = axis_vector.copy()
    start_offset.scaleBy(min(distances))
    start_point.translateBy(start_offset)

    end_point = origin.copy()
    end_offset = axis_vector.copy()
    end_offset.scaleBy(max(distances))
    end_point.translateBy(end_offset)

    return start_point, end_point


def _get_cylinder_edge_centers(face: adsk.fusion.BRepFace):
    centers = []
    tolerance = 1e-5

    try:
        edges = face.edges
        for index in range(edges.count):
            geometry = getattr(edges.item(index), 'geometry', None)
            center = getattr(geometry, 'center', None)
            if center is None:
                continue

            if not any(center.distanceTo(existing) < tolerance for existing in centers):
                centers.append(center)
    except:
        pass

    return centers


def _farthest_point_pair(points):
    if len(points) < 2:
        return None

    best_pair = (points[0], points[1])
    best_distance = points[0].distanceTo(points[1])
    for first_index in range(len(points)):
        for second_index in range(first_index + 1, len(points)):
            distance = points[first_index].distanceTo(points[second_index])
            if distance > best_distance:
                best_distance = distance
                best_pair = (points[first_index], points[second_index])

    return best_pair


def _get_selected_edge_count(inputs: adsk.core.CommandInputs):
    edge_input: adsk.core.SelectionCommandInput = inputs.itemById('chamfer_edges')
    if edge_input is None:
        return 0

    return edge_input.selectionCount


def _format_selected_edge_count(edge_count: int):
    if edge_count == 0:
        return 'keine'

    if edge_count == 1:
        return '1'

    return '2'


def _get_cylinder_side_type(face: adsk.fusion.BRepFace):
    cylinder = face.geometry
    origin = getattr(cylinder, 'origin', None)
    axis = getattr(cylinder, 'axis', None)
    point = getattr(face, 'pointOnFace', None)
    if origin is None or axis is None or point is None:
        return 'nicht eindeutig erkennbar'

    axis_vector = axis.copy()
    if not axis_vector.normalize():
        return 'nicht eindeutig erkennbar'

    vector_to_point = origin.vectorTo(point)
    axis_offset = axis_vector.copy()
    axis_offset.scaleBy(vector_to_point.dotProduct(axis_vector))

    closest_axis_point = origin.copy()
    closest_axis_point.translateBy(axis_offset)
    radial_vector = closest_axis_point.vectorTo(point)
    if not radial_vector.normalize():
        return 'nicht eindeutig erkennbar'

    normal_result = face.evaluator.getNormalAtPoint(point)
    if not normal_result or not normal_result[0]:
        return 'nicht eindeutig erkennbar'

    normal = normal_result[1]
    if not normal.normalize():
        return 'nicht eindeutig erkennbar'

    if normal.dotProduct(radial_vector) >= 0:
        return 'Außenfläche'

    return 'Innenfläche'


def _get_selected_cylinder_face(inputs: adsk.core.CommandInputs):
    selection_input: adsk.core.SelectionCommandInput = inputs.itemById('target_face')
    if selection_input is None or selection_input.selectionCount == 0:
        return None

    entity = selection_input.selection(0).entity
    face = adsk.fusion.BRepFace.cast(entity)
    if face is None:
        return None

    if getattr(face.geometry, 'radius', None) is None:
        return None

    return face
