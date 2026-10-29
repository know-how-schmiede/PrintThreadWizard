import os
import traceback
from dataclasses import replace

import adsk.core
import adsk.fusion

from ... import config
from ...core.iso_metric import ISO_FLANK_ANGLE, radial_thread_depth
from ...core.thread_parameters import ThreadParameters
from ...core.thread_pair import validate_pair
from ...core.thread_presets import (
    delete_thread_preset,
    export_thread_presets,
    import_thread_presets,
    load_default_tolerance,
    load_thread_presets,
    save_default_tolerance,
    save_thread_preset,
)
from ...fusion.face_analysis import analyze_cylinder
from ...fusion.thread_geometry import create_thread, thread_section
from ...lib import fusionAddInUtils as futil
from ...localization import detect_locale, set_locale, translate as tr
from ...version import VERSION
from . import calibration_tab, size_preview
from .records_tab import RecordInspector
from ...fusion.thread_reference_probe import probe_original_references
from ...fusion.thread_rebuild_trial import run_rebuild_trial
from ...fusion.thread_pair_edit import replace_linked_pair
from ...core.thread_records import pair_record_contexts
from ...fusion.thread_preview import ThreadPreview
from ...fusion.calibration import create_calibration
from ...core.calibration import profile_matches


app = adsk.core.Application.get()
ui = app.userInterface
LOCALE = detect_locale(adsk.core, app)
set_locale(LOCALE)

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = f'PrintThread Wizard {VERSION}'
CMD_DESCRIPTION = tr('description')

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
IS_PROMOTED = True

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')
THREAD_DIMENSIONS_IMAGE = os.path.join(ICON_FOLDER, 'thread_dimensions.png')
BRAND_LOGO_IMAGE = os.path.join(ICON_FOLDER, 'PrintThreadWizard_DialogLogo.png')

local_handlers = []
thread_preview = ThreadPreview()
record_inspector = RecordInspector()
updating_calculated_inputs = False
active_command_inputs = None
available_presets = []
loading_preset = False
table_refresh_serial = 0
table_delete_actions = {}
table_row_presets = {}

ISO_MODE_NAME = tr('iso_mode')
FREE_MODE_NAME = tr('free_mode')
TOLERANCE_OPTIONS = tuple(
    (f'{step * 0.05:.2f}'.replace('.', ',' if LOCALE != 'en' else '.') + ' mm', step * 0.005)
    for step in range(11)
)
FALLBACK_TOLERANCE_NAME = '0.15 mm' if LOCALE == 'en' else '0,15 mm'
CHAMFER_EXTRA_OPTIONS = tuple(
    (f'{step / 10:.1f}'.replace('.', ',' if LOCALE != 'en' else '.') + ' mm', step / 100)
    for step in range(11)
)


