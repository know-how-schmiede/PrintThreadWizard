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

    default_units = app.activeProduct.unitsManager.defaultLengthUnits
    flank_angle_value = adsk.core.ValueInput.createByString('80 deg')
    thread_depth_value = adsk.core.ValueInput.createByString(f'5 {default_units}')
    pitch_value = adsk.core.ValueInput.createByString(f'10 {default_units}')
    fillet_radius_value = adsk.core.ValueInput.createByString('0.4 mm')
    inputs.addValueInput('flank_angle', 'Flankenwinkel', 'deg', flank_angle_value)
    inputs.addValueInput('thread_depth', 'Gewindetiefe', default_units, thread_depth_value)
    inputs.addValueInput('pitch', 'Steigung', default_units, pitch_value)
    inputs.addValueInput('fillet_radius', 'Verrundungsradius', default_units, fillet_radius_value)

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
    try:
        inputs = args.command.commandInputs
        _update_result_text(inputs)
        face = _get_selected_cylinder_face(inputs)
        if face is None:
            _debug_log('Command execute stopped: no valid cylinder face selected.', adsk.core.LogLevels.ErrorLogLevel)
            return
        selected_edges = _get_selected_edges(inputs)

        _create_cylinder_axis(face)
        helix_result = _create_thread_helix(inputs, face)
        if helix_result:
            _debug_log(helix_result, adsk.core.LogLevels.ErrorLogLevel)
            ui.messageBox(helix_result)
            return

        fillet_result = _create_edge_fillets(inputs, selected_edges)
        if fillet_result:
            _debug_log(fillet_result, adsk.core.LogLevels.ErrorLogLevel)
            ui.messageBox(fillet_result)
    except Exception as error:
        _debug_log(f'Command execute failed: {error}', adsk.core.LogLevels.ErrorLogLevel)
        ui.messageBox(f'PrintThread Wizard Fehler: {error}')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {args.input.id}')

    if args.input.id in ('target_face', 'chamfer_edges'):
        _update_result_text(args.inputs)


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    futil.log(f'{CMD_NAME} Validate Input Event')
    _update_result_text(args.inputs)
    flank_angle_input: adsk.core.ValueCommandInput = args.inputs.itemById('flank_angle')
    thread_depth_input: adsk.core.ValueCommandInput = args.inputs.itemById('thread_depth')
    pitch_input: adsk.core.ValueCommandInput = args.inputs.itemById('pitch')
    fillet_radius_input: adsk.core.ValueCommandInput = args.inputs.itemById('fillet_radius')
    args.areInputsValid = (
        _get_selected_cylinder_face(args.inputs) is not None
        and flank_angle_input is not None
        and thread_depth_input is not None
        and pitch_input is not None
        and fillet_radius_input is not None
        and 0 < flank_angle_input.value < math.pi
        and thread_depth_input.value > 0
        and pitch_input.value > 0
        and fillet_radius_input.value > 0
    )


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


def _create_cylinder_axis(face: adsk.fusion.BRepFace):
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
    _debug_log(
        f'Axis sketch created: start={_format_point(axis_points[0])}, '
        f'end={_format_point(axis_points[1])}, isValid={line.isValid}'
    )


