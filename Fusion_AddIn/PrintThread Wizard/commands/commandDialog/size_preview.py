"""UI for metric size selection and disposable viewport preview."""
from time import perf_counter
import adsk.core
from ...core.thread_sizes import size_options, diameter_matches
from ...fusion.face_analysis import analyze_cylinder
from ...localization import translate as tr

OPTIONS = size_options()


def add_controls(inputs):
    group = inputs.addGroupCommandInput('size_preview_group', tr('size_help'))
    group.isExpanded = True
    fields = group.children
    size = fields.addDropDownCommandInput('metric_size', tr('metric_size'),
                                        adsk.core.DropDownStyles.TextListDropDownStyle)
    size.tooltip = tr('size_tip')
    size.listItems.add(tr('size_manual'), True)
    for diameter, pitch, kind in OPTIONS:
        size.listItems.add(f'M{diameter * 10:g} × {pitch * 10:g} mm ({tr(kind)})', False)
    fields.addBoolValueInput('apply_metric_size', tr('apply_size'), False, '', False).tooltip = tr('size_tip')
    fields.addTextBoxCommandInput('size_status', '', tr('size_notice'), 4, True)
    fields.addBoolValueInput('light_preview', tr('light_preview'), True, '', False).tooltip = tr('preview_tip')
    fields.addTextBoxCommandInput('preview_status', '', tr('preview_tip'), 4, True)


def selected_size(get):
    index = get('metric_size').selectedItem.index - 1
    return OPTIONS[index] if index >= 0 else None


def update_size_status(get):
    selected = selected_size(get)
    text = [tr('size_notice')]
    if selected is not None:
        diameter, pitch, kind = selected
        for key in ('target_face', 'partner_face'):
            if key == 'partner_face' and not get('pair_mode').value:
                continue
            field = get(key)
            if field.selectionCount:
                try:
                    actual = analyze_cylinder(field.selection(0).entity).radius * 2
                    if not diameter_matches(actual, diameter):
                        text.append(tr('size_mismatch', actual=f'{actual * 10:g}', expected=f'{diameter * 10:g}'))
                except ValueError as error:
                    text.append(str(error))
        if abs(get('pitch').value - pitch) > 1e-9:
            text.append(tr('size_not_applied'))
    get('size_status').text = '\n'.join(text)


def update_preview(get, preview, design, requests, errors, calibration):
    preview.clear()
    if not get('light_preview').value or calibration:
        get('preview_status').text = tr('preview_tip')
        return
    if errors:
        get('preview_status').text = '\n'.join(errors)
        return
    started = perf_counter()
    try:
        preview.update(design, requests)
        adsk.core.Application.get().activeViewport.refresh()
        get('preview_status').text = tr('preview_ready', elapsed=f'{(perf_counter() - started) * 1000:.1f}')
    except Exception as error:
        preview.clear()
        get('preview_status').text = tr('preview_error', error=str(error))
