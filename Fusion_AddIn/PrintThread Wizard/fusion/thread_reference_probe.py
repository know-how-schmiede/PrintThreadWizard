"""Explicit, reversible M6 feasibility probe, run only inside execute."""
from ..core.thread_records import validate_record
from ..core.thread_parameters import ThreadParameters
from ..localization import translate as tr
from .thread_records import resolve_reference


def probe_original_references(design, record, validate_parameters):
    validate_record(record)
    timeline = design.timeline
    saved_marker, saved_count = timeline.markerPosition, timeline.count
    first = design.findEntityByToken(record['references']['first_feature'])
    first = [entity for entity in first if entity.isValid]
    if len(first) != 1 or getattr(first[0], 'timelineObject', None) is None:
        raise ValueError(tr('record_timeline_missing'))
    feature = first[0].timelineObject
    groups = []
    parent = feature.parentGroup
    while parent is not None:
        groups.append((parent, parent.isCollapsed))
        parent = parent.parentGroup
    report = []
    resolved = {}
    errors = []
    try:
        for group, collapsed in reversed(groups):
            if collapsed:
                group.isCollapsed = False
        if not feature.rollTo(True):
            raise ValueError(tr('probe_roll_failed'))
        for key in ('component', 'body', 'face', 'occurrence', 'start_edge', 'chamfer_edges'):
            value = record['references'].get(key)
            tokens = value if isinstance(value, list) else ([value] if value else [])
            resolved[key] = []
            for number, token in enumerate(tokens):
                entities = resolve_reference(design, record, key, token)
                state = 'record_found' if len(entities) == 1 else 'record_ambiguous' if entities else 'record_missing'
                report.append((key, number, tr(state)))
                if len(entities) != 1:
                    errors.append(tr('record_ref_' + key) + ': ' + tr(state))
                else:
                    entity = entities[0]
                    resolved[key].append(getattr(entity, 'nativeObject', None) or entity)
        if not errors:
            p = ThreadParameters(face=resolved['face'][0],
                                 start_edge=resolved['start_edge'][0] if resolved['start_edge'] else None,
                                 chamfer_edges=tuple(resolved['chamfer_edges']), **record['parameters'])
            errors.extend(validate_parameters(p))
        return dict(references=report, errors=errors, ready=not errors)
    finally:
        # Restore the original group layout before restoring its marker index.
        # Moving to the end allows a group containing the probe marker to close.
        if timeline.moveToEnd() is False:
            raise RuntimeError(tr('probe_restore_failed'))
        for group, collapsed in groups:
            group.isCollapsed = collapsed
        timeline.markerPosition = saved_marker
        if timeline.markerPosition != saved_marker or timeline.count != saved_count:
            raise RuntimeError(tr('probe_restore_failed'))
