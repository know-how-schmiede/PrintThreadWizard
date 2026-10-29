"""Read-only reference inspection; reversible probing is a separate module."""
from ..core.thread_records import GROUP, ATTRIBUTE, make_record, encode_record, decode_record
from ..version import VERSION
from ..localization import translate as tr


def capture_record(parameters, calculation_mode, creation_occurrence=None, context=None):
    face = parameters.face
    occurrence = creation_occurrence or face.assemblyContext
    native = face.nativeObject or face
    def token(entity): return entity.entityToken if entity is not None else None
    references = dict(face=token(native), body=token(native.body),
                      component=token(native.body.parentComponent), occurrence=token(occurrence),
                      start_edge=token(parameters.start_edge),
                      chamfer_edges=[token(edge) for edge in parameters.chamfer_edges])
    record = make_record(parameters, references, calculation_mode, VERSION)
    if context:
        from ..core.thread_records import validate_record
        if set(context) - {'id', 'pair_id', 'partner_id'}:
            raise ValueError(tr('record_invalid'))
        record.update(context)
        validate_record(record, require_result=False)
    return record


def attach_record(record, parameter_sketch, result_feature):
    record['references'].update(first_feature=parameter_sketch.entityToken,
                                result_feature=result_feature.entityToken)
    parameter_sketch.attributes.add(GROUP, ATTRIBUTE, encode_record(record))
    result_feature.attributes.add(GROUP, 'thread_id', record['id'])


def list_records(design):
    entries = []
    for attribute in design.findAttributes(GROUP, ATTRIBUTE):
        name = getattr(attribute.parent, 'name', tr('record_selector'))
        try:
            record = decode_record(attribute.value)
            entries.append(dict(record=record, error=None, name=name))
        except ValueError as error:
            entries.append(dict(record=None, error=str(error), name=name))
    return entries


def resolve_reference(design, record, key, token):
    def lookup(value):
        try:
            return [entity for entity in design.findEntityByToken(value) if entity.isValid]
        except RuntimeError:
            return []
    entities = lookup(token)
    if key == 'component' and not entities:
        # Fusion may not resolve the root component's token. The uniquely
        # resolved target body still supplies its actual owning component.
        # Never substitute the root blindly or hide an ambiguous token result.
        bodies = lookup(record['references']['body'])
        if len(bodies) == 1:
            body = getattr(bodies[0], 'nativeObject', None) or bodies[0]
            component = getattr(body, 'parentComponent', None)
            if component is not None and component.isValid:
                return [component]
    return entities


def inspect_references(design, record):
    """Never equate token strings: ask Fusion to resolve each saved token."""
    report = []
    for key in ('component', 'body', 'face', 'occurrence', 'start_edge', 'chamfer_edges',
                'first_feature', 'result_feature'):
        value = record['references'].get(key)
        tokens = value if isinstance(value, list) else ([value] if value else [])
        for index, token in enumerate(tokens):
            try:
                entities = resolve_reference(design, record, key, token)
                state = 'record_found' if len(entities) == 1 else 'record_ambiguous' if entities else 'record_missing'
            except RuntimeError:
                state = 'record_missing'
            report.append((key, index, tr(state)))
    return report


def inspect_timeline(design, record):
    """Read actual feature positions; saved token text is never an identity test."""
    try:
        positions = []
        for key in ('first_feature', 'result_feature'):
            entities = [entity for entity in design.findEntityByToken(record['references'][key]) if entity.isValid]
            if len(entities) != 1 or getattr(entities[0], 'timelineObject', None) is None:
                return None
            positions.append(entities[0].timelineObject.index)
        start, end = positions
        if start < 0 or end < start:
            return None
        return dict(start=start + 1, end=end + 1, following=max(0, design.timeline.count - end - 1))
    except RuntimeError:
        return None
