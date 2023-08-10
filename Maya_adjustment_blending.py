'''
Adjustment Blending is a method for adjusting additive layer interpolation between keyframes, so that movement on the layer is shifted to areas where there is already movement on the base layer.

This helps to maintain the existing energy of the base layer motion, and helps to maintain contact points. For more information, see this talk from GDC 2016: https://youtu.be/eeWBlMJHR14?t=518

MobuCoreLibrary functions are required for this script.
____________________________________________________________________

"This product uses MobuCore (c) 2019 Dan Lowe."

https://github.com/Danlowlows/MobuCore/blob/master/MobuCore/MobuCoreTools/AdjustmentBlend/AdjustmentBlend.py

This is a Maya adaptation of the Adjustment Blending script (by Dan Lowe in MobuCore) written by Armin Tajik.

'''

import maya.cmds as cmds
import maya.OpenMaya as om


def get_key_pairs_from_keys(obj, keys):
    """
    Groups pairs of keys from the keys in an animation curve, between which it will run an independent adjustment blend
    (allows adjustment blend to work with multiple key poses on the layer).
    """
    key_pairs_list = []
    for i in range(len(keys) - 1):
        start_key_time = keys[i]
        start_key_value = cmds.keyframe(obj, q=1, eval=1, time=(start_key_time, start_key_time))
        stop_key_time = keys[i + 1]
        stop_key_value = cmds.keyframe(obj, q=1, eval=1, time=(stop_key_time, stop_key_time))
        key_pairs_list.append([start_key_time, stop_key_time, start_key_value[0], stop_key_value[0]])
    return key_pairs_list


def get_all_layers():
    """Returns all the layers in the scene."""
    layers = []
    root_layer = cmds.animLayer(q=True, r=True)
    if root_layer:
        layers.append(root_layer)
        children = cmds.animLayer(root_layer, q=True, c=True)
        if children:
            for child in children:
                layers.append(child)
    return layers


def evaluate_key_values_for_key_pair_timespan(obj, start_time, stop_time):
    """
    Reads the per frame values from an fcurve (doesn't require keys to be on those frames).
    """
    key_pair_span_values = []
    root_layer = cmds.animLayer(q=True, r=True)
    set_layer_as_preferred(root_layer)
    current = start_time
    while not current > stop_time:
        values = cmds.keyframe(obj, q=1, eval=1, t=(current, current))
        key_pair_span_values.append([current, values[0]])
        current += 0.2
    return key_pair_span_values


def set_layer_as_preferred(layer):
    """
    Sets the given layer as the preferred animation layer.
    """
    layers = get_all_layers()
    for item in layers:
        if item != layer:
            cmds.animLayer(f'{item}', e=1, preferred=0)
        else:
            cmds.animLayer(f'{layer}', e=1, preferred=1)


def get_change_values_frac(span_values):
    """
    Finds the fraction (0-1) of change that occurred on the base layer curve, for the key pair.
    """
    change_values = [0.0]
    total_base_layer_change = []
    for i in range(len(span_values) - 1):
        frame_change_value = abs(span_values[i + 1][1] - span_values[i][1])
        change_values.append(frame_change_value)
    total_base_layer_change = sum(change_values)
    frac_values = []
    for i in range(len(change_values)):
        if total_base_layer_change != 0:
            frac_values.append([span_values[i][0], change_values[i] / total_base_layer_change])
    return frac_values, total_base_layer_change


def adjustment_blend_object(obj):
    """
    The main adjustment blend function that does everything else.
    This is what you'd run if you were just adjustment blending a single object.
    """
    if len(get_all_layers()) > 1:
        pose_layer = get_all_layers()[::-1][0]
        root_layer = cmds.animLayer(q=True, r=True)
        set_layer_as_preferred(root_layer)
        curve_name = cmds.keyframe(obj, q=True, name=1)
        if curve_name:
            set_layer_as_preferred(pose_layer)
            pose_keys = cmds.keyframe(obj, q=1)
            if pose_keys:
                if len(pose_keys) > 1:
                    key_pair_list = get_key_pairs_from_keys(obj, pose_keys)
                    for key_pair in key_pair_list:
                        start_time = key_pair[0]
                        stop_time = key_pair[1]
                        start_value = key_pair[2]
                        stop_value = key_pair[3]
                        cmds.keyTangent(obj, inTangentType='linear', outTangentType='linear', e=1,
                                        time=(start_time, start_time))
                        cmds.keyTangent(obj, inTangentType='linear', outTangentType='linear', e=1,
                                        time=(stop_time, stop_time))
                        span_values = evaluate_key_values_for_key_pair_timespan(obj, start_time, stop_time)
                        set_layer_as_preferred(pose_layer)
                        frac_values, total_base_layer_change = get_change_values_frac(span_values)
                        total_pose_layer_change = abs(stop_value - start_value)
                        previous_value = start_value
                        for index, value in enumerate(frac_values):
                            current_t = value[0]
                            value_delta = (total_pose_layer_change) * value[1]
                            base_value = span_values[index][1]
                            if stop_value > start_value:
                                current_value = previous_value + value_delta
                            else:
                                current_value = previous_value - value_delta
                            cmds.setKeyframe(obj, animLayer=pose_layer, value=current_value + base_value,
                                             t=(current_t, current_t))
                            previous_value = current_value


def adjustment_blend_character(character=None):
    """
    The main adjustment blending function for running it on an entire character.
    """
    if not character:
        character = cmds.ls(type='character')[0]
    if character:
        character_objs = cmds.character(f'{character}', query=True)
        if character_objs:
            if len(get_all_layers()) > 1:
                for obj in character_objs:
                    if obj:
                        adjustment_blend_object(obj)
        else:
            om.MGlobal.displayWarning("No additive layer found. Adjustment blending affects interpolation between keys on the topmost additive layer.")
    else:
        om.MGlobal.displayWarning("No additive layer found. Adjustment blending affects interpolation between keys on the topmost additive layer.")


if __name__ == "__main__":
    adjustment_blend_character('character1')