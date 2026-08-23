import adsk.core
import adsk.fusion


def create_thread_end_chamfer(component, target_body, selected_edges, distance):
    """Fast die ausdrücklich ausgewählten Kanten mit gleichem Abstand an."""
    if not selected_edges:
        return None

    edges = adsk.core.ObjectCollection.create()
    for selected_edge in selected_edges:
        edge = adsk.fusion.BRepEdge.cast(selected_edge)
        if edge is None:
            raise ValueError('Eine ausgewählte Fasen-Kante ist ungültig.')

        native_edge = getattr(edge, 'nativeObject', None)
        if native_edge:
            edge = native_edge
        if edge.body != target_body:
            raise ValueError('Alle Fasen-Kanten müssen zum ausgewählten Zylinderkörper gehören.')
        edges.add(edge)

    chamfers = component.features.chamferFeatures
    chamfer_input = chamfers.createInput2()
    added = chamfer_input.chamferEdgeSets.addEqualDistanceChamferEdgeSet(
        edges, adsk.core.ValueInput.createByReal(distance), False
    )
    if not added:
        raise RuntimeError('Die ausgewählten Kanten konnten nicht zur Fase hinzugefügt werden.')

    chamfer = chamfers.add(chamfer_input)
    if chamfer is None:
        raise RuntimeError('Die Fase konnte nicht erzeugt werden.')
    chamfer.name = 'PrintThread Wizard – Gewindeenden'
    return chamfer