def _create_thread_helix(inputs: adsk.core.CommandInputs, face: adsk.fusion.BRepFace):
    if face is None:
        return 'Helix konnte nicht erstellt werden: Keine Zylinderfläche ausgewählt.'

    pitch_input: adsk.core.ValueCommandInput = inputs.itemById('pitch')
    thread_depth_input: adsk.core.ValueCommandInput = inputs.itemById('thread_depth')
    flank_angle_input: adsk.core.ValueCommandInput = inputs.itemById('flank_angle')
    if pitch_input is None or thread_depth_input is None or flank_angle_input is None:
        return 'Helix konnte nicht erstellt werden: Steigung, Gewindetiefe oder Flankenwinkel fehlt.'

    pitch = pitch_input.value
    thread_depth = thread_depth_input.value
    flank_angle = flank_angle_input.value
    _debug_log(f'Helix input: pitch={pitch:.4f}, threadDepth={thread_depth:.4f}')
    if pitch <= 0 or thread_depth <= 0:
        return 'Helix konnte nicht erstellt werden: Steigung und Gewindetiefe müssen größer als 0 sein.'
    if flank_angle <= 0 or flank_angle >= math.pi:
        return 'Helix konnte nicht erstellt werden: Flankenwinkel muss größer als 0 und kleiner als 180 Grad sein.'

    axis_points = _get_cylinder_axis_points(face)
    if axis_points is None:
        return 'Helix konnte nicht erstellt werden: Zylinderachse konnte nicht ermittelt werden.'

    start_axis_point, end_axis_point = axis_points
    axis_vector = start_axis_point.vectorTo(end_axis_point)
    cylinder_length = start_axis_point.distanceTo(end_axis_point)
    _debug_log(
        f'Helix axis: start={_format_point(start_axis_point)}, end={_format_point(end_axis_point)}, '
        f'length={cylinder_length:.4f}'
    )
    if cylinder_length <= 0 or not axis_vector.normalize():
        return 'Helix konnte nicht erstellt werden: Zylinderlänge konnte nicht ermittelt werden.'

    cylinder = face.geometry
    radius = getattr(cylinder, 'radius', None)
    _debug_log(f'Helix cylinder: radius={radius}')
    if radius is None or radius <= 0:
        return 'Helix konnte nicht erstellt werden: Zylinderradius konnte nicht ermittelt werden.'

    radial_vector = _get_radial_vector(face, start_axis_point, axis_vector)
    _debug_log(f'Helix radial vector: {_format_vector(radial_vector)}')
    if radial_vector is None:
        return 'Helix konnte nicht erstellt werden: Radiusrichtung konnte nicht ermittelt werden.'

    tangent_vector = axis_vector.crossProduct(radial_vector)
    if not tangent_vector.normalize():
        return 'Helix konnte nicht erstellt werden: Tangentialrichtung konnte nicht ermittelt werden.'
    _debug_log(f'Helix tangent vector: {_format_vector(tangent_vector)}')
    helix_start_tangent = axis_vector.copy()
    helix_tangent_offset = tangent_vector.copy()
    helix_tangent_offset.scaleBy(2 * math.pi * radius / pitch)
    helix_start_tangent.add(helix_tangent_offset)
    if not helix_start_tangent.normalize():
        return 'Helix konnte nicht erstellt werden: Start-Tangente konnte nicht ermittelt werden.'

    overrun = 2 * thread_depth
    helix_length = cylinder_length + 2 * overrun
    turns = helix_length / pitch
    point_count = max(24, int(math.ceil(turns * 48)) + 1)
    points = adsk.core.ObjectCollection.create()
    start_point = None
    end_point = None
    _debug_log(
        f'Helix geometry: overrun={overrun:.4f}, helixLength={helix_length:.4f}, '
        f'turns={turns:.4f}, pointCount={point_count}'
    )

    for index in range(point_count):
        ratio = index / (point_count - 1)
        angle = ratio * turns * 2 * math.pi
        axis_distance = -overrun + ratio * helix_length

        point = start_axis_point.copy()
        axis_offset = axis_vector.copy()
        axis_offset.scaleBy(axis_distance)
        point.translateBy(axis_offset)

        radial_offset = radial_vector.copy()
        radial_offset.scaleBy(math.cos(angle) * radius)
        point.translateBy(radial_offset)

        tangent_offset = tangent_vector.copy()
        tangent_offset.scaleBy(math.sin(angle) * radius)
        point.translateBy(tangent_offset)
        if index == 0:
            start_point = point.copy()
        if index == point_count - 1:
            end_point = point.copy()
        points.add(point)

    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        return 'Helix konnte nicht erstellt werden: Aktives Fusion-Design konnte nicht gelesen werden.'

    component = design.activeComponent if design.activeComponent else design.rootComponent
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = f'PrintThread Wizard Helix {VERSION}'
    sketch.is3D = True
    helix_curve = sketch.sketchCurves.sketchFittedSplines.add(points)
    _debug_log(
        f'Helix sketch created: sketch={sketch.name}, curveType={helix_curve.objectType}, '
        f'isValid={helix_curve.isValid}, startPoint={_format_point(start_point)}, '
        f'endPoint={_format_point(end_point)}'
    )
    profile_result = _create_triangle_profile(
        component,
        face,
        helix_curve,
        start_point,
        helix_start_tangent,
        radial_vector,
        flank_angle,
        thread_depth
    )
    if isinstance(profile_result, str):
        return profile_result

    profile_sketch = profile_result
    sweep_result = _sweep_triangle_profile(component, profile_sketch, helix_curve, face, start_axis_point)
    if sweep_result:
        return sweep_result

    _refresh_viewport()
    return None


