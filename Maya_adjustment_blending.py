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

# Groups pairs of keys from the keys in an animation curve, between which it will run an independent adjustment blend (allows adjustment blend to work with multiple key poses on the layer).
def GetKeyPairsFromKeys(obj, keys):
    keyPairsList = []
    for i in range(len(keys)-1):
        startKeyTime = keys[i]
        startKeyValue = cmds.keyframe(obj, q=1, eval=1, time=(startKeyTime,startKeyTime))
        stopKeyTime = keys[i+1]
        stopKeyValue = cmds.keyframe(obj, q=1, eval=1, time=(stopKeyTime,stopKeyTime))
        keyPairsList.append([startKeyTime, stopKeyTime, startKeyValue[0], stopKeyValue[0]])
    return keyPairsList
    
# Returns all the layers in the scene
def GetAllLayers():
    layers = []
    rootLayer = cmds.animLayer(q=True, r=True)
    if rootLayer:
        layers.append(rootLayer)
        children = cmds.animLayer(rootLayer, q=True, c=True)
        if children:
            for child in children:
                layers.append(child)
    return layers

# Reads the per frame values from an fcurve (doesn't require keys to be on those frames).
def EvaluateKeyValuesForKeyPairTimespan(obj, startTime, stopTime):
    keyPairSpanValues = []
    rootLayer = cmds.animLayer(q=True, r=True)
    SetLayerAsPreferred(rootLayer)
    current = startTime
    while not current > stopTime:
        values = cmds.keyframe(obj, q=1, eval = 1, t=(current, current))
        keyPairSpanValues.append([current, values[0]])
        current += .2
    return keyPairSpanValues

# Reads the per frame values from an fcurve (doesn't require keys to be on those frames).
def SetLayerAsPreferred(layer):
    layers = GetAllLayers()
    for item in layers:
        if item != layer:
            cmds.animLayer(f'{item}', e=1, preferred =0)
        else:
            cmds.animLayer(f'{layer}', e=1, preferred =1)
            
# Finds the frac (0-1) of change that occured on the base layer curve, for the key pair.
def GetChangeValuesFrac(spanValues):
    changeValues = [0.0]
    totalBaseLayerChange = []
    for i in range(len(spanValues)-1):   
        frameChangeValue = abs(spanValues[i+1][1] - spanValues[i][1])
        changeValues.append(frameChangeValue)
    totalBaseLayerChange = sum(changeValues)
    fracValues = []
    for i in range(len(changeValues)):
        if totalBaseLayerChange != 0:
            fracValues.append([spanValues[i][0],  changeValues[i]/(totalBaseLayerChange)])
    return fracValues, totalBaseLayerChange


# The main adjustment blend function that does everything else. This is what you'd run if you were just adjustment blending a single object.
def AdjustmentBlendObject(obj):
    if len(GetAllLayers()) > 1:
        poseLayer = GetAllLayers()[::-1][0]
        rootLayer = cmds.animLayer(q=True, r=True)
        SetLayerAsPreferred(rootLayer)
        curveName = cmds.keyframe(obj,q=True, name=1)
        if curveName:
            SetLayerAsPreferred(poseLayer)
            poseKeys = cmds.keyframe(obj, q=1)
            if poseKeys:
                if len(poseKeys)>1:
                    keyPairList = GetKeyPairsFromKeys(obj, poseKeys)
                    for keyPair in keyPairList:
                        startTime = keyPair[0]
                        stopTime = keyPair[1]
                        startValue = keyPair[2]
                        stopValue = keyPair[3]
                        cmds.keyTangent( obj, inTangentType='linear',outTangentType='linear', e=1, time=(startTime,startTime) )
                        cmds.keyTangent( obj, inTangentType='linear',outTangentType='linear', e=1, time=(stopTime,stopTime) )
                        spanValues = EvaluateKeyValuesForKeyPairTimespan(obj, startTime, stopTime)
                        SetLayerAsPreferred(poseLayer)
                        fracValues , totalBaseLayerChange = GetChangeValuesFrac(spanValues)
                        totalPoseLayerChange = abs(stopValue - startValue)
                        previousValue = startValue
                        for index, value in enumerate(fracValues):
                            currentT = value[0]
                            valueDelta = (totalPoseLayerChange) * value[1]
                            baseValue = spanValues[index][1]
                            if stopValue > startValue:
                                currentValue = previousValue + valueDelta
                            else:
                                currentValue = previousValue - valueDelta
                            cmds.setKeyframe(obj ,animLayer = poseLayer,  value=currentValue+baseValue, t=(currentT, currentT))
                            previousValue = currentValue
                        
# The main adjustment blending function for running it on an entire character.
def AdjustmentBlendCharacter(character = None):
    if not character:
        character = cmds.ls( type='character')[0]
    if character:
        characterObjs = cmds.character(f'{character}', query=True)
        if characterObjs:
            if len(GetAllLayers()) > 1:
                for obj in characterObjs:
                    if obj:
                        AdjustmentBlendObject(obj)  
        else:
            om.MGlobal.displayWarning("No additive layer found. Adjustment blending affects interpolation between keys on the the top most additive layer.")
    else:
        om.MGlobal.displayWarning("Nsadasdo additive layer found. Adjustment blending affects interpolation between keys on the the top most additive layer.")
              
if __name__ == "__main__":
    AdjustmentBlendCharacter('character1')