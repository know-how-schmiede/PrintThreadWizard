import os
import math
import adsk.core
import adsk.fusion
from ...lib import fusionAddInUtils as futil
from ... import config
from ...version import VERSION

app = adsk.core.Application.get()
ui = app.userInterface


CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = f'PrintThread Wizard {VERSION}'
CMD_Description = 'Select a cylindrical face and create a first helix curve.'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
COMMAND_BESIDE_ID = ''
PROFILE_OVERLAP_MM = 0.2

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def is None:
        cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace is None:
        ui.messageBox('PrintThread Wizard: The Fusion design workspace could not be found.')
        return

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    if panel is None:
        ui.messageBox('PrintThread Wizard: The Fusion create panel could not be found.')
        return

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.itemById(CMD_ID)
    if control is None:
        if COMMAND_BESIDE_ID:
            control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
        else:
            control = panel.controls.addCommand(cmd_def)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
    command_control = panel.controls.itemById(CMD_ID) if panel else None
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
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

    result_text = inputs.addTextBoxCommandInput(
        'result_text',
        'Ergebnis',
        'Noch keine Fläche ausgewählt.',
        3,
        True
    )
    result_text.isFullWidth = True

    start_side_input = inputs.addDropDownCommandInput(
        'start_side',
        'Startseite',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    start_side_input.listItems.add('Grundfläche', True, '')
    start_side_input.listItems.add('Deckfläche', False, '')

    default_units = app.activeProduct.unitsManager.defaultLengthUnits
    pitch_value = adsk.core.ValueInput.createByString(f'10 {default_units}')
    inputs.addValueInput('pitch', 'Steigung', default_units, pitch_value)

    length_value = adsk.core.ValueInput.createByString(f'30 {default_units}')
    angle_value = adsk.core.ValueInput.createByString('80 deg')
    depth_value = adsk.core.ValueInput.createByString(f'5 {default_units}')
    inputs.addValueInput('thread_length', 'Gewindelänge', default_units, length_value)
    inputs.addValueInput('profile_angle', 'Öffnungswinkel', 'deg', angle_value)
    inputs.addValueInput('thread_depth', 'Gewindetiefe', default_units, depth_value)

    # TODO Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')

    result = _get_selected_cylinder_info_text(args.command.commandInputs)
    if not result:
        return

    helix_result = _create_helix(args.command.commandInputs)
    ui.messageBox(f'{result}<br>{helix_result}')


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs

    # General logging for debug.
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')

    if changed_input.id == 'target_face':
        _update_result_text(inputs)


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Validate Input Event')

    _update_result_text(args.inputs)
    pitch_input: adsk.core.ValueCommandInput = args.inputs.itemById('pitch')
    length_input: adsk.core.ValueCommandInput = args.inputs.itemById('thread_length')
    angle_input: adsk.core.ValueCommandInput = args.inputs.itemById('profile_angle')
    depth_input: adsk.core.ValueCommandInput = args.inputs.itemById('thread_depth')
    args.areInputsValid = (
        _get_selected_cylinder_face(args.inputs) is not None
        and pitch_input is not None
        and length_input is not None
        and angle_input is not None
        and depth_input is not None
        and pitch_input.value > 0
        and length_input.value > 0
        and 0 < angle_input.value < math.pi
        and depth_input.value > 0
    )
        

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
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

    diameter = radius * 2
    units_manager = app.activeProduct.unitsManager
    default_units = units_manager.defaultLengthUnits
    diameter_text = units_manager.formatInternalValue(diameter, default_units, True)
    side_type = _get_cylinder_side_type(face)
    return f'Durchmesser der Zylinderfläche: {diameter_text}<br>Typ: {side_type}'


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


def _create_helix(inputs: adsk.core.CommandInputs):
    face = _get_selected_cylinder_face(inputs)
    if face is None:
        return 'Keine Zylinderfläche ausgewählt.'

    pitch_input: adsk.core.ValueCommandInput = inputs.itemById('pitch')
    length_input: adsk.core.ValueCommandInput = inputs.itemById('thread_length')
    angle_input: adsk.core.ValueCommandInput = inputs.itemById('profile_angle')
    depth_input: adsk.core.ValueCommandInput = inputs.itemById('thread_depth')
    start_side_input: adsk.core.DropDownCommandInput = inputs.itemById('start_side')
    if (
        pitch_input is None
        or length_input is None
        or angle_input is None
        or depth_input is None
        or start_side_input is None
    ):
        return 'Helix-Parameter konnten nicht gelesen werden.'

    cylinder = face.geometry
    axis = cylinder.axis.copy()
    if not axis.normalize():
        return 'Zylinderachse konnte nicht gelesen werden.'

    radius = cylinder.radius
    length = length_input.value
    pitch = pitch_input.value
    profile_angle = angle_input.value
    thread_depth = depth_input.value
    if radius <= 0 or length <= 0 or pitch <= 0 or thread_depth <= 0:
        return 'Radius, Gewindelänge und Steigung müssen größer als 0 sein.'

    if profile_angle <= 0 or profile_angle >= math.pi:
        return 'Der Öffnungswinkel muss größer als 0 und kleiner als 180 Grad sein.'

    axis_min, axis_max = _get_cylinder_axis_range(face, cylinder.origin, axis)
    if axis_min is None or axis_max is None:
        return 'Zylinderlänge konnte nicht ermittelt werden.'

    if start_side_input.selectedItem is None:
        return 'Startseite wurde nicht ausgewählt.'

    side_name = start_side_input.selectedItem.name
    start_at_top = side_name == 'Deckfläche'
    available_length = axis_max - axis_min
    helix_length = min(length, available_length) if available_length > 0 else length
    direction = -1 if start_at_top else 1
    start_distance = axis_max if start_at_top else axis_min
    guide_face = _get_cylinder_end_face(face, cylinder.origin, axis, start_distance)
    if guide_face is None:
        return 'Führungsfläche konnte nicht ermittelt werden.'

    radial_vector = _get_radial_vector(face, cylinder.origin, axis)
    if radial_vector is None:
        return 'Startpunkt der Helix konnte nicht ermittelt werden.'

    helix_radial_vector = radial_vector.copy()
    if not _is_outer_cylinder_face(face, radial_vector):
        helix_radial_vector.scaleBy(-1)

    tangent_vector = axis.crossProduct(helix_radial_vector)
    if not tangent_vector.normalize():
        return 'Tangentialrichtung der Helix konnte nicht ermittelt werden.'

    helix_start_tangent = axis.copy()
    helix_start_tangent.scaleBy(direction)
    helix_tangent_offset = tangent_vector.copy()
    helix_tangent_offset.scaleBy(direction * 2 * math.pi * radius / pitch)
    helix_start_tangent.add(helix_tangent_offset)
    if not helix_start_tangent.normalize():
        return 'Start-Tangente der Helix konnte nicht ermittelt werden.'

    turns = helix_length / pitch
    point_count = max(24, int(math.ceil(turns * 48)) + 1)
    points = adsk.core.ObjectCollection.create()
    start_point = None

    for index in range(point_count):
        ratio = index / (point_count - 1)
        angle = direction * ratio * turns * 2 * math.pi
        axis_distance = start_distance + direction * ratio * helix_length

        point = cylinder.origin.copy()
        axis_offset = axis.copy()
        axis_offset.scaleBy(axis_distance)
        point.translateBy(axis_offset)

        radial_offset = helix_radial_vector.copy()
        radial_offset.scaleBy(math.cos(angle) * radius)
        point.translateBy(radial_offset)

        tangent_offset = tangent_vector.copy()
        tangent_offset.scaleBy(math.sin(angle) * radius)
        point.translateBy(tangent_offset)

        if index == 0:
            start_point = point.copy()

        points.add(point)

    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        return 'Aktives Fusion-Design konnte nicht gelesen werden.'

    timeline_start_index = design.timeline.count
    component = design.activeComponent if design.activeComponent else design.rootComponent
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = f'PrintThread Wizard Helix {VERSION}'
    sketch.is3D = True
    helix_curve = sketch.sketchCurves.sketchFittedSplines.add(points)
    profile_result = _create_thread_profile(
        component,
        face,
        helix_curve,
        guide_face,
        start_point,
        helix_start_tangent,
        radial_vector,
        profile_angle,
        thread_depth
    )

    units_manager = app.activeProduct.unitsManager
    default_units = units_manager.defaultLengthUnits
    length_text = units_manager.formatInternalValue(helix_length, default_units, True)
    pitch_text = units_manager.formatInternalValue(pitch, default_units, True)
    group_name = _build_thread_group_name(abs(radius * 2), pitch)
    group_result = _create_timeline_group(design, timeline_start_index, group_name)
    return f'Helix erstellt: Länge {length_text}, Steigung {pitch_text}, Startseite {side_name}.<br>{profile_result}<br>{group_result}'


def _create_thread_profile(
    component: adsk.fusion.Component,
    face: adsk.fusion.BRepFace,
    helix_curve: adsk.fusion.SketchCurve,
    guide_face: adsk.fusion.BRepFace,
    start_point: adsk.core.Point3D,
    helix_tangent: adsk.core.Vector3D,
    radial_vector: adsk.core.Vector3D,
    profile_angle: float,
    thread_depth: float
):
    if start_point is None:
        return 'Profil konnte nicht erstellt werden: Helix-Startpunkt fehlt.'

    depth_direction = radial_vector.copy()
    if not _is_outer_cylinder_face(face, radial_vector):
        depth_direction.scaleBy(-1)

    if not depth_direction.normalize():
        return 'Profil konnte nicht erstellt werden: Gewindetiefenrichtung fehlt.'

    base_direction = helix_tangent.crossProduct(depth_direction)
    if not base_direction.normalize():
        return 'Profil konnte nicht erstellt werden: Profilbasisrichtung fehlt.'

    overlap = _profile_overlap_internal_value()
    half_base_width = thread_depth * math.tan(profile_angle / 2)
    base_center = _offset_point(start_point, depth_direction, -overlap)
    base_left = _offset_point(base_center, base_direction, half_base_width)
    base_right = _offset_point(base_center, base_direction, -half_base_width)
    apex = _offset_point(start_point, depth_direction, thread_depth)

    try:
        plane_input = component.constructionPlanes.createInput()
        plane_input.setByDistanceOnPath(helix_curve, adsk.core.ValueInput.createByReal(0))
        construction_plane = component.constructionPlanes.add(plane_input)
        construction_plane.name = f'PrintThread Wizard Profile Plane {VERSION}'

        profile_sketch = component.sketches.add(construction_plane)
        profile_sketch.name = f'PrintThread Wizard Profile {VERSION}'

        sketch_points = [
            profile_sketch.modelToSketchSpace(base_left),
            profile_sketch.modelToSketchSpace(apex),
            profile_sketch.modelToSketchSpace(base_right)
        ]

        lines = profile_sketch.sketchCurves.sketchLines
        lines.addByTwoPoints(sketch_points[0], sketch_points[1])
        lines.addByTwoPoints(sketch_points[1], sketch_points[2])
        lines.addByTwoPoints(sketch_points[2], sketch_points[0])

        sweep_result = _sweep_profile_along_helix(component, profile_sketch, helix_curve, guide_face)
    except Exception as error:
        return f'Profil konnte nicht erstellt werden: {error}'

    units_manager = app.activeProduct.unitsManager
    default_units = units_manager.defaultLengthUnits
    depth_text = units_manager.formatInternalValue(thread_depth, default_units, True)
    overlap_text = units_manager.formatInternalValue(overlap, default_units, True)
    angle_text = units_manager.formatInternalValue(profile_angle, 'deg', True)
    return f'Dreiecksprofil erstellt: Gewindetiefe {depth_text}, Überstand {overlap_text}, Öffnungswinkel {angle_text}.<br>{sweep_result}'


def _sweep_profile_along_helix(
    component: adsk.fusion.Component,
    profile_sketch: adsk.fusion.Sketch,
    helix_curve: adsk.fusion.SketchCurve,
    guide_face: adsk.fusion.BRepFace
):
    if profile_sketch.profiles.count < 1:
        return 'Sweep konnte nicht erstellt werden: Das Dreieck bildet kein geschlossenes Profil.'

    profile = profile_sketch.profiles.item(0)
    path = component.features.createPath(helix_curve)
    sweep_features = component.features.sweepFeatures
    sweep_input = sweep_features.createInput(
        profile,
        path,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    sweep_input.isChainSelection = False
    sweep_input.guideSurfaces = [guide_face]
    sweep_features.add(sweep_input)
    return 'Sweep mit Führungsfläche erstellt.'


def _profile_overlap_internal_value():
    return app.activeProduct.unitsManager.convert(PROFILE_OVERLAP_MM, 'mm', 'cm')


def _build_thread_group_name(diameter: float, pitch: float):
    units_manager = app.activeProduct.unitsManager
    default_units = units_manager.defaultLengthUnits
    diameter_value = units_manager.convert(abs(diameter), 'cm', default_units)
    pitch_value = units_manager.convert(abs(pitch), 'cm', default_units)
    return f'3DG{_format_group_value(diameter_value)}x{_format_group_value(pitch_value)}'


def _format_group_value(value: float):
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 0.0005:
        return str(int(round(rounded)))

    return f'{rounded:.3f}'.rstrip('0').rstrip('.')


def _create_timeline_group(design: adsk.fusion.Design, start_index: int, group_name: str):
    try:
        end_index = design.timeline.count - 1
        if end_index < start_index:
            return 'Timeline-Gruppe wurde nicht erstellt: keine neuen Arbeitsschritte.'

        group = design.timeline.timelineGroups.add(start_index, end_index)
        if group is None:
            return 'Timeline-Gruppe konnte nicht erstellt werden.'

        group.name = group_name
        return f'Timeline-Gruppe erstellt: {group_name}.'
    except Exception as error:
        return f'Timeline-Gruppe konnte nicht erstellt werden: {error}'


def _offset_point(point: adsk.core.Point3D, direction: adsk.core.Vector3D, distance: float):
    result = point.copy()
    offset = direction.copy()
    offset.scaleBy(distance)
    result.translateBy(offset)
    return result


def _is_outer_cylinder_face(face: adsk.fusion.BRepFace, radial_vector: adsk.core.Vector3D):
    point = getattr(face, 'pointOnFace', None)
    if point is None:
        return True

    normal_result = face.evaluator.getNormalAtPoint(point)
    if not normal_result or not normal_result[0]:
        return True

    normal = normal_result[1]
    if not normal.normalize():
        return True

    radial = radial_vector.copy()
    if not radial.normalize():
        return True

    return normal.dotProduct(radial) >= 0


def _get_cylinder_axis_range(face: adsk.fusion.BRepFace, origin: adsk.core.Point3D, axis: adsk.core.Vector3D):
    distances = []

    try:
        vertices = face.vertices
        for index in range(vertices.count):
            distances.append(_axis_distance(origin, axis, vertices.item(index).geometry))
    except:
        pass

    try:
        edges = face.edges
        for index in range(edges.count):
            point = getattr(edges.item(index), 'pointOnEdge', None)
            if point:
                distances.append(_axis_distance(origin, axis, point))
    except:
        pass

    if len(distances) < 2:
        box = face.boundingBox
        min_point = box.minPoint
        max_point = box.maxPoint
        for x in (min_point.x, max_point.x):
            for y in (min_point.y, max_point.y):
                for z in (min_point.z, max_point.z):
                    distances.append(_axis_distance(origin, axis, adsk.core.Point3D.create(x, y, z)))

    if len(distances) < 2:
        return None, None

    return min(distances), max(distances)


def _get_cylinder_end_face(
    cylinder_face: adsk.fusion.BRepFace,
    origin: adsk.core.Point3D,
    axis: adsk.core.Vector3D,
    target_distance: float
):
    tolerance = 1e-4
    best_face = None
    best_score = None

    try:
        edges = cylinder_face.edges
        for edge_index in range(edges.count):
            edge = edges.item(edge_index)
            point = getattr(edge, 'pointOnEdge', None)
            if point is None:
                continue

            edge_distance = _axis_distance(origin, axis, point)
            distance_score = abs(edge_distance - target_distance)
            if distance_score > tolerance:
                continue

            faces = edge.faces
            for face_index in range(faces.count):
                candidate = faces.item(face_index)
                if candidate == cylinder_face:
                    continue

                normal_score = _axis_normal_score(candidate, axis)
                if normal_score is None:
                    continue

                score = distance_score - normal_score
                if best_score is None or score < best_score:
                    best_score = score
                    best_face = candidate
    except:
        return None

    return best_face


def _axis_normal_score(face: adsk.fusion.BRepFace, axis: adsk.core.Vector3D):
    point = getattr(face, 'pointOnFace', None)
    if point is None:
        return None

    normal_result = face.evaluator.getNormalAtPoint(point)
    if not normal_result or not normal_result[0]:
        return None

    normal = normal_result[1]
    if not normal.normalize():
        return None

    axis_vector = axis.copy()
    if not axis_vector.normalize():
        return None

    return abs(normal.dotProduct(axis_vector))


def _get_radial_vector(face: adsk.fusion.BRepFace, origin: adsk.core.Point3D, axis: adsk.core.Vector3D):
    point = getattr(face, 'pointOnFace', None)
    if point is None:
        return None

    distance = _axis_distance(origin, axis, point)
    axis_point = origin.copy()
    axis_offset = axis.copy()
    axis_offset.scaleBy(distance)
    axis_point.translateBy(axis_offset)

    radial_vector = axis_point.vectorTo(point)
    if not radial_vector.normalize():
        return None

    return radial_vector


def _axis_distance(origin: adsk.core.Point3D, axis: adsk.core.Vector3D, point: adsk.core.Point3D):
    return origin.vectorTo(point).dotProduct(axis)


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
