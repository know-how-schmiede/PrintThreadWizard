"""First M6 stage: inspect saved settings and references without rebuilding."""
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
        fields.addTextBoxCommandInput('records_help', '', tr('records_help'), 5, True)
        fields.addDropDownCommandInput('record_selector', tr('record_selector'),
                                      adsk.core.DropDownStyles.TextListDropDownStyle)
        fields.addBoolValueInput('records_refresh', tr('records_refresh'), False, '', False).tooltip = tr('records_refresh_tip')
        fields.addBoolValueInput('record_probe', tr('probe_action'), True, '', False).tooltip = tr('probe_tip')
        fields.addTextBoxCommandInput('probe_help', '', tr('probe_tip'), 4, True)
        fields.addBoolValueInput('record_rebuild_trial', tr('trial_action'), True, '', False).tooltip = tr('trial_tip')
        fields.addTextBoxCommandInput('trial_help', '', tr('trial_tip'), 5, True)
        edits = fields.addGroupCommandInput('trial_changes', tr('trial_changes')).children
        edits.addBoolValueInput('trial_modify', tr('trial_modify'), True, '', False).tooltip = tr('trial_modify_tip')
        for key, label, default in (('pitch', 'pitch', '2 mm'), ('tolerance', 'cal_gap', '0.15 mm'),
                                    ('start_offset', 'start_offset', '0 mm'), ('thread_length', 'thread_length', '10 mm')):
            edits.addValueInput('trial_' + key, tr(label), 'mm',
                               adsk.core.ValueInput.createByString(default)).tooltip = tr('trial_modify_tip')
        edits.addTextBoxCommandInput('trial_changes_help', '', tr('trial_modify_tip'), 4, True)
        fields.addTextBoxCommandInput('record_details', '', '', 16, True)
        self.refresh(design, fields.itemById)

    def selected_record(self, get):
        selected = get('record_selector').selectedItem
        index = selected.index - 1 if selected is not None else -1
        if not 0 <= index < len(self.entries) or self.entries[index]['error']:
            raise ValueError(tr('probe_select'))
        return self.entries[index]['record']

    def trial_changes(self, get):
        record = self.selected_record(get)
        if not get('trial_modify').value:
            return None
        keys = ('pitch', 'tolerance') if record['parameters']['full_length'] else (
               'pitch', 'tolerance', 'start_offset', 'thread_length')
        return validate_trial_changes({key: get('trial_' + key).value for key in keys},
                                      record['parameters']['full_length'])

    def refresh(self, design, get):
        self.entries = list_records(design)
        items = get('record_selector').listItems
        items.clear()
        items.add(tr('choose_setting'), True)
        for index, entry in enumerate(self.entries):
            record = entry['record']
            label = f'{index + 1}: {entry["name"]}'
            if record:
                label += f' ({record["id"][:8]})'
            items.add(label, False)
        get('record_details').text = tr('records_count', count=len(self.entries))

    def show(self, design, get):
        selected = get('record_selector').selectedItem
        index = selected.index - 1 if selected is not None else -1
        if not 0 <= index < len(self.entries):
            get('record_details').text = tr('records_count', count=len(self.entries))
            return
        entry = self.entries[index]
        if entry['error']:
            get('record_details').text = entry['error']
            return
        record = entry['record']
        p = record['parameters']
        get('trial_modify').value = False
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
