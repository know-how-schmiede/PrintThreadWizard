"""Calibration tab and print profile controls, separate from the main dialog."""
import adsk.core
from ...core.calibration import CalibrationSeries
from ...core.thread_presets import load_print_profiles, save_print_profile, delete_print_profile
from ...localization import translate as tr


def add_tab(inputs):
    tab = inputs.addTabCommandInput('calibration_tab', tr('cal_tab')).children
    tab.addTextBoxCommandInput('cal_help', '', tr('cal_help'), 4, True)
    tab.addBoolValueInput('cal_enabled', tr('cal_enabled'), True, '', False)
    for key, label, value in (
        ('diameter', 'nominal_diameter', '20 mm'), ('pitch', 'pitch', '2 mm'),
        ('length', 'thread_length', '8 mm'), ('wall', 'cal_wall', '3 mm')):
        tab.addValueInput('cal_' + key, tr(label), 'mm', adsk.core.ValueInput.createByString(value))
    direction = tab.addDropDownCommandInput('cal_direction', tr('thread_direction'),
                                          adsk.core.DropDownStyles.TextListDropDownStyle)
    direction.listItems.add(tr('right_hand'), True)
    direction.listItems.add(tr('left_hand'), False)
    tab.addStringValueInput('cal_gaps', tr('cal_gaps'), '0.10; 0.15; 0.20; 0.25; 0.30')
    tab.addTextBoxCommandInput('cal_status', '', '', 3, True)
    group = tab.addGroupCommandInput('print_profiles', tr('print_profiles')).children
    group.addTextBoxCommandInput('profile_help', '', tr('profile_help'), 4, True)
    selector = group.addDropDownCommandInput('print_profile_selector', tr('print_profiles'),
                                            adsk.core.DropDownStyles.TextListDropDownStyle)
    refresh_profiles(selector)
    for key, label in (('name', 'name'), ('printer', 'profile_printer'),
                       ('material', 'profile_material'), ('orientation', 'profile_orientation'),
                       ('note', 'note')):
        group.addStringValueInput('profile_' + key, tr(label), '')
    for key, label, value in (
        ('nozzle', 'profile_nozzle', '0.4 mm'), ('layer_height', 'profile_layer', '0.2 mm'),
        ('tolerance', 'cal_gap', '0.2 mm'),
        ('diameter_min', 'profile_dmin', '0 mm'), ('diameter_max', 'profile_dmax', '0 mm'),
        ('pitch_min', 'profile_pmin', '0 mm'), ('pitch_max', 'profile_pmax', '0 mm')):
        group.addValueInput('profile_' + key, tr(label), 'mm', adsk.core.ValueInput.createByString(value))
    distribution = group.addDropDownCommandInput('profile_distribution', tr('clearance_distribution'),
                                                adsk.core.DropDownStyles.TextListDropDownStyle)
    for key in ('balanced', 'internal', 'external'):
        distribution.listItems.add(tr('distribution_' + key), key == 'internal')
    for key, label in (('save', 'save_current'), ('apply', 'profile_apply'), ('delete', 'delete')):
        group.addBoolValueInput('profile_' + key, tr(label), False, '', False)
    group.addTextBoxCommandInput('profile_status', '', '', 4, True)
    _add_tooltips(tab)


def _add_tooltips(inputs):
    """Include controls inside the print-profile group."""
    keys = {
        'cal_enabled': 'tip_cal_enabled', 'cal_diameter': 'tip_cal_diameter',
        'cal_pitch': 'tip_cal_pitch', 'cal_length': 'tip_cal_length',
        'cal_wall': 'tip_cal_wall', 'cal_direction': 'direction_help',
        'cal_gaps': 'tip_cal_gaps', 'print_profile_selector': 'tip_profile_selector',
        'profile_name': 'tip_profile_name', 'profile_printer': 'tip_profile_process',
        'profile_material': 'tip_profile_process', 'profile_orientation': 'tip_profile_orientation',
        'profile_note': 'tip_profile_note', 'profile_nozzle': 'tip_profile_process',
        'profile_layer_height': 'tip_profile_process', 'profile_tolerance': 'tip_profile_gap',
        'profile_distribution': 'distribution_help', 'profile_save': 'tip_profile_save',
        'profile_apply': 'tip_profile_apply', 'profile_delete': 'tip_profile_delete',
        **{f'profile_{field}': 'tip_profile_bounds' for field in
           ('diameter_min', 'diameter_max', 'pitch_min', 'pitch_max')},
    }
    for index in range(inputs.count):
        control = inputs.item(index)
        if control.id in keys:
            control.tooltip = tr(keys[control.id])
        children = getattr(control, 'children', None)
        if children is not None:
            _add_tooltips(children)


def refresh_profiles(selector, selected_id=None):
    selector.listItems.clear()
    selector.listItems.add(tr('choose_setting'), selected_id is None)
    for profile in load_print_profiles():
        selector.listItems.add(profile['name'], profile['id'] == selected_id)


def read_series(get):
    try:
        gaps = tuple(float(v.strip().replace(',', '.')) / 10
                     for v in get('cal_gaps').value.split(';'))
        return CalibrationSeries(*(get('cal_' + key).value for key in ('diameter', 'pitch', 'length')),
                                 clearances=gaps, wall=get('cal_wall').value,
                                 handedness=('right', 'left')[get('cal_direction').selectedItem.index]).validate()
    except (ValueError, TypeError, OverflowError):
        raise ValueError(tr('cal_invalid')) from None


def selected_profile(get):
    index = get('print_profile_selector').selectedItem.index - 1
    return load_print_profiles()[index] if index >= 0 else None


def handle_profile(key, get, apply):
    try:
        if key == 'print_profile_selector':
            profile = selected_profile(get)
            if profile is None:
                return
            for field in ('name', 'printer', 'material', 'orientation', 'note'):
                get('profile_' + field).value = profile[field]
            for field in ('nozzle', 'layer_height', 'tolerance', 'diameter_min', 'diameter_max', 'pitch_min', 'pitch_max'):
                get('profile_' + field).value = profile[field + '_cm'] or 0
            get('profile_distribution').listItems.item(
                ('balanced', 'internal', 'external').index(profile['clearance_distribution'])).isSelected = True
            get('profile_status').text = tr('profile_loaded')
            return
        if key not in ('profile_save', 'profile_apply', 'profile_delete') or not get(key).value:
            return
        get(key).value = False
        if key == 'profile_save':
            profile = {field: get('profile_' + field).value
                       for field in ('name', 'printer', 'material', 'orientation', 'note')}
            for field in ('nozzle', 'layer_height', 'tolerance', 'diameter_min', 'diameter_max', 'pitch_min', 'pitch_max'):
                value = get('profile_' + field).value
                profile[field + '_cm'] = None if field.startswith(('diameter_', 'pitch_')) and value == 0 else value
            profile['clearance_distribution'] = ('balanced', 'internal', 'external')[get('profile_distribution').selectedItem.index]
            profile = save_print_profile(profile)
            refresh_profiles(get('print_profile_selector'), profile['id'])
            get('profile_status').text = tr('saved', name=profile['name'])
        else:
            profile = selected_profile(get)
            if profile is None:
                raise ValueError(tr('choose_setting'))
            if key == 'profile_delete':
                delete_print_profile(profile['id'])
                refresh_profiles(get('print_profile_selector'))
                get('profile_status').text = tr('deleted', name=profile['name'])
            else:
                apply(profile)
                get('profile_status').text = tr('profile_applied')
    except (ValueError, OSError) as error:
        get('profile_status').text = str(error)
