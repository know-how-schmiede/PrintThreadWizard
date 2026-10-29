"""Rebuild in execute: rollback-only trial or ownership-guarded final replacement."""
from ..core.thread_records import validate_record
from ..core.thread_parameters import ThreadParameters
from ..localization import translate as tr
from .thread_records import resolve_reference
from ..core.thread_edits import apply_trial_changes
from ..core.thread_records import record_context


def run_rebuild_trial(design, record, validate_parameters, build_thread, changes=None,
                      replace_original=False):
    """Default trials must be rolled back by the caller even after success.

    replace_original enables restricted permanent editing only after proving
    complete ownership of the final timeline suffix. Every failure must reach
    executeFailed in the caller so deletion and rebuilding roll back together.
    """
    validate_record(record)
    if replace_original and design.timeline.markerPosition != design.timeline.count:
        raise ValueError(tr('edit_last_only'))
    first = [entity for entity in design.findEntityByToken(record['references']['first_feature']) if entity.isValid]
    if len(first) != 1 or getattr(first[0], 'timelineObject', None) is None:
        raise ValueError(tr('record_timeline_missing'))
    feature = first[0].timelineObject
    groups = []
    parent = feature.parentGroup
    while parent is not None:
        groups.append((parent, parent.isCollapsed))
        parent = parent.parentGroup
    deleted = False
    try:
        for group, collapsed in reversed(groups):
            if collapsed:
                group.isCollapsed = False
        if replace_original:
            verify_owned_suffix(design, record, feature)
        if not feature.rollTo(True):
            raise ValueError(tr('probe_roll_failed'))
        refs = {}
        for key in ('face', 'body', 'component', 'occurrence', 'start_edge', 'chamfer_edges'):
            value = record['references'].get(key)
            tokens = value if isinstance(value, list) else ([value] if value else [])
            refs[key] = []
            for token in tokens:
                entities = resolve_reference(design, record, key, token)
                if len(entities) != 1:
                    raise ValueError(tr('record_ref_' + key) + ': ' + tr(
                        'record_ambiguous' if entities else 'record_missing'))
                entity = entities[0]
                refs[key].append(getattr(entity, 'nativeObject', None) or entity)
        parameters = ThreadParameters(face=refs['face'][0],
                      start_edge=refs['start_edge'][0] if refs['start_edge'] else None,
                      chamfer_edges=tuple(refs['chamfer_edges']), **record['parameters'])
        if changes is not None:
            from .face_analysis import analyze_cylinder
            parameters = apply_trial_changes(parameters, record['calculation_mode'], changes,
                                             analyze_cylinder(parameters.face).is_external)
        errors = validate_parameters(parameters)
        if errors:
            raise ValueError('\n'.join(errors))
        if replace_original:
            if not design.timeline.deleteAllAfterMarker():
                raise RuntimeError(tr('edit_delete_failed'))
            deleted = True
            if design.timeline.markerPosition != design.timeline.count:
                raise RuntimeError(tr('edit_delete_failed'))
            # Deleting future features may invalidate wrappers. Resolve the
            # preserved source face and edges again before passing them on.
            def one(key, token):
                entities = resolve_reference(design, record, key, token)
                if len(entities) != 1:
                    raise ValueError(tr('record_ref_' + key) + ': ' + tr('record_missing'))
                return getattr(entities[0], 'nativeObject', None) or entities[0]
            from dataclasses import replace
            parameters = replace(parameters,
                face=one('face', record['references']['face']),
                start_edge=one('start_edge', record['references']['start_edge']) if record['references'].get('start_edge') else None,
                chamfer_edges=tuple(one('chamfer_edges', token) for token in record['references']['chamfer_edges']))
            errors = validate_parameters(parameters)
            if errors:
                raise ValueError('\n'.join(errors))
        keywords = dict(creation_occurrence=refs['occurrence'][0] if refs['occurrence'] else None,
                        calculation_mode=record['calculation_mode'], group_timeline=replace_original)
        if replace_original:
            keywords['record_context'] = record_context(record)
        build_thread(parameters, **keywords)
    finally:
        # Do not move to the end: later original features must not be computed
        # on the trial body. Fusion's ensuing transaction abort restores history.
        if groups and not deleted:
            if not feature.rollTo(True):
                raise RuntimeError(tr('probe_restore_failed'))
            for group, collapsed in groups:
                group.isCollapsed = collapsed


def verify_owned_suffix(design, record, first):
    positions = owned_feature_positions(design, record)
    expected = list(range(first.index, design.timeline.count))
    if first.index < 0 or sorted(positions) != expected:
        raise ValueError(tr('edit_last_only'))


def owned_feature_positions(design, record):
    tokens = record['references'].get('owned_features')
    if not tokens:
        raise ValueError(tr('edit_ownership_missing'))
    positions = []
    for token in tokens:
        entities = [entity for entity in design.findEntityByToken(token) if entity.isValid]
        if len(entities) != 1 or getattr(entities[0], 'timelineObject', None) is None:
            raise ValueError(tr('edit_ownership_missing'))
        owner = entities[0].attributes.itemByName('PrintThreadWizard', 'thread_owner')
        if owner is None or owner.value != record['id']:
            raise ValueError(tr('edit_ownership_missing'))
        positions.append(entities[0].timelineObject.index)
    last = design.findEntityByToken(record['references']['result_feature'])
    if len(last) != 1 or last[0].timelineObject.index != positions[-1]:
        raise ValueError(tr('edit_ownership_missing'))
    if any(index < 0 for index in positions):
        raise ValueError(tr('edit_ownership_missing'))
    return positions