def _create_triangle_profile(
    component: adsk.fusion.Component,
    face: adsk.fusion.BRepFace,
    helix_curve: adsk.fusion.SketchCurve,
    start_point: adsk.core.Point3D,
    helix_tangent: adsk.core.Vector3D,
    radial_vector: adsk.core.Vector3D,
    flank_angle: float,
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

    half_base_width = thread_depth * math.tan(flank_angle / 2)
    base_left = _offset_point(start_point, base_direction, half_base_width)
    base_right = _offset_point(start_point, base_direction, -half_base_width)
    apex = _offset_point(start_point, depth_direction, thread_depth)

    try:
        plane_input = component.constructionPlanes.createInput()
        plane_input.setByDistanceOnPath(helix_curve, adsk.core.ValueInput.createByReal(0))
        profile_plane = component.constructionPlanes.add(plane_input)
        profile_plane.name = f'PrintThread Wizard Profilebene {VERSION}'

        profile_sketch = component.sketches.add(profile_plane)
        profile_sketch.name = f'PrintThread Wizard Profil {VERSION}'
        sketch_points = [
            profile_sketch.modelToSketchSpace(base_left),
            profile_sketch.modelToSketchSpace(apex),
            profile_sketch.modelToSketchSpace(base_right)
        ]

        lines = profile_sketch.sketchCurves.sketchLines
        lines.addByTwoPoints(sketch_points[0], sketch_points[1])
        lines.addByTwoPoints(sketch_points[1], sketch_points[2])
        lines.addByTwoPoints(sketch_points[2], sketch_points[0])
        _debug_log(
            f'Triangle profile created: planeValid={profile_plane.isValid}, '
            f'profiles={profile_sketch.profiles.count}, baseLeft={_format_point(base_left)}, '
            f'apex={_format_point(apex)}, baseRight={_format_point(base_right)}'
        )
        return profile_sketch
    except Exception as error:
        return f'Profil konnte nicht erstellt werden: {error}'


def _sweep_triangle_profile(
    component: adsk.fusion.Component,
    profile_sketch: adsk.fusion.Sketch,
    helix_curve: adsk.fusion.SketchCurve,
    cylinder_face: adsk.fusion.BRepFace,
    start_axis_point: adsk.core.Point3D
):
    if profile_sketch.profiles.count < 1:
        return 'Sweep konnte nicht erstellt werden: Das Dreieck bildet kein geschlossenes Profil.'

    guide_face = _get_cylinder_end_face(cylinder_face, start_axis_point)
    if guide_face is None:
        return 'Sweep konnte nicht erstellt werden: Zylindergrundfläche konnte nicht ermittelt werden.'

    try:
        path_curves = adsk.core.ObjectCollection.create()
        path_curves.add(helix_curve)
        path = component.features.createPath(path_curves)

        sweep_features = component.features.sweepFeatures
        sweep_input = sweep_features.createInput(
            profile_sketch.profiles.item(0),
            path,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        sweep_input.isChainSelection = False
        sweep_input.guideSurfaces = [guide_face]
        sweep_feature = sweep_features.add(sweep_input)
        if sweep_feature.bodies.count > 0:
            sweep_feature.bodies.item(0).name = f'PrintThread Wizard Gewindekoerper {VERSION}'

        _debug_log(
            f'Sweep created: guideFaceValid={guide_face.isValid}, '
            f'profileCount={profile_sketch.profiles.count}, isValid={sweep_feature.isValid}'
        )
        _refresh_viewport()
        return None
    except Exception as error:
        return f'Sweep konnte nicht erstellt werden: {error}'


def _create_edge_fillets(inputs: adsk.core.CommandInputs, edges):
    if not edges:
        _debug_log('Fillet skipped: no edges selected.')
        return None

    fillet_radius_input: adsk.core.ValueCommandInput = inputs.itemById('fillet_radius')
    if fillet_radius_input is None or fillet_radius_input.value <= 0:
        return 'Verrundung konnte nicht erstellt werden: Verrundungsradius fehlt oder ist ungültig.'

    valid_edges = [edge for edge in edges if edge and edge.isValid]
    if not valid_edges:
        return 'Verrundung konnte nicht erstellt werden: Ausgewählte Kanten sind nicht mehr gültig.'

    component = _component_from_edge(valid_edges[0])
    if component is None:
        return 'Verrundung konnte nicht erstellt werden: Komponente der Kante konnte nicht ermittelt werden.'

    edge_collection = adsk.core.ObjectCollection.create()
    for edge in valid_edges:
        edge_collection.add(edge)

    try:
        fillet_features = component.features.filletFeatures
        fillet_input = fillet_features.createInput()
        fillet_input.addConstantRadiusEdgeSet(
            edge_collection,
            adsk.core.ValueInput.createByReal(fillet_radius_input.value),
            True
        )
        fillet_feature = fillet_features.add(fillet_input)
        _debug_log(
            f'Fillet created: edges={len(valid_edges)}, radius={fillet_radius_input.value:.4f}, '
            f'isValid={fillet_feature.isValid}'
        )
        _refresh_viewport()
        return None
    except Exception as error:
        return f'Verrundung konnte nicht erstellt werden: {error}'


def _component_from_edge(edge: adsk.fusion.BRepEdge):
    try:
        body = edge.body
        if body:
            return body.parentComponent
    except:
        pass

    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        return None

    return design.activeComponent if design.activeComponent else design.rootComponent


def _get_cylinder_end_face(cylinder_face: adsk.fusion.BRepFace, target_center: adsk.core.Point3D):
    best_edge = None
    best_distance = None

    try:
        edges = cylinder_face.edges
        for index in range(edges.count):
            edge = edges.item(index)
            geometry = getattr(edge, 'geometry', None)
            center = getattr(geometry, 'center', None)
            if center is None:
                continue

            distance = center.distanceTo(target_center)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_edge = edge
    except:
        return None

    if best_edge is None:
        return None

    try:
        faces = best_edge.faces
        for index in range(faces.count):
            face = faces.item(index)
            if face == cylinder_face:
                continue

            if getattr(face.geometry, 'normal', None) is not None or face.geometry.objectType.endswith('Plane'):
                return face

        for index in range(faces.count):
            face = faces.item(index)
            if face != cylinder_face:
                return face
    except:
        return None

    return None


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


def _get_selected_edges(inputs: adsk.core.CommandInputs):
    edge_input: adsk.core.SelectionCommandInput = inputs.itemById('chamfer_edges')
    if edge_input is None:
        return []

    edges = []
    for index in range(edge_input.selectionCount):
        entity = edge_input.selection(index).entity
        edge = adsk.fusion.BRepEdge.cast(entity)
        if edge:
            edges.append(edge)

    return edges


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


def _get_radial_vector(face: adsk.fusion.BRepFace, axis_origin: adsk.core.Point3D, axis: adsk.core.Vector3D):
    point = getattr(face, 'pointOnFace', None)
    if point is None:
        return None

    distance = axis_origin.vectorTo(point).dotProduct(axis)
    axis_point = axis_origin.copy()
    axis_offset = axis.copy()
    axis_offset.scaleBy(distance)
    axis_point.translateBy(axis_offset)

    radial_vector = axis_point.vectorTo(point)
    if not radial_vector.normalize():
        return None

    return radial_vector


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


def _offset_point(point: adsk.core.Point3D, direction: adsk.core.Vector3D, distance: float):
    result = point.copy()
    offset = direction.copy()
    offset.scaleBy(distance)
    result.translateBy(offset)
    return result


def _debug_log(message: str, level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel):
    futil.log(f'[PrintThread Wizard] {message}', level, force_console=True)


def _format_point(point: adsk.core.Point3D):
    if point is None:
        return 'None'

    return f'({point.x:.4f}, {point.y:.4f}, {point.z:.4f})'


def _format_vector(vector: adsk.core.Vector3D):
    if vector is None:
        return 'None'

    return f'({vector.x:.4f}, {vector.y:.4f}, {vector.z:.4f})'


def _refresh_viewport():
    try:
        adsk.doEvents()
    except:
        pass

    try:
        viewport = app.activeViewport
        if viewport:
            viewport.refresh()
    except:
        pass


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
