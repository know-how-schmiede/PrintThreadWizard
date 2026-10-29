"""Atomic replacement of a positively linked final thread pair in execute."""
from ..core.thread_records import validate_record, record_context
from ..core.thread_parameters import ThreadParameters
from ..core.thread_edits import apply_trial_changes
from ..localization import translate as tr
from .thread_records import list_records, resolve_reference
from .thread_rebuild_trial import owned_feature_positions


def linked_pair(design, selected):
    validate_record(selected)
    if not selected.get('pair_id') or not selected.get('partner_id'):
        raise ValueError(tr('pair_edit_missing'))
    matches = [entry['record'] for entry in list_records(design)
               if entry['record'] and entry['record']['id'] == selected['partner_id']]
    if (len(matches) != 1 or matches[0].get('pair_id') != selected['pair_id']
            or matches[0].get('partner_id') != selected['id']):
        raise ValueError(tr('pair_edit_missing'))
    return [selected, matches[0]]


def load_pair_parameters(design, record, changes, classify_face):
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
            # Preserve occurrence assembly context; geometric inputs remain native.
            refs[key].append(entity if key == 'occurrence' else (getattr(entity, 'nativeObject', None) or entity))
    params = ThreadParameters(face=refs['face'][0], chamfer_edges=tuple(refs['chamfer_edges']),
                             start_edge=refs['start_edge'][0] if refs['start_edge'] else None,
                             **record['parameters'])
    if changes is not None:
        if set(changes) - {'pitch', 'tolerance', 'handedness'}:
            raise ValueError(tr('pair_edit_shared'))
        params = apply_trial_changes(params, record['calculation_mode'], changes,
                                     classify_face(params.face).is_external)
    return params, refs['occurrence'][0] if refs['occurrence'] else None


def replace_linked_pair(design, selected, changes, validate_parameters, build_thread,
                        classify_face, validate_pair):
    records = linked_pair(design, selected)
    timeline = design.timeline
    if timeline.markerPosition != timeline.count:
        raise ValueError(tr('pair_edit_last'))
    saved_marker, saved_count = timeline.markerPosition, timeline.count
    groups = []
    firsts = []
    deleted = False
    try:
        for record in records:
            entities = [entity for entity in design.findEntityByToken(record['references']['first_feature']) if entity.isValid]
            if len(entities) != 1 or getattr(entities[0], 'timelineObject', None) is None:
                raise ValueError(tr('record_timeline_missing'))
            firsts.append(entities[0].timelineObject)
            parent = firsts[-1].parentGroup
            while parent is not None:
                if not any(parent == group for group, collapsed in groups):
                    groups.append((parent, parent.isCollapsed))
                parent = parent.parentGroup
        # Expand ancestors before their children; nested groups can otherwise
        # retain hidden (-1) feature indices.
        pending = list(groups)
        while pending:
            progress = False
            for item in list(pending):
                group, collapsed = item
                if not any(group.parentGroup == other[0] for other in pending):
                    if collapsed:
                        group.isCollapsed = False
                    pending.remove(item)
                    progress = True
            if not progress:
                raise ValueError(tr('pair_edit_last'))
        positioned = [(owned_feature_positions(design, record), record, first)
                      for record, first in zip(records, firsts)]
        positioned.sort(key=lambda item: min(item[0]))
        all_positions = [position for positions, record, first in positioned for position in positions]
        first_index = min(all_positions)
        if sorted(all_positions) != list(range(first_index, timeline.count)):
            raise ValueError(tr('pair_edit_last'))
        if any(min(positions) != first.index for positions, record, first in positioned):
            raise ValueError(tr('edit_ownership_missing'))
        if not positioned[0][2].rollTo(True):
            raise ValueError(tr('probe_roll_failed'))
        source = [load_pair_parameters(design, record, changes, classify_face)
                  for positions, record, first in positioned]
        if any(getattr(source[0][0], key) != getattr(source[1][0], key)
               for key in ('pitch', 'handedness', 'tolerance', 'clearance_distribution')):
            raise ValueError(tr('pair_edit_shared'))
        for params, occurrence in source:
            errors = validate_parameters(params)
            if errors:
                raise ValueError('\n'.join(errors))
        validate_pair(classify_face(source[0][0].face), classify_face(source[1][0].face))
        if not timeline.deleteAllAfterMarker():
            raise RuntimeError(tr('edit_delete_failed'))
        deleted = True
        if timeline.markerPosition != timeline.count:
            raise RuntimeError(tr('edit_delete_failed'))
        # A failure on either partner propagates to executeFailed; no partial
        # replacement can commit. Resolve wrappers again after deletion/builds.
        for positions, record, first in positioned:
            params, occurrence = load_pair_parameters(design, record, changes, classify_face)
            errors = validate_parameters(params)
            if errors:
                raise ValueError('\n'.join(errors))
            build_thread(params, creation_occurrence=occurrence,
                         calculation_mode=record['calculation_mode'],
                         record_context=record_context(record))
    finally:
        if not deleted:
            if timeline.moveToEnd() is False:
                raise RuntimeError(tr('probe_restore_failed'))
            # Inner groups must close before their enclosing groups.
            def depth(item):
                count, parent = 0, item[0].parentGroup
                while parent is not None:
                    count += 1
                    parent = parent.parentGroup
                return count
            for group, collapsed in sorted(groups, key=depth, reverse=True):
                group.isCollapsed = collapsed
            timeline.markerPosition = saved_marker
            if timeline.markerPosition != saved_marker or timeline.count != saved_count:
                raise RuntimeError(tr('probe_restore_failed'))