def start():
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    if command_definition is None:
        command_definition = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER
        )

    futil.add_handler(command_definition.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
    if panel is None:
        ui.messageBox("PrintThread Wizard: " + tr("panel_missing"))
        return

    control = panel.controls.itemById(CMD_ID)
    if control is None:
        control = panel.controls.addCommand(command_definition)
    control.isPromoted = IS_PROMOTED


def stop():
    thread_preview.clear()
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID) if workspace else None
    control = panel.controls.itemById(CMD_ID) if panel else None
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    if control:
        control.deleteMe()
    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    global active_command_inputs
    # Enable independent selection sets so an end edge can be selected for
    # both chamfer and start side. The API reference reverses these boolean
    # meanings; Autodesk's November 2024 release notes describe this behavior.
    args.command.hasDistinctSelectionSets = True
    inputs = args.command.commandInputs
    active_command_inputs = inputs

    version_text = inputs.addTextBoxCommandInput(
        'version_info', tr('version'), f'PrintThread Wizard {VERSION}', 1, True
    )
    version_text.isFullWidth = True

    create_tab = inputs.addTabCommandInput('create_tab', tr('create_tab'))
    create_inputs = create_tab.children
    management_tab = inputs.addTabCommandInput('management_tab', tr('manage_tab'))
    management_inputs = management_tab.children
    calibration_tab.add_tab(inputs)
    record_inspector.add_tab(inputs, adsk.fusion.Design.cast(app.activeProduct))
    info_tab = inputs.addTabCommandInput('info_tab', tr('info_tab'))
    info_inputs = info_tab.children

    brand_logo = info_inputs.addImageCommandInput('brand_logo', '', BRAND_LOGO_IMAGE)
    brand_logo.isFullWidth = True

    info_description = info_inputs.addTextBoxCommandInput(
        'info_description', '', tr('info_description'), 3, True
    )
    info_description.isFullWidth = True

    homepage_link = info_inputs.addTextBoxCommandInput(
        'homepage_link', '',
        tr('info_homepage', url='https://www.know-how-schmiede.de'),
        3, True
    )
    homepage_link.isFullWidth = True

    repository_link = info_inputs.addTextBoxCommandInput(
        'repository_link', '',
        tr('info_source', url='https://github.com/know-how-schmiede/PrintThreadWizard'),
        2, True
    )
    repository_link.isFullWidth = True

    update_info = info_inputs.addTextBoxCommandInput(
        'update_info', '',
        tr('info_updates', url='https://github.com/know-how-schmiede/PrintThreadWizard/releases'),
        2, True
    )
    update_info.isFullWidth = True

    issue_info = info_inputs.addTextBoxCommandInput(
        'issue_info', '',
        tr('info_issues', url='https://github.com/know-how-schmiede/PrintThreadWizard/issues'),
        3, True
    )
    issue_info.isFullWidth = True

    subscribe_info = info_inputs.addTextBoxCommandInput(
        'subscribe_info', '',
        tr('info_subscribe', url='https://www.youtube.com/@knowhowschmiede'),
        3, True
    )
    subscribe_info.isFullWidth = True

    face_input = create_inputs.addSelectionInput(
        'target_face', tr('target_face'), tr('select_face')
    )
    face_input.addSelectionFilter('Faces')
    # Both command modes share this dialog. Keep native selections optional;
    # _request_errors requires a face only when creating a model thread.
    face_input.setSelectionLimits(0, 1)

    edge_input = create_inputs.addSelectionInput(
        'chamfer_edges', tr('chamfer_edges'), tr('select_edges')
    )
    edge_input.addSelectionFilter('Edges')
    edge_input.setSelectionLimits(0, 2)

    chamfer_extra = create_inputs.addDropDownCommandInput(
        'chamfer_extra', tr('chamfer_extra'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    chamfer_extra.tooltip = tr('chamfer_extra_help')
    for name, value in CHAMFER_EXTRA_OPTIONS:
        chamfer_extra.listItems.add(name, value == 0.0)

    preset_selector = create_inputs.addDropDownCommandInput(
        'preset_selector', tr('saved_setting'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )

    default_units = app.activeProduct.unitsManager.defaultLengthUnits
    create_inputs.addBoolValueInput('full_length', tr('full_length'), True, '', True)
    start_edge = create_inputs.addSelectionInput('start_edge', tr('start_edge'), tr('start_edge_help'))
    start_edge.addSelectionFilter('CircularEdges')
    start_edge.setSelectionLimits(0, 1)
    start_edge.isVisible = False
    for input_id, label, initial in (('start_offset', 'start_offset', '0 mm'),
                                      ('thread_length', 'thread_length', '15 mm')):
        field = create_inputs.addValueInput(input_id, tr(label), default_units,
                                           adsk.core.ValueInput.createByString(initial))
        field.isVisible = False
    create_inputs.addBoolValueInput('pair_mode', tr('pair_mode'), True, '', False)
    distribution = create_inputs.addDropDownCommandInput(
        'clearance_distribution', tr('clearance_distribution'),
        adsk.core.DropDownStyles.TextListDropDownStyle)
    distribution.tooltip = tr('distribution_help')
    for index, key in enumerate(('balanced', 'internal', 'external')):
        distribution.listItems.add(tr('distribution_' + key), index == 0)
    partner = create_inputs.addGroupCommandInput('partner_group', tr('partner_group'))
    partner.isExpanded = True
    partner.isVisible = False
    second = partner.children
    for input_id, label, selection_filter, maximum in (
        ('partner_face', 'target_face', 'Faces', 1),
        ('partner_chamfer_edges', 'chamfer_edges', 'Edges', 2),
        ('partner_start_edge', 'start_edge', 'CircularEdges', 1),
    ):
        selection = second.addSelectionInput(input_id, tr(label), tr(label))
        selection.addSelectionFilter(selection_filter)
        selection.setSelectionLimits(0, maximum)
    second.addBoolValueInput('partner_full_length', tr('full_length'), True, '', True)
    for input_id, label, initial in (
        ('partner_start_offset', 'start_offset', '0 mm'),
        ('partner_thread_length', 'thread_length', '15 mm'),
    ):
        second.addValueInput(input_id, tr(label), default_units,
                             adsk.core.ValueInput.createByString(initial))
    _update_pair_visibility(inputs)
    mode_input = create_inputs.addDropDownCommandInput(
        'calculation_mode', tr('calculation'), adsk.core.DropDownStyles.TextListDropDownStyle
    )
    mode_input.listItems.add(ISO_MODE_NAME, True)
    mode_input.listItems.add(FREE_MODE_NAME, False)

    direction_input = create_inputs.addDropDownCommandInput(
        'handedness', tr('thread_direction'), adsk.core.DropDownStyles.TextListDropDownStyle
    )
    direction_input.tooltip = tr('direction_help')
    direction_input.listItems.add(tr('right_hand'), True)
    direction_input.listItems.add(tr('left_hand'), False)

    create_inputs.addValueInput(
        'flank_angle', tr('profile_angle'), 'deg', adsk.core.ValueInput.createByString('60 deg')
    )
    create_inputs.addValueInput(
        'thread_depth', tr('thread_depth'), default_units,
        adsk.core.ValueInput.createByString(f'5 {default_units}')
    )
    create_inputs.addValueInput(
        'pitch', tr('pitch'), default_units,
        adsk.core.ValueInput.createByString(f'10 {default_units}')
    )
    create_inputs.addValueInput(
        'fillet_radius', tr('fillet_radius'), default_units,
        adsk.core.ValueInput.createByString('0.4 mm')
    )
    tolerance_input = create_inputs.addDropDownCommandInput(
        'tolerance', tr('tolerance'), adsk.core.DropDownStyles.TextListDropDownStyle
    )
    default_tolerance_name = _tolerance_name(load_default_tolerance())
    for name, _ in TOLERANCE_OPTIONS:
        tolerance_input.listItems.add(name, name == default_tolerance_name)

    result_text = create_inputs.addTextBoxCommandInput(
        'result_text', tr('result'),
        tr('select_face_result'), 9, True
    )
    result_text.isFullWidth = True

    size_preview.add_controls(create_inputs)

    dimensions_group = create_inputs.addGroupCommandInput(
        'dimensions_group', tr('dimensions_group')
    )
    dimensions_group.isExpanded = False
    dimensions_image = dimensions_group.children.addImageCommandInput(
        'thread_dimensions_image', '', THREAD_DIMENSIONS_IMAGE
    )
    dimensions_image.isFullWidth = True

    preset_table = management_inputs.addTableCommandInput(
        'preset_table', '', 5, '3:1:1:1:1'
    )
    preset_table.isFullWidth = True
    preset_table.minimumVisibleRows = 3
    preset_table.maximumVisibleRows = 8
    preset_table.tablePresentationStyle = (
        adsk.core.TablePresentationStyles.itemBorderTablePresentationStyle
    )
    preset_table.hasGrid = False

    management_details = management_inputs.addTextBoxCommandInput(
        'management_details', '', tr('no_row'), 7, True
    )
    management_details.isFullWidth = True

    transfer_group = management_inputs.addGroupCommandInput(
        'transfer_group', tr('json_group')
    )
    transfer_inputs = transfer_group.children
    transfer_buttons = transfer_inputs.addTableCommandInput(
        'transfer_buttons', '', 2, '1:1'
    )
    transfer_buttons.minimumVisibleRows = 1
    transfer_buttons.maximumVisibleRows = 1
    transfer_buttons.hasGrid = False
    transfer_buttons.isFullWidth = True
    transfer_buttons.tablePresentationStyle = (
        adsk.core.TablePresentationStyles.itemBorderTablePresentationStyle
    )
    export_button = transfer_inputs.addBoolValueInput(
        'export_presets', tr('export'), False, '', False
    )
    import_button = transfer_inputs.addBoolValueInput(
        'import_presets', tr('import'), False, '', False
    )
    transfer_buttons.addCommandInput(export_button, 0, 0)
    transfer_buttons.addCommandInput(import_button, 0, 1)
    transfer_status = transfer_inputs.addTextBoxCommandInput(
        'transfer_status', '', '', 2, True
    )
    transfer_status.isFullWidth = True

    default_tolerance_input = management_inputs.addDropDownCommandInput(
        'default_tolerance', tr('default_tolerance'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    for name, _ in TOLERANCE_OPTIONS:
        default_tolerance_input.listItems.add(name, name == default_tolerance_name)
    management_inputs.addBoolValueInput(
        'save_default_tolerance', tr('set_default'), False, '', False
    )
    default_status = management_inputs.addTextBoxCommandInput(
        'default_tolerance_status', '', '', 2, True
    )
    default_status.isFullWidth = True

    preset_group = create_inputs.addGroupCommandInput(
        'preset_group', tr('save_group')
    )
    preset_group.isExpanded = False
    preset_inputs = preset_group.children
    preset_inputs.addStringValueInput('preset_name', tr('thread_name'), '')
    preset_inputs.addTextBoxCommandInput(
        'preset_note', tr('short_note'), '', 2, False
    )
    preset_inputs.addBoolValueInput(
        'save_preset', tr('save_current'), False, '', False
    )
    preset_status = preset_inputs.addTextBoxCommandInput(
        'preset_status', '', '', 2, True
    )
    preset_status.isFullWidth = True

    _refresh_preset_selectors(inputs)
    _apply_calculation_mode(inputs)

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_execute_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute_preview(args: adsk.core.CommandEventArgs):
    # Fusion rolls back the previous preview transaction before this event.
    # Graphics created in inputChanged can disappear in that rollback.
    if _record_probe_enabled(args.command.commandInputs):
        thread_preview.clear()
    else:
        _update_assistance(args.command.commandInputs, draw_preview=True)
    # Schematic graphics are not the command result. OK must still execute
    # the real thread/calibration creation rather than commit this preview.
    args.isValidResult = False


def command_execute(args: adsk.core.CommandEventArgs):
    thread_preview.clear()
    try:
        if _record_probe_enabled(args.command.commandInputs):
            if _record_view_only(args.command.commandInputs):
                return
            record = record_inspector.selected_record(lambda key: _input_by_id(args.command.commandInputs, key))
            if _record_pair_edit_enabled(args.command.commandInputs):
                replace_linked_pair(adsk.fusion.Design.cast(app.activeProduct), record,
                    record_inspector.trial_changes(lambda key: _input_by_id(args.command.commandInputs, key)),
                    _validation_errors, create_thread, analyze_cylinder, validate_pair)
                ui.messageBox(tr('pair_edit_done'))
                return
            if _record_apply_edit_enabled(args.command.commandInputs):
                run_rebuild_trial(adsk.fusion.Design.cast(app.activeProduct), record,
                    _validation_errors, create_thread,
                    changes=record_inspector.trial_changes(lambda key: _input_by_id(args.command.commandInputs, key)),
                    replace_original=True)
                ui.messageBox(tr('edit_done'))
                return
            if _record_rebuild_trial_enabled(args.command.commandInputs):
                run_rebuild_trial(adsk.fusion.Design.cast(app.activeProduct), record,
                                  _validation_errors, create_thread,
                                  changes=record_inspector.trial_changes(lambda key: _input_by_id(args.command.commandInputs, key)))
                # A successful trial must NEVER commit its inserted geometry.
                args.executeFailed = True
                args.executeFailedMessage = tr('trial_rolled_back')
                futil.log(tr('trial_rolled_back'))
                return
            result = probe_original_references(adsk.fusion.Design.cast(app.activeProduct), record, _validation_errors)
            lines = [tr('probe_success' if result['ready'] else 'probe_incomplete')]
            for key, number, state in result['references']:
                lines.append(f'{tr("record_ref_" + key)} {number + 1 if key == "chamfer_edges" else ""}: {state}')
            lines.extend(error for error in result['errors'] if error not in lines)
            ui.messageBox('\n'.join(lines))
            return
        if _calibration_enabled(args.command.commandInputs):
            create_calibration(adsk.fusion.Design.cast(app.activeProduct),
                               calibration_tab.read_series(lambda key: _input_by_id(args.command.commandInputs, key)))
            return
        _apply_calculation_mode(args.command.commandInputs)
        parameters = _read_parameters(args.command.commandInputs)
        errors = _request_errors(args.command.commandInputs, parameters)
        if errors:
            raise ValueError('\n'.join(errors))

        # Both creations belong to this command transaction. Any exception
        # reaches executeFailed below and rolls back the complete pair.
        partner = _partner_parameters(args.command.commandInputs, parameters)
        contexts = pair_record_contexts() if partner is not None else (None, None)
        mode = 'iso_metric' if _is_iso_mode(args.command.commandInputs) else 'free'
        create_thread(parameters, calculation_mode=mode, record_context=contexts[0])
        if partner is not None:
            create_thread(partner, calculation_mode=mode, record_context=contexts[1])
        futil.log(f"{CMD_NAME}: {tr('thread_created')}")
    except Exception as error:
        # Abort the entire Fusion command transaction, including target-body edits.
        args.executeFailed = True
        args.executeFailedMessage = str(error)
        futil.log(f'{CMD_NAME}: {error}; {error.__cause__ or error}\n{traceback.format_exc()}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)
        ui.messageBox(f'PrintThread Wizard:\n{error}')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    global loading_preset
    if loading_preset:
        return
    if args.input.id == 'record_action':
        if args.input.selectedItem.index > 0:
            _input_by_id(active_command_inputs, 'cal_enabled').value = False
        record_inspector.update_action_help(lambda key: _input_by_id(active_command_inputs, key))
        return
    if args.input.id == 'cal_enabled' and args.input.value:
        _input_by_id(active_command_inputs, 'record_action').listItems.item(0).isSelected = True
    if args.input.id in ('record_selector', 'records_refresh'):
        design = adsk.fusion.Design.cast(app.activeProduct)
        get = lambda key: _input_by_id(active_command_inputs, key)
        if args.input.id == 'records_refresh':
            if args.input.value:
                args.input.value = False
                record_inspector.refresh(design, get)
        else:
            record_inspector.show(design, get)
        return
    if args.input.id == 'apply_metric_size' and args.input.value:
        args.input.value = False
        selected = size_preview.selected_size(lambda key: _input_by_id(active_command_inputs, key))
        if selected is not None:
            loading_preset = True
            try:
                _input_by_id(active_command_inputs, 'pitch').value = selected[1]
                _select_dropdown_item(_input_by_id(active_command_inputs, 'calculation_mode'), ISO_MODE_NAME)
            finally:
                loading_preset = False
            _apply_calculation_mode(active_command_inputs)
            _update_result_text(active_command_inputs)
        return
    if args.input.id in ('metric_size', 'light_preview', 'cal_enabled'):
        _update_assistance(active_command_inputs)
        return
    if args.input.id.startswith('profile_') or args.input.id == 'print_profile_selector':
        calibration_tab.handle_profile(args.input.id,
            lambda key: _input_by_id(active_command_inputs, key), _apply_print_profile)
        return
    if args.input.id in ('pair_mode', 'partner_full_length'):
        _update_pair_visibility(active_command_inputs)
    if args.input.id == 'full_length':
        for input_id in ('start_edge', 'start_offset', 'thread_length'):
            _input_by_id(active_command_inputs, input_id).isVisible = not args.input.value
    if args.input.id == 'preset_selector':
        _load_selected_preset(active_command_inputs, 'preset_selector')
        return
    if args.input.id == 'preset_table' or args.input.id.startswith('preset_table_'):
        _show_selected_table_details(active_command_inputs)
        return
    if args.input.id in table_delete_actions:
        if args.input.value:
            args.input.value = False
            _delete_preset(active_command_inputs, table_delete_actions[args.input.id])
        return
    if args.input.id == 'export_presets':
        if args.input.value:
            args.input.value = False
            _export_presets(active_command_inputs)
        return
    if args.input.id == 'import_presets':
        if args.input.value:
            args.input.value = False
            _import_presets(active_command_inputs)
        return
    if args.input.id == 'save_default_tolerance':
        if args.input.value:
            _save_default_tolerance(active_command_inputs)
            args.input.value = False
        return
    if args.input.id == 'save_preset':
        if args.input.value:
            _save_current_preset(active_command_inputs)
            args.input.value = False
        return
    if args.input.id in (
        'pair_mode', 'partner_face', 'partner_chamfer_edges', 'partner_start_edge',
        'partner_full_length', 'partner_start_offset', 'partner_thread_length',
        'clearance_distribution', 'target_face',
        'pitch',
        'calculation_mode',
        'handedness',
        'full_length', 'start_edge', 'start_offset', 'thread_length', 'chamfer_edges',
        'flank_angle',
        'thread_depth',
        'fillet_radius',
        'tolerance', 'chamfer_extra',
    ):
        _apply_calculation_mode(active_command_inputs)
        _update_result_text(active_command_inputs)


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    if _record_probe_enabled(active_command_inputs):
        if _record_view_only(active_command_inputs):
            args.areInputsValid = True
            return
        try:
            record = record_inspector.selected_record(lambda key: _input_by_id(active_command_inputs, key))
            if _record_pair_edit_enabled(active_command_inputs) and not record.get('pair_id'):
                raise ValueError(tr('pair_edit_missing'))
            if (_record_apply_edit_enabled(active_command_inputs) or _record_pair_edit_enabled(active_command_inputs)) and not record['references'].get('owned_features'):
                raise ValueError(tr('edit_ownership_missing'))
            if _record_rebuild_trial_enabled(active_command_inputs) or _record_apply_edit_enabled(active_command_inputs) or _record_pair_edit_enabled(active_command_inputs):
                record_inspector.trial_changes(lambda key: _input_by_id(active_command_inputs, key))
            args.areInputsValid = True
        except ValueError as error:
            _input_by_id(active_command_inputs, 'record_details').text = str(error)
            _input_by_id(active_command_inputs, 'edit_availability').text = str(error)
            args.areInputsValid = False
        return
    if _calibration_enabled(active_command_inputs):
        try:
            series = calibration_tab.read_series(lambda key: _input_by_id(active_command_inputs, key))
            _input_by_id(active_command_inputs, 'cal_status').text = '\n'.join(
                label for label, gap, x in series.specimens())
            args.areInputsValid = True
        except ValueError as error:
            _input_by_id(active_command_inputs, 'cal_status').text = str(error)
            args.areInputsValid = False
        return
    _apply_calculation_mode(active_command_inputs)
    parameters = _read_parameters(active_command_inputs)
    errors = _request_errors(active_command_inputs, parameters)
    args.areInputsValid = not errors
    _set_result_text(active_command_inputs, errors)


def command_destroy(args: adsk.core.CommandEventArgs):
    thread_preview.clear()
    global local_handlers, active_command_inputs, available_presets
    global table_delete_actions, table_row_presets
    local_handlers = []
    active_command_inputs = None
    available_presets = []
    table_delete_actions = {}
    table_row_presets = {}


def _input_by_id(inputs, input_id):
    """Sucht auch in Gruppen und Tabs nach einer Dialogeingabe."""
    direct_input = inputs.itemById(input_id)
    if direct_input is not None:
        return direct_input
    for index in range(inputs.count):
        command_input = inputs.item(index)
        children = getattr(command_input, 'children', None)
        if children is not None:
            nested_input = _input_by_id(children, input_id)
            if nested_input is not None:
                return nested_input
    return None


def _refresh_preset_selectors(inputs, selected_id=None):
    global available_presets, loading_preset
    previous_loading_state = loading_preset
    loading_preset = True
    try:
        available_presets = load_thread_presets()
        for selector_id in ('preset_selector',):
            selector = _input_by_id(inputs, selector_id)
            selector.listItems.clear()
            selector.listItems.add(tr('choose_setting'), selected_id is None)
            for preset in available_presets:
                selector.listItems.add(preset['name'], preset.get('id') == selected_id)
        _populate_preset_table(inputs)
    except Exception as error:
        status = _input_by_id(inputs, 'preset_status')
        if status is not None:
            status.text = str(error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)
    finally:
        loading_preset = previous_loading_state


def _populate_preset_table(inputs):
    global table_refresh_serial, table_delete_actions, table_row_presets
    table = _input_by_id(inputs, 'preset_table')
    if table is None:
        return
    table.clear()
    table_delete_actions = {}
    table_row_presets = {}
    table_refresh_serial += 1
    cell_inputs = table.commandInputs
    units = app.activeProduct.unitsManager
    length_units = units.defaultLengthUnits

    rows = [(tr('name'), 'α', 'h', 'P', tr('action'))]
    for preset in available_presets:
        settings = preset.get('settings', {})
        rows.append((
            str(preset.get('name', '')),
            _format_table_value(units, settings.get('flank_angle_rad'), 'deg'),
            _format_table_value(units, settings.get('thread_depth_cm'), length_units),
            _format_table_value(units, settings.get('pitch_cm'), length_units),
            '',
        ))

    for row_index, row_values in enumerate(rows):
        if row_index > 0:
            table_row_presets[row_index] = available_presets[row_index - 1]['id']
        for column_index, value in enumerate(row_values):
            if row_index > 0 and column_index == 4:
                input_id = f'delete_preset_{table_refresh_serial}_{row_index}'
                delete_button = cell_inputs.addBoolValueInput(
                    input_id, tr('delete'), False, '', False
                )
                table.addCommandInput(delete_button, row_index, column_index)
                table_delete_actions[input_id] = available_presets[row_index - 1]['id']
                continue
            text_value = f'<b>{value}</b>' if row_index == 0 else value
            cell = cell_inputs.addTextBoxCommandInput(
                f'preset_table_{table_refresh_serial}_{row_index}_{column_index}',
                '', text_value, 1, True
            )
            table.addCommandInput(cell, row_index, column_index)


def _format_table_value(units, value, unit_name):
    if value is None:
        return '–'
    try:
        return units.formatInternalValue(float(value), unit_name, True)
    except (TypeError, ValueError):
        return '–'


def _save_default_tolerance(inputs):
    status = _input_by_id(inputs, 'default_tolerance_status')
    try:
        dropdown = _input_by_id(inputs, 'default_tolerance')
        selected_name = dropdown.selectedItem.name
        value = dict(TOLERANCE_OPTIONS)[selected_name]
        save_default_tolerance(value)
        _select_dropdown_item(_input_by_id(inputs, 'tolerance'), selected_name)
        status.text = tr('default_saved', value=selected_name)
        _update_result_text(inputs)
    except Exception as error:
        status.text = str(error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)


def _selected_preset(inputs, selector_id):
    selector = _input_by_id(inputs, selector_id)
    if selector is None or selector.selectedItem is None:
        return None
    preset_index = selector.selectedItem.index - 1
    if preset_index < 0 or preset_index >= len(available_presets):
        return None
    return available_presets[preset_index]


def _load_selected_preset(inputs, selector_id):
    global loading_preset
    preset = _selected_preset(inputs, selector_id)
    if preset is None:
        return

    loading_preset = True
    try:
        _input_by_id(inputs, 'metric_size').listItems.item(0).isSelected = True
        settings = preset['settings']
        _input_by_id(inputs, 'pair_mode').value = settings.get('pair_mode', False)
        _input_by_id(inputs, 'clearance_distribution').listItems.item(
            ('balanced', 'internal', 'external').index(settings.get('clearance_distribution', 'balanced'))).isSelected = True
        for key, default in (('full_length', True), ('start_offset', 0.0), ('thread_length', 1.0)):
            storage_key = 'partner_' + key + ('' if key == 'full_length' else '_cm')
            _input_by_id(inputs, 'partner_' + key).value = settings.get(storage_key, default)
        _update_pair_visibility(inputs)
        _input_by_id(inputs, 'full_length').value = settings.get('full_length', True)
        _input_by_id(inputs, 'start_offset').value = settings.get('start_offset_cm', 0.0)
        _input_by_id(inputs, 'thread_length').value = settings.get('thread_length_cm', 1.0)
        for input_id in ('start_edge', 'start_offset', 'thread_length'):
            _input_by_id(inputs, input_id).isVisible = not settings.get('full_length', True)
        _select_dropdown_item(
            _input_by_id(inputs, 'handedness'),
            tr('left_hand' if settings.get('handedness', 'right') == 'left' else 'right_hand'),
        )
        mode_name = (
            ISO_MODE_NAME if settings['calculation_mode'] == 'iso_metric' else FREE_MODE_NAME
        )
        _select_dropdown_item(_input_by_id(inputs, 'calculation_mode'), mode_name)
        _input_by_id(inputs, 'flank_angle').value = float(settings['flank_angle_rad'])
        _input_by_id(inputs, 'thread_depth').value = float(settings['thread_depth_cm'])
        _input_by_id(inputs, 'pitch').value = float(settings['pitch_cm'])
        _input_by_id(inputs, 'fillet_radius').value = float(settings['fillet_radius_cm'])

        tolerance_value = float(settings.get('tolerance_cm', 0.0))
        extra_value = float(settings.get('chamfer_extra_cm', 0.0))
        extra_name = min(
            CHAMFER_EXTRA_OPTIONS, key=lambda option: abs(option[1] - extra_value)
        )[0]
        _select_dropdown_item(_input_by_id(inputs, 'chamfer_extra'), extra_name)
        tolerance_name = min(
            TOLERANCE_OPTIONS, key=lambda option: abs(option[1] - tolerance_value)
        )[0]
        _select_dropdown_item(_input_by_id(inputs, 'tolerance'), tolerance_name)
        _apply_calculation_mode(inputs)
        _update_result_text(inputs)
    except (KeyError, TypeError, ValueError) as error:
        result = _input_by_id(inputs, 'result_text')
        result.text = tr(
            'preset_incomplete', name=preset.get('name', ''), error=error
        )
    finally:
        loading_preset = False


def _select_dropdown_item(dropdown, item_name):
    for index in range(dropdown.listItems.count):
        item = dropdown.listItems.item(index)
        if item.name == item_name:
            item.isSelected = True
            return


def _show_selected_table_details(inputs):
    table = _input_by_id(inputs, 'preset_table')
    details = _input_by_id(inputs, 'management_details')
    preset_id = table_row_presets.get(table.selectedRow) if table is not None else None
    preset = next(
        (item for item in available_presets if item.get('id') == preset_id), None
    )
    if preset is None:
        details.text = tr('no_row')
        return
    settings = preset.get('settings', {})
    mode = tr('profile_mode_iso') if settings.get('calculation_mode') == 'iso_metric' else tr('profile_mode_free')
    units = app.activeProduct.unitsManager
    length_units = units.defaultLengthUnits
    details.text = (
        f'{tr("details_name")}: {preset.get("name", "")}\n'
        f'{tr("note")}: {preset.get("note", "–") or "–"}\n'
        f'{tr("mode")}: {mode}\n'
        f'{tr("pair_mode")}: {tr("yes" if settings.get("pair_mode", False) else "no")}\n'
        f'{tr("clearance_distribution")}: {tr("distribution_" + settings.get("clearance_distribution", "balanced"))}\n'
        f'{tr("thread_direction")}: {tr("left_hand" if settings.get("handedness", "right") == "left" else "right_hand")}\n'
        f'{tr("full_length")}: {tr("yes" if settings.get("full_length", True) else "no")}\n'
        f'{tr("start_offset")}: {_format_table_value(units, settings.get("start_offset_cm", 0.0), length_units)}\n'
        f'{tr("thread_length")}: {_format_table_value(units, settings.get("thread_length_cm", 1.0), length_units)}\n'
        f'{tr("partner_group")} – {tr("full_length")}: {tr("yes" if settings.get("partner_full_length", True) else "no")}\n'
        f'{tr("partner_group")} – {tr("start_offset")}: {_format_table_value(units, settings.get("partner_start_offset_cm", 0.0), length_units)}\n'
        f'{tr("partner_group")} – {tr("thread_length")}: {_format_table_value(units, settings.get("partner_thread_length_cm", 1.0), length_units)}\n'
        f'{tr("profile_angle")}: {_format_table_value(units, settings.get("flank_angle_rad"), "deg")}\n'
        f'{tr("thread_depth")}: {_format_table_value(units, settings.get("thread_depth_cm"), length_units)}\n'
        f'{tr("pitch")}: {_format_table_value(units, settings.get("pitch_cm"), length_units)}\n'
        f'{tr("saved_at")}: {preset.get("created_at", "–")}'
    )


def _delete_preset(inputs, preset_id):
    global available_presets
    preset = next((item for item in available_presets if item.get('id') == preset_id), None)
    if preset is None:
        return
    answer = ui.messageBox(
        tr('confirm_delete', name=preset.get('name', '')),
        'PrintThread Wizard',
        adsk.core.MessageBoxButtonTypes.YesNoButtonType,
        adsk.core.MessageBoxIconTypes.QuestionIconType,
    )
    if answer != adsk.core.DialogResults.DialogYes:
        return
    if delete_thread_preset(preset_id):
        table = _input_by_id(inputs, 'preset_table')
        row = next(
            (row_index for row_index, row_id in table_row_presets.items() if row_id == preset_id),
            None,
        )
        if table is not None and row is not None:
            for column in range(5):
                cell_input = table.getInputAtPosition(row, column)
                if cell_input is not None:
                    cell_input.isVisible = False
        table_row_presets.pop(row, None)
        available_presets = load_thread_presets()
        _refresh_quick_selector(inputs)
        _input_by_id(inputs, 'management_details').text = (
            tr('deleted', name=preset.get('name', ''))
        )


def _refresh_quick_selector(inputs):
    global loading_preset
    previous_loading_state = loading_preset
    loading_preset = True
    try:
        selector = _input_by_id(inputs, 'preset_selector')
        selector.listItems.clear()
        selector.listItems.add(tr('choose_setting'), True)
        for preset in available_presets:
            selector.listItems.add(preset['name'], False)
    finally:
        loading_preset = previous_loading_state


def _export_presets(inputs):
    status = _input_by_id(inputs, 'transfer_status')
    try:
        dialog = ui.createFileDialog()
        dialog.title = tr('export_title')
        dialog.filter = tr('json_filter')
        dialog.initialFilename = 'PrintThreadWizard-settings.json'
        if dialog.showSave() != adsk.core.DialogResults.DialogOK:
            status.text = tr('export_cancelled')
            return
        filename = dialog.filename
        if not filename.lower().endswith('.json'):
            filename += '.json'
        count = export_thread_presets(filename)
        status.text = tr('export_ok', count=count)
    except Exception as error:
        status.text = tr('export_failed', error=error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)


def _import_presets(inputs):
    status = _input_by_id(inputs, 'transfer_status')
    try:
        dialog = ui.createFileDialog()
        dialog.title = tr('import_title')
        dialog.filter = tr('json_filter')
        dialog.isMultiSelectEnabled = False
        if dialog.showOpen() != adsk.core.DialogResults.DialogOK:
            status.text = tr('import_cancelled')
            return
        count = import_thread_presets(dialog.filename)
        _refresh_preset_selectors(inputs)
        calibration_tab.refresh_profiles(_input_by_id(inputs, 'print_profile_selector'))
        default_name = _tolerance_name(load_default_tolerance())
        _select_dropdown_item(_input_by_id(inputs, 'default_tolerance'), default_name)
        status.text = tr('import_ok', count=count)
    except Exception as error:
        status.text = tr('import_failed', error=error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)


def _read_parameters(inputs):
    face_input = _input_by_id(inputs, 'target_face')
    face = face_input.selection(0).entity if face_input and face_input.selectionCount else None

    edge_input = _input_by_id(inputs, 'chamfer_edges')
    edges = tuple(
        edge_input.selection(index).entity for index in range(edge_input.selectionCount)
    ) if edge_input else ()

    return ThreadParameters(
        face=face,
        chamfer_edges=edges,
        flank_angle=_input_by_id(inputs, 'flank_angle').value,
        thread_depth=_input_by_id(inputs, 'thread_depth').value,
        pitch=_input_by_id(inputs, 'pitch').value,
        fillet_radius=_input_by_id(inputs, 'fillet_radius').value,
        tolerance=_selected_tolerance(inputs),
        clearance_distribution=('balanced', 'internal', 'external')[
            _input_by_id(inputs, 'clearance_distribution').selectedItem.index],
        handedness='left' if _input_by_id(inputs, 'handedness').selectedItem.index == 1 else 'right',
        full_length=_input_by_id(inputs, 'full_length').value,
        start_offset=_input_by_id(inputs, 'start_offset').value,
        thread_length=_input_by_id(inputs, 'thread_length').value,
        start_edge=(_input_by_id(inputs, 'start_edge').selection(0).entity
                    if _input_by_id(inputs, 'start_edge').selectionCount else None),
        chamfer_extra=dict(CHAMFER_EXTRA_OPTIONS)[
            _input_by_id(inputs, 'chamfer_extra').selectedItem.name
        ],
    )


def _update_pair_visibility(inputs):
    enabled = _input_by_id(inputs, 'pair_mode').value
    _input_by_id(inputs, 'partner_group').isVisible = enabled
    partial = not _input_by_id(inputs, 'partner_full_length').value
    for key in ('start_edge', 'start_offset', 'thread_length'):
        _input_by_id(inputs, 'partner_' + key).isVisible = partial


def _partner_parameters(inputs, parameters):
    if not _input_by_id(inputs, 'pair_mode').value:
        return None
    def selected(key):
        field = _input_by_id(inputs, 'partner_' + key)
        return tuple(field.selection(i).entity for i in range(field.selectionCount))
    faces = selected('face')
    starts = selected('start_edge')
    depth = parameters.thread_depth
    if faces and _is_iso_mode(inputs):
        depth = radial_thread_depth(parameters.pitch, analyze_cylinder(faces[0]).is_external)
    return replace(parameters, face=faces[0] if faces else None,
                   chamfer_edges=selected('chamfer_edges'),
                   start_edge=starts[0] if starts else None,
                   full_length=_input_by_id(inputs, 'partner_full_length').value,
                   start_offset=_input_by_id(inputs, 'partner_start_offset').value,
                   thread_length=_input_by_id(inputs, 'partner_thread_length').value,
                   thread_depth=depth)


def _request_errors(inputs, parameters):
    errors = _validation_errors(parameters)
    try:
        partner = _partner_parameters(inputs, parameters)
        if partner is not None:
            errors.extend(tr('partner_group') + ': ' + e for e in _validation_errors(partner))
            if not errors:
                validate_pair(analyze_cylinder(parameters.face), analyze_cylinder(partner.face))
    except ValueError as error:
        errors.append(str(error))
    return errors


def _selected_tolerance(inputs):
    tolerance_input = _input_by_id(inputs, 'tolerance')
    selected_name = (
        tolerance_input.selectedItem.name
        if tolerance_input and tolerance_input.selectedItem
        else FALLBACK_TOLERANCE_NAME
    )
    return dict(TOLERANCE_OPTIONS)[selected_name]


def _tolerance_name(value):
    return min(TOLERANCE_OPTIONS, key=lambda option: abs(option[1] - value))[0]


def _save_current_preset(inputs):
    status = _input_by_id(inputs, 'preset_status')
    try:
        _apply_calculation_mode(inputs)
        parameters = _read_parameters(inputs)
        parameter_errors = [
            error for error in parameters.validation_errors()
            if error != tr('face_required')
        ]
        if parameter_errors:
            raise ValueError('\n'.join(parameter_errors))

        context = _preset_face_context(parameters.face)
        settings = {
            'calculation_mode': 'iso_metric' if _is_iso_mode(inputs) else 'free',
            'flank_angle_rad': parameters.flank_angle,
            'thread_depth_cm': parameters.thread_depth,
            'pitch_cm': parameters.pitch,
            'fillet_radius_cm': parameters.fillet_radius,
            'tolerance_cm': parameters.tolerance,
            'chamfer_extra_cm': parameters.chamfer_extra,
            'clearance_distribution': parameters.clearance_distribution,
            'pair_mode': _input_by_id(inputs, 'pair_mode').value,
            'partner_full_length': _input_by_id(inputs, 'partner_full_length').value,
            'partner_start_offset_cm': _input_by_id(inputs, 'partner_start_offset').value,
            'partner_thread_length_cm': _input_by_id(inputs, 'partner_thread_length').value,
            'handedness': parameters.handedness,
            'full_length': parameters.full_length,
            'start_offset_cm': parameters.start_offset,
            'thread_length_cm': parameters.thread_length,
            'display_length_units': app.activeProduct.unitsManager.defaultLengthUnits,
            **context,
        }
        preset = save_thread_preset(
            _input_by_id(inputs, 'preset_name').value,
            _input_by_id(inputs, 'preset_note').text,
            settings,
        )
        status.text = tr('saved', name=preset['name'])
        _refresh_preset_selectors(inputs, preset['id'])
        futil.log(f"{CMD_NAME}: {tr('saved', name=preset['name'])}")
    except Exception as error:
        status.text = str(error)
        futil.log(f'{CMD_NAME}: {error}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)


def _preset_face_context(face):
    if face is None:
        return {}
    try:
        cylinder = analyze_cylinder(face)
        return {
            'thread_type': 'external' if cylinder.is_external else 'internal',
            'nominal_diameter_cm': cylinder.radius * 2,
        }
    except ValueError:
        return {}


def _is_iso_mode(inputs):
    mode_input = _input_by_id(inputs, 'calculation_mode')
    return bool(mode_input and mode_input.selectedItem.name == ISO_MODE_NAME)


def _apply_calculation_mode(inputs):
    global updating_calculated_inputs
    if updating_calculated_inputs:
        return

    angle_input = _input_by_id(inputs, 'flank_angle')
    depth_input = _input_by_id(inputs, 'thread_depth')
    pitch_input = _input_by_id(inputs, 'pitch')
    is_iso = _is_iso_mode(inputs)
    angle_input.isEnabled = not is_iso
    depth_input.isEnabled = not is_iso
    if not is_iso or pitch_input.value <= 0:
        return

    is_external = True
    face_input = _input_by_id(inputs, 'target_face')
    if face_input and face_input.selectionCount:
        try:
            is_external = analyze_cylinder(face_input.selection(0).entity).is_external
        except ValueError:
            pass

    updating_calculated_inputs = True
    try:
        angle_input.value = ISO_FLANK_ANGLE
        depth_input.value = radial_thread_depth(pitch_input.value, is_external)
    finally:
        updating_calculated_inputs = False


def _validation_errors(parameters):
    errors = parameters.validation_errors()
    if parameters.face is not None:
        try:
            cylinder = analyze_cylinder(parameters.face)
            if not errors:
                thread_section(cylinder, parameters)
            effective_radius = (
                cylinder.radius
                + parameters.tolerance_radius_offset(cylinder.is_external)
            )
            if effective_radius <= 0:
                errors.append(tr('tolerance_large'))
            if parameters.sharp_profile_depth >= effective_radius:
                errors.append(tr('depth_radius'))
        except ValueError as error:
            errors.append(str(error))
    return errors


def _update_result_text(inputs):
    parameters = _read_parameters(inputs)
    errors = _request_errors(inputs, parameters)
    _set_result_text(inputs, errors)
    _update_assistance(inputs)


def _set_result_text(inputs, errors):
    result = _input_by_id(inputs, 'result_text')
    if result is None:
        return
    if errors:
        result.text = '\n'.join(errors)
        return

    cylinder = analyze_cylinder(_read_parameters(inputs).face)
    units = app.activeProduct.unitsManager
    nominal_diameter = units.formatInternalValue(
        cylinder.radius * 2, units.defaultLengthUnits, True
    )
    parameters = _read_parameters(inputs)
    effective_radius = (
        cylinder.radius + parameters.tolerance_radius_offset(cylinder.is_external)
    )
    diameter = units.formatInternalValue(
        effective_radius * 2, units.defaultLengthUnits, True
    )
    core_value = effective_radius * 2 - 2 * parameters.thread_depth
    core_diameter = units.formatInternalValue(
        core_value, units.defaultLengthUnits, True
    )
    pitch_diameter = units.formatInternalValue(
        effective_radius * 2 - parameters.thread_depth,
        units.defaultLengthUnits,
        True,
    )
    pitch_value = units.formatInternalValue(
        parameters.pitch, units.defaultLengthUnits, True
    )
    angle_value = units.formatInternalValue(parameters.flank_angle, 'deg', True)
    mode_text = tr('profile_mode_iso') if _is_iso_mode(inputs) else tr('profile_mode_free')
    selected_tolerance = next(
        name for name, value in TOLERANCE_OPTIONS if value == parameters.tolerance
    )
    thread_type = tr('external_thread') if cylinder.is_external else tr('internal_thread')
    bore_diameter = tr('internal_only') if cylinder.is_external else core_diameter
    section = thread_section(cylinder, parameters)
    def point_text(point):
        return ', '.join(units.formatInternalValue(value, units.defaultLengthUnits, True)
                         for value in (point.x, point.y, point.z))
    section_length = units.formatInternalValue(section.length, units.defaultLengthUnits, True)
    result.text = (
        f'{tr("clearance_distribution")}: {tr("distribution_" + parameters.clearance_distribution)}\n'
        f'{tr("thread_length")}: {section_length}\n'
        f'{tr("section_start")}: {point_text(section.axis_start)}\n'
        f'{tr("section_end")}: {point_text(section.axis_end)}\n'
        f'{tr("thread_direction")}: {tr("left_hand" if parameters.handedness == "left" else "right_hand")}\n'
        f'{thread_type} – {tr("nominal_diameter")}: {nominal_diameter}\n'
        f'{tr("pitch")}: {pitch_value}\n'
        f'{tr("major_diameter")}: {diameter}\n'
        f'{tr("pitch_diameter")}: {pitch_diameter}\n'
        f'{tr("minor_diameter")}: {core_diameter}\n'
        f'{tr("tap_drill")}: {bore_diameter}\n'
        f'{tr("profile_angle")}: {angle_value}\n'
        f'{tr("tolerance")}: {selected_tolerance}\n'
        f'{tr("mode")}: {mode_text}'
    )
    partner = _partner_parameters(inputs, parameters)
    if partner is not None:
        other = analyze_cylinder(partner.face)
        section = thread_section(other, partner)
        def length(value):
            return units.formatInternalValue(value, units.defaultLengthUnits, True)
        result.text += (
            f'\n\n{tr("partner_group")}: {tr("external_thread" if other.is_external else "internal_thread")}'
            f'\n{tr("thread_length")}: {length(section.length)}'
            f'\n{tr("section_start")}: {point_text(section.axis_start)}'
            f'\n{tr("section_end")}: {point_text(section.axis_end)}'
            f'\n{tr("thread_depth")}: {length(partner.thread_depth)}'
            f'\n{tr("major_diameter")}: {length(2 * (other.radius + partner.tolerance_radius_offset(other.is_external)))}'
        )


def _calibration_enabled(inputs):
    return _input_by_id(inputs, 'cal_enabled').value


def _apply_print_profile(profile):
    global TOLERANCE_OPTIONS
    inputs = active_command_inputs
    params = _read_parameters(inputs)
    if params.face is None:
        raise ValueError(tr('face_required'))
    cylinder = analyze_cylinder(params.face)
    if not profile_matches(profile, 2 * cylinder.radius, params.pitch):
        raise ValueError(tr('profile_range'))
    partner = _partner_parameters(inputs, params)
    if partner is not None:
        if partner.face is None:
            raise ValueError(tr('face_required'))
        if not profile_matches(profile, 2 * analyze_cylinder(partner.face).radius, partner.pitch):
            raise ValueError(tr('profile_range'))
    value = profile['tolerance_cm']
    name = next((name for name, gap in TOLERANCE_OPTIONS if abs(gap - value) < 1e-10), None)
    dropdown = _input_by_id(inputs, 'tolerance')
    if name is None:
        name = f'{value * 10:.8g} mm'
        TOLERANCE_OPTIONS += ((name, value),)
    if not any(dropdown.listItems.item(i).name == name for i in range(dropdown.listItems.count)):
        dropdown.listItems.add(name, False)
    _select_dropdown_item(dropdown, name)
    distribution = ('balanced', 'internal', 'external').index(profile['clearance_distribution'])
    _input_by_id(inputs, 'clearance_distribution').listItems.item(distribution).isSelected = True
    _update_result_text(inputs)


def _update_assistance(inputs, draw_preview=False):
    get = lambda key: _input_by_id(inputs, key)
    size_preview.update_size_status(get)
    if not draw_preview:
        return
    parameters = _read_parameters(inputs)
    calibration = _calibration_enabled(inputs)
    errors = [] if calibration else _request_errors(inputs, parameters)
    requests = [parameters]
    if not calibration and not errors:
        partner = _partner_parameters(inputs, parameters)
        if partner is not None:
            requests.append(partner)
    size_preview.update_preview(get, thread_preview, adsk.fusion.Design.cast(app.activeProduct),
                                requests, errors, calibration)


def _record_probe_enabled(inputs):
    return _input_by_id(inputs, 'records_tab').isActive


def _record_rebuild_trial_enabled(inputs):
    return _input_by_id(inputs, 'record_action').selectedItem.index == 2


def _record_apply_edit_enabled(inputs):
    return _input_by_id(inputs, 'record_action').selectedItem.index == 3


def _record_view_only(inputs):
    return _input_by_id(inputs, 'record_action').selectedItem.index == 0


def _record_pair_edit_enabled(inputs):
    return _input_by_id(inputs, 'record_action').selectedItem.index == 4
