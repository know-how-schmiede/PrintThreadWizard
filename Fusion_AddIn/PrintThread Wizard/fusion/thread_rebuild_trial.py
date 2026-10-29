"""Temporary rebuild in execute; caller MUST abort the command transaction."""
from ..core.thread_records import validate_record
from ..core.thread_parameters import ThreadParameters
from ..localization import translate as tr
from .thread_records import resolve_reference
from ..core.thread_edits import apply_trial_changes


def run_rebuild_trial(design, record, validate_parameters, build_thread, changes=None):
    """Insert a trial before the old features, never delete the original ones.

    This function does not commit or manually delete trial features. Its only
    caller marks executeFailed after success, and on every exception, so Fusion
    restores the entire pre-command state including the original geometry.
    """
    validate_record(record)
    first = [entity for entity in design.findEntityByToken(record['references']['first_feature']) if entity.isValid]
    if len(first) != 1 or getattr(first[0], 'timelineObject', None) is None:
        raise ValueError(tr('record_timeline_missing'))
    feature = first[0].timelineObject
    groups = []
    parent = feature.parentGroup
    while parent is not None:
        groups.append((parent, parent.isCollapsed))
        parent = parent.parentGroup
    try:
        for group, collapsed in reversed(groups):
            if collapsed:
                group.isCollapsed = False
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
        build_thread(parameters, creation_occurrence=refs['occurrence'][0] if refs['occurrence'] else None,
                     calculation_mode=record['calculation_mode'], group_timeline=False)
    finally:
        # Do not move to the end: later original features must not be computed
        # on the trial body. Fusion's ensuing transaction abort restores history.
        if groups:
            if not feature.rollTo(True):
                raise RuntimeError(tr('probe_restore_failed'))
            for group, collapsed in groups:
                group.isCollapsed = collapsed
