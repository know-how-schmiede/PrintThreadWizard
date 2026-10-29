"""Compact record selection, parameter editing and explicit action menu."""
import math
import adsk.core
from ...core.thread_edits import validate_trial_changes
from ...fusion.thread_records import list_records, inspect_references, inspect_timeline
from ...localization import translate as tr


class RecordInspector:
    def __init__(self):
        self.entries = []

    def add_tab(self, inputs, design):
        fields = inputs.addTabCommandInput('records_tab', tr('records_tab')).children
        fields.addTextBoxCommandInput('records_help', '', tr('records_intro'), 2, True)
        fields.addDropDownCommandInput('record_selector', tr('record_short'),
                                      adsk.core.DropDownStyles.TextListDropDownStyle)
        fields.addBoolValueInput('records_refresh', tr('records_refresh'), False, '', False).tooltip = tr('records_refresh_tip')
        action = fields.addDropDownCommandInput('record_action', tr('action'),
                                               adsk.core.DropDownStyles.TextListDropDownStyle)
        for index, key in enumerate(('records_view', 'records_probe', 'records_trial', 'records_apply', 'records_pair_apply')):
            action.listItems.add(tr(key), index == 0)
        fields.addTextBoxCommandInput('record_action_help', '', tr('records_view_tip'), 3, True)
        fields.addTextBoxCommandInput('edit_availability', '', tr('probe_select'), 3, True)
        group = fields.addGroupCommandInput('trial_changes', tr('trial_changes'))
        group.isExpanded = True
        edits = group.children
        direction = edits.addDropDownCommandInput('trial_handedness', tr('thread_direction'),
                                                 adsk.core.DropDownStyles.TextListDropDownStyle)
        direction.listItems.add(tr('right_hand'), True)
        direction.listItems.add(tr('left_hand'), False)
        direction.tooltip = tr('direction_help')
        for key, label, default in (('pitch', 'pitch', '2 mm'), ('tolerance', 'cal_gap', '0.15 mm'),
                                    ('start_offset', 'start_offset', '0 mm'), ('thread_length', 'thread_length', '10 mm')):
            edits.addValueInput('trial_' + key, tr(label), 'mm',
                               adsk.core.ValueInput.createByString(default)).tooltip = tr('record_parameters_tip')
        details = fields.addGroupCommandInput('record_details_group', tr('record_details_group'))
        details.isExpanded = False
        details.children.addTextBoxCommandInput('record_details', '', '', 12, True)
        self.refresh(design, lambda key: fields.itemById(key) or edits.itemById(key) or details.children.itemById(key))

    def selected_record(self, get):
        selected = get('record_selector').selectedItem
        index = selected.index - 1 if selected is not None else -1
        if not 0 <= index < len(self.entries) or self.entries[index]['error']:
            raise ValueError(tr('probe_select'))
        return self.entries[index]['record']

    def trial_changes(self, get):
        record = self.selected_record(get)
        paired = get('record_action').selectedItem.index == 4
        keys = ('pitch', 'tolerance') if record['parameters']['full_length'] or paired else (
               'pitch', 'tolerance', 'start_offset', 'thread_length')
        changes = {key: get('trial_' + key).value for key in keys}
        changes['handedness'] = ('right', 'left')[get('trial_handedness').selectedItem.index]
        return validate_trial_changes(changes, record['parameters']['full_length'])

    def refresh(self, design, get):
        get('record_action').listItems.item(0).isSelected = True
        self.update_action_help(get)
        get('edit_availability').text = tr('probe_select')
        self.entries = list_records(design)
        items = get('record_selector').listItems
        items.clear()
        items.add(tr('choose_setting'), True)
        for index, entry in enumerate(self.entries):
            record = entry['record']
            label = f'{index + 1}: {entry["name"][:40]}'
            if record:
                p = record['parameters']
                direction = tr('left_hand' if p['handedness'] == 'left' else 'right_hand')
                label = f'{index + 1}: {direction}, P{p["pitch"] * 10:g} mm ({record["id"][:8]})'
            items.add(label, False)
        get('record_details').text = tr('records_count', count=len(self.entries))

    def show(self, design, get):
        get('record_action').listItems.item(0).isSelected = True
        self.update_action_help(get)
        get('edit_availability').text = tr('probe_select')
        selected = get('record_selector').selectedItem
        index = selected.index - 1 if selected is not None else -1
        if not 0 <= index < len(self.entries):
            get('record_details').text = tr('records_count', count=len(self.entries))
            return
        entry = self.entries[index]
        get('record_selector').tooltip = entry['name']
        if entry['error']:
            get('record_details').text = entry['error']
            return
        record = entry['record']
        owned = bool(record['references'].get('owned_features'))
        get('edit_availability').text = tr('edit_ready' if owned else 'edit_ownership_missing')
        p = record['parameters']
        get('trial_handedness').listItems.item(1 if p['handedness'] == 'left' else 0).isSelected = True
        for key in ('pitch', 'tolerance', 'start_offset', 'thread_length'):
            field = get('trial_' + key)
            field.value = p[key]
            field.isEnabled = key in ('pitch', 'tolerance') or not p['full_length']
        lines = [tr('record_version', version=record['created_with']),
                 tr('iso_mode' if record['calculation_mode'] == 'iso_metric' else 'free_mode'),
                 tr('left_hand' if p['handedness'] == 'left' else 'right_hand')]
        for key, label, factor, suffix in (
            ('pitch', 'pitch', 10, 'mm'), ('thread_depth', 'thread_depth', 10, 'mm'),
            ('flank_angle', 'profile_angle', 180 / math.pi, '°'),
            ('fillet_radius', 'fillet_radius', 10, 'mm'), ('tolerance', 'cal_gap', 10, 'mm'),
            ('chamfer_extra', 'chamfer_extra', 10, 'mm')):
            lines.append(f'{tr(label)}: {p[key] * factor:g} {suffix}')
        lines.append(tr('distribution_' + p['clearance_distribution']))
        if p['full_length']:
            lines.append(tr('full_length'))
        else:
            lines.extend((f'{tr("start_offset")}: {p["start_offset"] * 10:g} mm',
                          f'{tr("thread_length")}: {p["thread_length"] * 10:g} mm'))
        lines.append(tr('record_refs'))
        for key, number, state in inspect_references(design, record):
            lines.append(f'{tr("record_ref_" + key)} {number + 1 if key == "chamfer_edges" else ""}: {state}')
        timeline = inspect_timeline(design, record)
        lines.append(tr('record_timeline', **timeline) if timeline else tr('record_timeline_missing'))
        lines.append(tr('record_source_note'))
        get('record_details').text = '\n'.join(lines)


    def update_action_help(self, get):
        selected = get('record_action').selectedItem
        index = selected.index if selected is not None else 0
        get('record_action_help').text = tr(('records_view_tip', 'probe_tip', 'trial_tip', 'edit_tip', 'pair_edit_tip')[index])
        selected = get('record_selector').selectedItem
        row = selected.index - 1 if selected is not None else -1
        partial = (0 <= row < len(self.entries) and self.entries[row]['record'] is not None
                   and not self.entries[row]['record']['parameters']['full_length'])
        for key in ('start_offset', 'thread_length'):
            get('trial_' + key).isEnabled = partial and index != 4
