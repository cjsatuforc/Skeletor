#Author-Mike Fogel
#Description-

import adsk.core, adsk.fusion, traceback

defaultBoneDiameter = '1mm'

newBodyOp = 'New Bod(y/ies)'
newCompOp = 'New Component'

# global set of event handlers to keep them referenced for the duration of the command
handlers = []
app = adsk.core.Application.get()
if app:
    ui = app.userInterface

product = app.activeProduct
design = adsk.fusion.Design.cast(product)


def createNewComponent(name):
    # Get the active design.
    rootComp = design.rootComponent
    allOccs = rootComp.occurrences
    component = allOccs.addNewComponent(adsk.core.Matrix3D.create()).component
    component.name = name
    return component


def createSkeleton(targetBody, boneDiameter, parentComponent):

    planes = parentComponent.constructionPlanes
    sketches = parentComponent.sketches
    sweeps = parentComponent.features.sweepFeatures
    revolves = parentComponent.features.revolveFeatures

    positivePoint = adsk.core.Point3D.create(boneDiameter/2, 0, 0)
    negativePoint = adsk.core.Point3D.create(-boneDiameter/2, 0, 0)
    startMiddlePoint = adsk.core.Point3D.create(0, boneDiameter/2, 0)
    endMiddlePoint = adsk.core.Point3D.create(0, -boneDiameter/2, 0)

    for edge in targetBody.edges:
        planeInput = planes.createInput()
        planeInput.setByDistanceOnPath(edge, adsk.core.ValueInput.createByReal(0))
        plane = planes.add(planeInput)

        sketch = sketches.add(plane)
        sketch.sketchCurves.sketchArcs.addByThreePoints(positivePoint, startMiddlePoint, negativePoint)
        line = sketch.sketchCurves.sketchLines.addByTwoPoints(negativePoint, positivePoint)
        path = adsk.fusion.Path.create(edge, adsk.fusion.ChainedCurveOptions.noChainedCurves)
        profile = sketch.profiles.item(0)

        sweepInput = sweeps.createInput(profile, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        sweeps.add(sweepInput)

        revolveInput = revolves.createInput(profile, line, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        revolveInput.setAngleExtent(False, adsk.core.ValueInput.createByString('-180deg'))
        revolves.add(revolveInput)

        planeInput = planes.createInput()
        planeInput.setByDistanceOnPath(edge, adsk.core.ValueInput.createByReal(1))
        plane = planes.add(planeInput)

        sketch = sketches.add(plane)
        sketch.sketchCurves.sketchArcs.addByThreePoints(positivePoint, endMiddlePoint, negativePoint)
        line = sketch.sketchCurves.sketchLines.addByTwoPoints(negativePoint, positivePoint)
        path = adsk.fusion.Path.create(edge, adsk.fusion.ChainedCurveOptions.noChainedCurves)
        profile = sketch.profiles.item(0)

        sweepInput = sweeps.createInput(profile, path, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        sweeps.add(sweepInput)

        revolveInput = revolves.createInput(profile, line, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        revolveInput.setAngleExtent(False, adsk.core.ValueInput.createByString('180deg'))
        revolves.add(revolveInput)


class SkeletorizeCommandExecuteHandler(adsk.core.CommandEventHandler):

    def notify(self, args):
        try:
            unitsMgr = app.activeProduct.unitsManager
            command = args.firingEvent.sender
            inputs = command.commandInputs

            if inputs.count != 2:
                raise ValueError('Unexpected number of inputs: {}'.format(inputs.count))

            for input in inputs:
                if input.id == 'body':
                    targetBody = input.selection(0).entity
                elif input.id == 'boneDiameter':
                    boneDiameter = unitsMgr.evaluateExpression(input.expression, "mm")
                else:
                    raise ValueError('Unexpected input iud: {}'.format(input.id))

            # ensure our target has edges and such (ex: a sphere doesn't)
            if targetBody.edges.count == 0:
                raise ValueError('Target Body has no edges')

            # do the real work
            parentComponent = createNewComponent(targetBody.name + ' Skeleton')
            createSkeleton(targetBody, boneDiameter, parentComponent)
            adsk.terminate()

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class SkeletorizeCommandDestroyHandler(adsk.core.CommandEventHandler):

    def notify(self, args):
        try:
            # when the command is done, terminate the script
            # this will release all globals which will remove all event handlers
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class SkeletorizeCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):

    def notify(self, args):
        try:
            cmd = args.command
            cmd.isRepeatable = False
            onExecute = SkeletorizeCommandExecuteHandler()
            cmd.execute.add(onExecute)
            onDestroy = SkeletorizeCommandDestroyHandler()
            cmd.destroy.add(onDestroy)

            # keep the handlers referenced beyond this function
            handlers.append(onExecute)
            handlers.append(onDestroy)

            #define the inputs
            inputs = cmd.commandInputs

            bodyInput = inputs.addSelectionInput('body', 'Body', 'Please select a Body to skeletorize')
            bodyInput.addSelectionFilter(adsk.core.SelectionCommandInput.Bodies);
            bodyInput.setSelectionLimits(1, 1)

            initBoneDiameter = adsk.core.ValueInput.createByString(defaultBoneDiameter)
            inputs.addValueInput('boneDiameter', 'Bone Diameter', 'mm', initBoneDiameter)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):

    try:
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        if not design:
            ui.messageBox('It is not supported in current workspace, please change to MODEL workspace and try again.')
            return
        commandDefinitions = ui.commandDefinitions
        #check the command exists or not
        cmdDef = commandDefinitions.itemById('Skeletorize')
        if not cmdDef:
            cmdDef = commandDefinitions.addButtonDefinition('Skeletorize',
                                                            'Skeletorize a body',
                                                            'Skeletorize a body.')

        onCommandCreated = SkeletorizeCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        # keep the handler referenced beyond this function
        handlers.append(onCommandCreated)
        inputs = adsk.core.NamedValues.create()
        cmdDef.execute(inputs)

        # prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))