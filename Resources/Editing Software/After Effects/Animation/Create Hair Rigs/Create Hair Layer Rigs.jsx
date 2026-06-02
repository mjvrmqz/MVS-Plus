/* 
        Title:  AFP Hair Rig
        By:     Anthony Possobon - anthonypossobon@gmail.com
        Date:   Mar 13, 2020
        This script is a fast and easy way to create a simple hair rig for AE character animation.
*/

{
    

    var numLayers;
    var scriptFileName  = "AFPHairRig";
    var scriptTitle     = "/////AFPHairRig//////";
    var scriptVersion   = 'v03.51';


    ///////////////////
    //CLASS INCLUDES
    ///////////////////
    var thisScriptFile = new File($.fileName);
    var includePath = "";
    var foundIncludeClass = false;

    if(thisScriptFile.name.toString() == scriptFileName+".jsx" || thisScriptFile.name.toString() == scriptFileName+".jsxbin")
    {
        includePath = "../uti/jsx";
    }else
    {
        includePath = thisScriptFile.parent.toString();
        
    }

    var classes = new File(String(includePath+"/AFPStyle.jsx"));
    var AFPStyle;

    if(classes.exists)
    {
        foundIncludeClass = true;
        eval("#include "+String(includePath+"/AFPStyle.jsx"));

        AFPStyle                    = new AFPStyle();
    }else
    {
        AFPStyle = {textAccentColor: [1,1,1]}
    }

    ///////////////////
    //SCRIPT VARS
    ///////////////////
    app.beginUndoGroup("AFPHairRig");

    var proj            = app.project;
    var prMessage       = "Null size";
    var nullSize        = 100;
    var myComp          = proj.activeItem;
    var layersSelec     = myComp.selectedLayers;
    var layerArr        = [];
    var nname           = "Hair";
    var nameBol         = false;
    var buildNulls      = false;
    var pStack          = 1;

    //style
    var textColor               = AFPStyle.textAccentColor; //pink

    init();
    function init()
    {

        checkBeforeRun();
    };

    //check the proj before running script to make sure no errors occure
    function checkBeforeRun()
    {
        if(!proj || proj.numItems == 0 || !myComp || layersSelec[0] == null)
        {
            //Can't run script because of reasons in below alert
            alert("You need a project, a selected comp, a selected layer, and select PuppetPins to use the AFPHairRig.");
        }else
        {
            //All is a go! Check names of layers to see if a rename is in order
            checkLayerNames();

            buildUI(this);
            
        };
    };

    function buildUI(thisObj)
    {
        if (thisObj instanceof Panel)
        {
            var myPal = thisObj;
        }else
        {
            var myPal = new Window("dialog",scriptTitle+" "+scriptVersion,undefined,{resizeable:false});
        };
        if(myPal != null)
        {
            panalUI(myPal);
        };

        return myPal;
    };

    function panalUI(myPalette)
    {
        AFPHairRigWindow = myPalette;
        
        var myGroup = myPalette.add("Group");


        var titleGroup =  myGroup.add("Group");
        titleGroup.add("statictext", [0,0,260,20], "PARAMETERS");
        titleGroup.alignment = 'left';
        titleGroup.graphics.font = ScriptUI.newFont("Arial", 'ITALIC', 14);
        //titleGroup.graphics.foregroundColor = titleGroup.graphics.newPen (titleGroup.graphics.PenType.SOLID_COLOR, [1, 1, 1], 1);

        qBTN = titleGroup.add("button", [0,0,20,20], "?");
        qBTN.alignment = 'right';
        qBTN.helpTip = "About";
        qBTN.onClick = function()
        {
            var myQPal = new Window("dialog","About",undefined,{resizeable:false});
            panaQUI(myQPal);

        };

        var myPanel = myGroup.add("panel", undefined, "BONES");
        myPanel.graphics.foregroundColor = myPanel.graphics.newPen (myPanel.graphics.PenType.SOLID_COLOR, textColor, 1);
        myGroup.orientation = "column";
        
        var radTGroup = myPanel.add("Group");
        radTGroup.add("statictext", [0,0,250,20], "Which do you want to apply to?");
        radTGroup.margins = [0, 0, 0, 0];
        radTGroup.spacing = [0, 0, 0, 0];

        var radGroup = myPanel.add("Group");
        var radio1 = radGroup.add ("radiobutton", undefined, "PuppetPins");
        var radio2 = radGroup.add ("radiobutton", undefined, "New Nulls");
        radio1.value = true;
        radio1.onClick = function()
        {
            nullGroup.enabled = false;
        };
        radio2.onClick = function()
        {
            nullGroup.enabled = true;
        };

        var nullGroup = myPanel.add("Group");
        nullGroup.margins = [0, 0, 0, 0];
        nullGroup.spacing = [0, 0, 0, 0];
        nullGroup.add("statictext", undefined, prMessage);
        nullGroup.alignment = 'right';
        var notesTxt = nullGroup.add("edittext", [0, 0, 30, 20], nullSize);
        nullGroup.enabled = false;

        var myRPanel = myGroup.add("panel", undefined, "RENAME LAYERS");
        myRPanel.graphics.foregroundColor = myRPanel.graphics.newPen (myRPanel.graphics.PenType.SOLID_COLOR, textColor, 1);
        myRPanel.orientation = "column";

        var reGroup =  myRPanel.add("Group");
        /*reGroup.add("statictext", [0,0,220,20], "RENAME LAYERS");
        reGroup.alignment = 'left';
        reGroup.graphics.font = ScriptUI.newFont("Arial", 'BOLD', 11);
        reGroup.graphics.foregroundColor = titleGroup.graphics.newPen (titleGroup.graphics.PenType.SOLID_COLOR, [1, 1, 1], 1);*/

        if(nameBol)
        {
            var renameGroupT = myRPanel.add("Group");
            var newNameMessage = renameGroupT.add("statictext", undefined, "You have one or more layers with the same name.");
            var renameGroupR = myRPanel.add("Group");
            var newNameMessageC = renameGroupR.add("statictext", undefined, "Running this will change your layer names.");
        };
        var renameGroup = myRPanel.add("Group");
        renameGroup.margins = [0, 0, 0, 0];
        renameGroup.spacing = [0, 0, 0, 0];
        
        var check1 = renameGroup.add ("checkbox", undefined, "Rename layers");
        var newName = renameGroup.add("edittext", [0,0,90,20], nname); 

        check1.value = nameBol;
        check1.enabled = true;
        newName.enabled = nameBol;
        newName.onActivate = updateText(newName, true);
        newName.onDeactivate = updateText(newName, false);
        newName.onChanging = function()
        {
            nname = newName.text;
        };

        check1.onClick = function()
        {
            if(nameBol)
            {
                check1.value = true;
            }else
            {
                if(check1.value)
                {
                    newName.enabled = true;
                    newName.active = true;
                }else
                {
                    newName.enabled = false;
                };
                updateText(newName, false);
            };
        };

        var confGroup =  myGroup.add("Group");
        confGroup.margins = [0, 0, 0, 0];
        confGroup.spacing = [0, 0, 0, 0];
        runBTN = confGroup.add("button", [0,0,283,40], "RUN");
        runBTN.alignment = 'right';
        runBTN.helpTip = "Run script";
        runBTN.enabled = true;
        //runBTN.graphics.font = ScriptUI.newFont("Arial", 'BOLD', 15);
        //runBTN.graphics.foregroundColor = runBTN.graphics.newPen (runBTN.graphics.PenType.SOLID_COLOR, [1, 1, 1], 1);
        runBTN.onClick = function ()
        {
            runBTN.enabled = false;
            nullSize = notesTxt.text;
            buildNulls = radio2.value;
            if(check1.value)
            {
                renameLayers();
            }

            //builds out the controllers needed for the tool
            buildHairGlobal();

            //collects all the PuppetPins that will be used for the tool
            findPuppetPins();

            myPalette.close();
        };

        myPalette.show();
    };

    function checkLayerNames()
    {
        var sameName = false;

        //runs through all selected layers to see if anything has the same name
        for (var l = 0; l < app.project.activeItem.selectedLayers.length; l++) 
        {
            for (var t = 0; t < app.project.activeItem.selectedLayers.length; t++) 
            {
                var testLayer = app.project.activeItem.selectedLayers[l];
                var layer = app.project.activeItem.selectedLayers[t];
                if(l != t && testLayer.name == layer.name)
                {
                    sameName = true;
                };
            };
        };
        if(sameName == true)
        {
            //if layers have the same name, it runs renameLayer function
            nameBol = true;
        };
    };

    function updateText(t, b)
    {
        if(t.text == "Hair" && b == true)
        {
            t.text = "";
        }
        if(t.text == "" && b == false)
        {
            t.text = "Hair"
        };
    };

    function renameLayers()
    {
        for (var t = 0; t < app.project.activeItem.selectedLayers.length; t++) 
        {
            var layer = app.project.activeItem.selectedLayers[t];
            layer.name = nname+"_"+layer.index;
        };
    };

    function findPuppetPins()
    {
        for (var l = 0; l < app.project.activeItem.selectedLayers.length; l++) 
        {
           layerArr.push(app.project.activeItem.selectedLayers[l]);
        };

        buildHairNull();

        for (var i = 0; i < layerArr.length; i++) 
        {
            var hasPuppet = false;
            var selectedLayer = layerArr[i];

            if(selectedLayer.property("Effects").property("Puppet"))
            {
                var pinArr = [];
                hasPuppet = true;
                var pinProperty = selectedLayer.property("Effects").property("Puppet").property("arap").property("Mesh").property(1).property("Deform");

                for (var p = 0; p < pinProperty.numProperties; p++) 
                {
                    var pin = pinProperty.property(p+1);

                    if(pin.property("Position").numKeys > 0)
                    {
                        pinArr.push(pin.name);
                    };
                };
                runHairRig(selectedLayer, selectedLayer.property("Effects").property("Puppet"), selectedLayer.property("Effects").property("Puppet").property("arap").property("Mesh").property(1), pinArr);
            };
        };
    };
    function panaQUI(myPal)
    {
        var myG = myPal.add("Group");
        var myP = myG.add("panel", undefined, "");

        var vGroup =  myP.add("Group");
        //vGroup.orientation = "column";
        vGroup.alignment = 'left';

        //vGroup.add("statictext", undefined, aboutTxt());
        var v = vGroup.add("statictext", [0,0,70,20], "Version "+scriptVersion);
        v.alignment = 'left';

        nBTN = vGroup.add("button", [0,0,70,20], "Notes");
        nBTN.alignment = 'right';
        nBTN.helpTip = "Run script";
        nBTN.onClick = function()
        {
            var w = new Window("dialog");
            var g = w.add("group");
            //var panel = g.add("panel", [0,0,300,200]);
            var n = w.add('edittext {preferredSize: [450, 300], properties: {multiline: true}}');
            n.text = notesTxtUpdate();
            w.show();
        };

        var hGroup =  myP.add("Group");
        //vGroup.orientation = "column";
        hGroup.alignment = 'left';

        //vGroup.add("statictext", undefined, aboutTxt());
        var c = hGroup.add("statictext", [0,0,70,20], "Controller");
        c.alignment = 'left';

        cBTN = hGroup.add("button", [0,0,70,20], "Breakdown");
        cBTN.alignment = 'right';
        cBTN.helpTip = "Run script";
        cBTN.onClick = function()
        {
            var w = new Window("dialog");
            var g = w.add("group");
            //var panel = g.add("panel", [0,0,300,200]);
            var n = w.add('edittext {preferredSize: [450, 300], properties: {multiline: true}}');
            n.text = controllerTxtUpdate();
            w.show();
        };

        var aGroup =  myP.add("Group");
        aGroup.orientation = "column";
        aGroup.alignment = 'left';

        var s = aGroup.add("statictext", undefined, "Script by Anthony Possobon");
        s.alignment = 'left';
        s.graphics.foregroundColor = s.graphics.newPen (s.graphics.PenType.SOLID_COLOR, textColor, 1);
        var e = aGroup.add("statictext", undefined, "anthonypossobon@gmail.com");
        e.alignment = 'left';
        myPal.show();
    };
    
    function runHairRig(myLayer, myPuppet, myMesh, myPins)
    {
        var valueArr = myPins;
        var puppetName = myPuppet.name;
        var meshName = myMesh.name;
        var layerName = myLayer.name;

        pStack = 1;

        Amp = buildEffect(myLayer, "Amp", "ADBE Slider Control");
        Amp.slider.setValue(5);
        Amp.slider.expression = buildAFPExp(ampExp(""));
        Amp.moveTo(propStack());

        Freq = buildEffect(myLayer, "Freq", "ADBE Slider Control");
        Freq.slider.setValue(1);
        Freq.slider.expression = buildAFPExp(freqExp(""));
        Freq.moveTo(propStack());

        loops = buildEffect(myLayer, "Animation Loops Every(sec)", "ADBE Slider Control");
        loops.slider.setValue(1);
        loops.slider.expression = buildAFPExp(loopsExp(""));
        loops.moveTo(propStack());

        Delay = buildEffect(myLayer, "Delay", "ADBE Slider Control");
        Delay.slider.setValue(1);
        Delay.slider.expression = buildAFPExp(delayExp(""));
        Delay.moveTo(propStack());

        layerIndex = buildEffect(myLayer, "layerIndex", "ADBE Slider Control");
        layerIndex.slider.setValue(0);
        layerIndex.slider.expression = layerIndexExp();
        layerIndex.moveTo(propStack());

        windOrderPosition = buildEffect(myLayer, "WindOrderPosition", "ADBE Point Control");
        windOrderPosition.point.setValue([0,0]);
        /*windOrderPosition = myLayer.Effects.addProperty("ADBE Point Control");
        windOrderPosition.name = "windOrderPosition";
        windOrderPosition.point.setValue([50,50]);*/
        windOrderPosition.point.expression = "thisLayer.toWorld(thisLayer.anchorPoint);";
        windOrderPosition.point.setValue(windOrderPosition.point.value);
        windOrderPosition.point.expression = "";
        windOrderPosition.moveTo(propStack());

        RandomSeed = buildEffect(myLayer, "RandomSeed", "ADBE Slider Control");
        RandomSeed.slider.setValue(Math.random());
        RandomSeed.moveTo(propStack());
        
        FallOff = buildEffect(myLayer, "FallOff", "ADBE Slider Control");
        for (var i = 0; i < valueArr.length; i++) 
        {
            var num = (i/(valueArr.length-1));
            var valTime = ((num/1)*.8)+.2;
            FallOff.slider.setValueAtTime(num, valTime);

        };
       /* FallOff.slider.setValueAtTime(0, .2);
        FallOff.slider.setValueAtTime(1, 1);*/
        FallOff.moveTo(propStack());

        Offset = buildEffect(myLayer, "Offset", "ADBE Slider Control");
        Offset.slider.setValue(0);
        Offset.slider.expression =  buildAFPExp(offsetExp(""));
        Offset.moveTo(propStack());

        PhaseLocator = buildEffect(myLayer, "PhaseLocator", "ADBE Slider Control");
        PhaseLocator.slider.setValue(0);
        PhaseLocator.slider.expression = buildAFPExp(phaseLocatorExp(""));
        PhaseLocator.moveTo(propStack());

        WaveMath = buildEffect(myLayer, "WaveMath", "ADBE Angle Control");
        WaveMath.angle.setValue(0);
        WaveMath.angle.expression = buildAFPExp(waveMathExp(""));
        WaveMath.moveTo(propStack());

        SubFreq = buildEffect(myLayer, "SubFreq", "ADBE Slider Control");
        SubFreq.slider.setValue(1);
        SubFreq.slider.expression = buildAFPExp(freqExp("Sub"));
        SubFreq.moveTo(propStack());

        SubAmp = buildEffect(myLayer, "SubAmp", "ADBE Slider Control");
        SubAmp.slider.setValue(0);
        SubAmp.slider.expression =  buildAFPExp(ampExp("Sub"));
        SubAmp.moveTo(propStack());

        SubDelay = buildEffect(myLayer, "SubDelay", "ADBE Slider Control");
        SubDelay.slider.setValue(1);
        SubDelay.slider.expression = buildAFPExp(delayExp("Sub"));
        SubDelay.moveTo(propStack());

        SubWaveDirection = buildEffect(myLayer, "SubWaveDirection", "ADBE Angle Control");
        SubWaveDirection.angle.setValue(0);
        SubWaveDirection.moveTo(propStack());

        SubFallOff = buildEffect(myLayer, "SubFallOff", "ADBE Slider Control");
        /*SubFallOff.slider.setValueAtTime(0, 0);
        SubFallOff.slider.setValueAtTime(1, 1);*/
        for (var s = 0; s < valueArr.length; s++) 
        {
            var num = (s/(valueArr.length-1));
            var valTime = ((num/1));
            SubFallOff.slider.setValueAtTime(num, valTime);
        };
        SubFallOff.moveTo(propStack());

        SubOffset = buildEffect(myLayer, "SubOffset", "ADBE Slider Control");
        SubOffset.slider.setValue(0);
        SubOffset.slider.expression = buildAFPExp(offsetExp("Sub"));
        SubOffset.moveTo(propStack());

        SubPhaseLocator = buildEffect(myLayer, "SubPhaseLocator", "ADBE Slider Control");
        SubPhaseLocator.slider.setValue(0);
        SubPhaseLocator.slider.expression = buildAFPExp(phaseLocatorExp("Sub"));
        SubPhaseLocator.moveTo(propStack());
        
        SubWaveMath = buildEffect(myLayer, "SubWaveMath", "ADBE Angle Control");
        SubWaveMath.angle.setValue(0);
        SubWaveMath.angle.expression =  buildAFPExp(waveMathExp("Sub"));
        SubWaveMath.moveTo(propStack());



        if(buildNulls)
        {
            var layerParent = null;
            var arrNull = [];
            
            for(var i= 0; i<valueArr.length ; i++)
            {
                /***************************null bone structure***************************/
                var numOff = i+1;
                var backWards = valueArr.length-i-1;
                var newNull = app.project.activeItem.layers.addNull();
                newNull.name = myLayer.name+"-"+numOff+"_HR_Bone";
                newNull.label = myLayer.label;
                newNull.anchorPoint.setValue([50,50]);
                newNull.position.expression =  buildAFPExp("thisComp.layer('" + layerName + "').toWorld(thisComp.layer('" + layerName + "').effect('" + puppetName + "').arap.mesh('" + meshName + "').deform('" + valueArr[backWards] + "').position)");
                newNull.position.setValue(newNull.position.value);
                newNull.position.expression = "";
                newNull.scale.setValue([nullSize,nullSize]);

                var SubPoint = newNull.Effects.addProperty("ADBE Point Control");
                SubPoint.name = "SubPoint";
                SubPoint.point.setValue([50,50]);
                SubPoint.point.expression = buildAFPExp(subPointExp(numOff, myLayer.name, valueArr.length, "value[0]", "value[1]"));
                
                if(layerParent != null)
                {
                    newNull.parent = layerParent;
                };
                layerParent = newNull;
                arrNull.push(newNull);
                
                //adding expressions to puppet pins  
                app.project.activeItem.layer(layerName).effect(puppetName).arap.mesh(meshName).deform(valueArr[backWards]).position.expression =    buildAFPExp("bonePos = thisComp.layer('"+newNull.name+"').toWorld(thisComp.layer('"+newNull.name+"').effect('SubPoint')('Point'));\n"+
                                                                                                                                                    "fromWorld(bonePos);");
            };

            for(var t= 0; t<arrNull.length ; t++)
            {
                var numOffset = t+1;

                arrNull[t].rotation.expression = buildAFPExp(angleExp(numOffset, myLayer.name, valueArr.length, false));
            };
        }else
        {   
            /***************************puppet pin bone structure***************************/
            for(var i= 0; i<valueArr.length ; i++)
            {
                var numOffset = i+1;

                pointRot = buildEffect(myLayer, "pin"+numOffset+"Rot", "ADBE Angle Control");
                pointRot.angle.setValue(0);
                pointRot.angle.expression = buildAFPExp(angleExp(numOffset, myLayer.name, valueArr.length, true));
                pointRot.moveTo(propStack());
            };
            for(var t= 0; t<valueArr.length ; t++)
            {
                var numOffset   = t+1;
                var backWards   = valueArr.length-t-1;
                var pinPos      = buildEffect(myLayer, "pin"+numOffset+"Pos", "ADBE Point Control");
                var pin         = app.project.activeItem.layer(layerName).effect(puppetName).arap.mesh(meshName).deform(valueArr[backWards]);
                pinPos.point.setValue(pin.position.keyValue(1));
                pin.position.expression = buildAFPExp(pinBonesExp(numOffset, valueArr.length));
                pinPos.moveTo(propStack());
            };
        };
    };
    function buildEffect(l, n, contType)
    {
        if(l.Effects.property(n) == null)
        {
            //alert("doesn't exist");
            obj = l.Effects.addProperty(contType);
            obj.name = n;
        }else
        {
            //alert("exists");
            obj = l.Effects.property(n);
        };
        return obj;
    };
    function propStack()
    {
        pStack++;
        return pStack;
    };
    function buildHairGlobal()
    {

        var buildComp = true;
        for (var i = 1; i < proj.items.length; i++) 
        {
            if(proj.items[i].name == "GLOBAL_HR_controller")
            {
                buildComp = false;
            };
        };
        if(buildComp == true)
        {
            var globalComp = proj.items.addComp("GLOBAL_HR_controller", 500, 500, 1, 15, app.project.activeItem.frameRate);

            var n = globalComp.layers.addNull();
            n.name = "GLOBAL_HR_controller";
            n.anchorPoint.setValue([50,50]);
            n.position.setValue([-50,50])

            var globalOffsetSpacing = n.Effects.addProperty("ADBE Slider Control");
            globalOffsetSpacing.name = "globalOffsetSpacing";
            globalOffsetSpacing.slider.setValue(1);

            var globalSubOffsetSpacing = n.Effects.addProperty("ADBE Slider Control");
            globalSubOffsetSpacing.name = "globalSubOffsetSpacing";
            globalSubOffsetSpacing.slider.setValue(1);
            
            var globalAmp = n.Effects.addProperty("ADBE Slider Control");
            globalAmp.name = "globalAmp";
            globalAmp.slider.setValue(1);

            var globalFreq = n.Effects.addProperty("ADBE Slider Control");
            globalFreq.name = "globalFreq";
            globalFreq.slider.setValue(1);

            var globalDelay = n.Effects.addProperty("ADBE Slider Control");
            globalDelay.name = "globalDelay";
            globalDelay.slider.setValue(1);

            var globalFallOff = n.Effects.addProperty("ADBE Slider Control");
            globalFallOff.name = "globalFallOff";
            globalFallOff.slider.setValueAtTime(0, 1);
            globalFallOff.slider.setValueAtTime(1, 1);
            
            var globalSubValue = n.Effects.addProperty("ADBE Slider Control");
            globalSubValue.name = "globalSubValue";
            globalSubValue.slider.setValue(0);

            var globalSubAmp = n.Effects.addProperty("ADBE Slider Control");
            globalSubAmp.name = "globalSubAmp";
            globalSubAmp.slider.setValue(1);

            var globalSubFreq = n.Effects.addProperty("ADBE Slider Control");
            globalSubFreq.name = "globalSubFreq";
            globalSubFreq.slider.setValue(1);

            var globalSubDelay = n.Effects.addProperty("ADBE Slider Control");
            globalSubDelay.name = "globalSubDelay";
            globalSubDelay.slider.setValue(1);

            var globalSubWaveDirection = n.Effects.addProperty("ADBE Angle Control");
            globalSubWaveDirection.name = "globalSubWaveDirection";

            var globalSubFallOff = n.Effects.addProperty("ADBE Slider Control");
            globalSubFallOff.name = "globalSubFallOff";
            globalSubFallOff.slider.setValueAtTime(0, 1);
            globalSubFallOff.slider.setValueAtTime(1, 1);
        };
    };

    function buildHairNull()
    {
        var l = app.project.activeItem.layers;
        var makeNull = false;

        for(var i= 1; i<l.length ; i++)
        {
            if(l[i].name == "MASTER_HR_controller")
            {
                makeNull = true;
            };
        };
        if(!makeNull)
        {
            var n = app.project.activeItem.layers.addNull();
            n.name = "MASTER_HR_controller";
            n.anchorPoint.setValue([50,50]);
            n.position.setValue([50,50])
            n.label = 11;

            var onOff = n.Effects.addProperty("ADBE Checkbox Control");
            onOff.name = "TurnOffHairRig";

            var acDc = n.Effects.addProperty("ADBE Checkbox Control");
            acDc.name = "Ascending > Descending";

            var useWindStartPoint = n.Effects.addProperty("ADBE Checkbox Control");
            useWindStartPoint.name = "Use windStartPoint";
            //acDc.layer.setValue();
            var windStartPoint = n.Effects.addProperty("ADBE Point Control");
            windStartPoint.name = "windStartPoint";
            windStartPoint.point.setValue([0,0]);

            var masterOffset = n.Effects.addProperty("ADBE Slider Control");
            masterOffset.name = "masterOffset";
            masterOffset.slider.setValue(0);

            var masterOffsetSpacing = n.Effects.addProperty("ADBE Slider Control");
            masterOffsetSpacing.name = "masterOffsetSpacing";
            masterOffsetSpacing.slider.setValue(20);

            var masterOffsetRandom = n.Effects.addProperty("ADBE Slider Control");
            masterOffsetRandom.name = "masterOffsetRandom";
            masterOffsetRandom.slider.setValue(0);
            
            var masterAmp = n.Effects.addProperty("ADBE Slider Control");
            masterAmp.name = "masterAmp";
            masterAmp.slider.setValue(1);

            var masterFreq = n.Effects.addProperty("ADBE Slider Control");
            masterFreq.name = "masterFreq";
            masterFreq.slider.setValue(1);

            var masterDelay = n.Effects.addProperty("ADBE Slider Control");
            masterDelay.name = "masterDelay";
            masterDelay.slider.setValue(1);

            var masterFallOff = n.Effects.addProperty("ADBE Slider Control");
            masterFallOff.name = "masterFallOff";
            masterFallOff.slider.setValueAtTime(0, 1);
            masterFallOff.slider.setValueAtTime(1, 1);

            var masterSubOffset = n.Effects.addProperty("ADBE Slider Control");
            masterSubOffset.name = "masterSubOffset";
            masterSubOffset.slider.setValue(0);

            var masterSubOffsetSpacing = n.Effects.addProperty("ADBE Slider Control");
            masterSubOffsetSpacing.name = "masterSubOffsetSpacing";
            masterSubOffsetSpacing.slider.setValue(20);

            var masterSubOffsetRandom = n.Effects.addProperty("ADBE Slider Control");
            masterSubOffsetRandom.name = "masterSubOffsetRandom";
            masterSubOffsetRandom.slider.setValue(0);

            var masterSubValue = n.Effects.addProperty("ADBE Slider Control");
            masterSubValue.name = "masterSubValue";
            masterSubValue.slider.setValue(0);

            var masterSubAmp = n.Effects.addProperty("ADBE Slider Control");
            masterSubAmp.name = "masterSubAmp";
            masterSubAmp.slider.setValue(1);

            var masterSubFreq = n.Effects.addProperty("ADBE Slider Control");
            masterSubFreq.name = "masterSubFreq";
            masterSubFreq.slider.setValue(1);

            var masterSubDelay = n.Effects.addProperty("ADBE Slider Control");
            masterSubDelay.name = "masterSubDelay";
            masterSubDelay.slider.setValue(1);

            var masterSubWaveDirection = n.Effects.addProperty("ADBE Angle Control");
            masterSubWaveDirection.name = "masterSubWaveDirection";

            var masterSubFallOff = n.Effects.addProperty("ADBE Slider Control");
            masterSubFallOff.name = "masterSubFallOff";
            masterSubFallOff.slider.setValueAtTime(0, 1);
            masterSubFallOff.slider.setValueAtTime(1, 1);
        };
    };
    function layerIndexExp()
    {
        var str         =   "if(thisComp.layer('MASTER_HR_controller').effect('Use windStartPoint')('Checkbox') == false)\n"+
                            "{"+
                            "   if(value == 0)\n"+
                            "   {\n"+
                            "       index\n"+
                            "   }else\n"+
                            "   {\n"+
                            "       Math.ceil(value);\n"+
                            "   };\n"+
                            "}else\n"+
                            "{\n"+
                            "   dist = length(thisLayer.effect('WindOrderPosition')('Point'), thisComp.layer('MASTER_HR_controller').effect('windStartPoint')('Point'));\n"+
                            "   (dist/thisComp.width)*thisComp.layer('MASTER_HR_controller').effect('masterOffsetSpacing')('Slider');\n"+
                            "};"; 

        /*var str         =   "dist = length(thisLayer.effect('WindOrderPosition')('Point'), thisComp.layer('MASTER_HR_controller').effect('windStartPoint')('Point'));\n"+
                            "(dist/thisComp.width)*thisComp.layer('MASTER_HR_controller').effect('masterOffsetSpacing')('Slider');";*/
        return str;
    };
    function loopsExp()
    {
        var str         =   "if(effect('Freq')('Slider').numKeys == 0 && thisComp.layer('MASTER_HR_controller').effect('masterFreq')('Slider').numKeys == 0 && comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('globalFreq')('Slider').numKeys == 0)\n"+
                            "{\n"+
                            "   1/effect('Freq')('Slider');//this is only for display purposes. Changing this slider will have no affect.\n"+
                            "}else\n"+
                            "{\n"+
                            "   0;//if you have a key in Freq, masterFreq, or globalFreq Animation Loop value errors and goes to 0\n"+
                            "};\n";
        return str;
    };
    function freqExp(s)
    {
        var str         =   "masterFreq = thisComp.layer('MASTER_HR_controller').effect('master"+s+"Freq')('Slider');\n"+
                            "globalFreq = comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('global"+s+"Freq')('Slider');\n"+
                            "value*masterFreq*globalFreq;";
        return str;
    };

    function ampExp(s)
    {
        var str         =   "masterAmp = thisComp.layer('MASTER_HR_controller').effect('master"+s+"Amp')('Slider');\n"+
                            "globalAmp = comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('global"+s+"Amp')('Slider');\n";
        if(s == "Sub")
        {
            str += "(value+thisComp.layer('MASTER_HR_controller').effect('masterSubValue')('Slider')+comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('globalSubValue')('Slider'))*masterAmp*globalAmp;";
        }else{
            str += "value*masterAmp*globalAmp;";
        };

        return str;
    };
    function delayExp(s)
    {
        var str         =   "masterDelay = thisComp.layer('MASTER_HR_controller').effect('master"+s+"Delay')('Slider');\n"+
                            "globalDelay = comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('global"+s+"Delay')('Slider');\n";

        str += "value*masterDelay*globalDelay;";
        

        return str;
    };
    function offsetExp(s)
    {
        var str         =   "ran = thisComp.layer('MASTER_HR_controller').effect('master"+s+"OffsetRandom')('Slider')*effect('RandomSeed')('Slider');\n"+ 
                            "if(thisComp.layer('MASTER_HR_controller').effect('Ascending > Descending')('Checkbox') == false)\n"+
                            "{\n"+
                            "    ((effect('layerIndex')('Slider')*thisComp.layer('MASTER_HR_controller').effect('master"+s+"OffsetSpacing')('Slider')*(-1)+ran)+thisComp.layer('MASTER_HR_controller').effect('master"+s+"Offset')('Slider'))*comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('global"+s+"OffsetSpacing')('Slider')+value;\n"+    
                            "}else\n"+
                            "{\n"+
                            "    ((effect('layerIndex')('Slider')*thisComp.layer('MASTER_HR_controller').effect('master"+s+"OffsetSpacing')('Slider')+ran)+thisComp.layer('MASTER_HR_controller').effect('master"+s+"Offset')('Slider'))*comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('global"+s+"OffsetSpacing')('Slider')+value;\n"+
                            "};";
        return str;
    };
                                    
    function waveMathExp(s)
    {
        var str         =   "//Wave Math//\n"+
                            "amp = effect('"+s+"Amp')(1);\n"+
                            "offset = framesToTime(effect('"+s+"Offset')(1));\n"+
                            "phase = effect('"+s+"PhaseLocator')('Slider');\n"+
                            "value + amp*Math.sin((phase+offset)*Math.PI*2);";
                            //"freq = effect('Freq')(1);\n"+
                            //"value + amp*Math.sin((time*freq+offset)*Math.PI*2);";
        return str;
    };

    function angleExp(id, ln, tp, s)
    {
        var pinId       =   id;
        var layerName   =   ln;
        var totalPins   =   tp;
        var isPuppetBone=   s;
        var boneStr     =   "";

        if(s == true)
        {
            boneStr = "thisLayer;";
        }else
        {
            boneStr = "thisComp.layer('"+layerName+"');";
        }

        var str         =   "pointFromParent= "+pinId+";\n"+
                            "refLayer = "+boneStr+"\n"+
                            "pos = refLayer.effect('Delay')('Slider')*(pointFromParent/"+(tp*2)+");\n"+
                            "fallOffLoc = (pointFromParent-1)/"+tp+";\n"+
                            "amp = refLayer.effect('Amp')('Slider')*refLayer.effect('FallOff')('Slider').valueAtTime(fallOffLoc)*thisComp.layer('MASTER_HR_controller').effect('masterFallOff')('Slider').valueAtTime(fallOffLoc)*comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('globalFallOff')('Slider').valueAtTime(fallOffLoc);\n"+
                            "freq = refLayer.effect('Freq')('Slider');\n"+
                            "masterFreq = thisComp.layer('MASTER_HR_controller').effect('masterFreq')('Slider');\n"+
                            "globalFreq = comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('globalFreq')('Slider');\n"+
                            "offset =refLayer.effect('Offset')('Slider');\n"+
                            "phase = refLayer.effect('PhaseLocator')('Slider');\n"+
                            "delay = 1-(pos*(1/refLayer.effect('Freq')('Slider')));\n"+
                            "\n"+
                            "n = freq.numKeys+masterFreq.numKeys+globalFreq.numKeys;\n"+
                            "if (n > 0)\n"+
                            "{\n"+
                            "    delay = (1-(pos));\n"+
                            "};\n"+
                            "value+refLayer.effect('WaveMath')('Angle').valueAtTime(time+delay)*amp;\n";
                            //"    value + (amp*Math.sin((phase.valueAtTime(time+delay+offset))*Math.PI*2))*amp;\n"+
        return str;
    };
    
    function phaseLocatorExp(s)
    {
        var str         =   "//"+s+"PhaseLocator//\n"+
                            "freq = effect('"+s+"Freq')('Slider');\n"+
                            "masterFreq = thisComp.layer('MASTER_HR_controller').effect('master"+s+"Freq')('Slider');\n"+
                            "globalFreq = comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('global"+s+"Freq')('Slider');\n"+
                            "offset =effect('"+s+"Offset')('Slider')\n"+
                            "\n"+
                            "//this array only adds layers with linear keys\n"+
                            "layersWithKeys = [];\n"+
                            "\n"+
                            "//total key array from all layers\n"+
                            "keyArr = [];\n"+
                            "\n"+
                            "//find linear keys in freq, masterFreq, and globalFreq\n"+
                            "n = freq.numKeys+masterFreq.numKeys+globalFreq.numKeys;\n"+
                            "if (n > 0)\n"+
                            "{\n"+
                            "    //checks which layers has keys\n"+
                            "    if(freq.numKeys>0)\n"+
                            "    {\n"+
                            "        layersWithKeys[layersWithKeys.length] = freq;\n"+
                            "    };\n"+
                            "    if(masterFreq.numKeys>0)\n"+
                            "    {\n"+
                            "        layersWithKeys[layersWithKeys.length] = masterFreq;\n"+
                            "    };\n"+
                            "    if(globalFreq.numKeys>0)\n"+
                            "    {\n"+
                            "        layersWithKeys[layersWithKeys.length] = globalFreq;\n"+
                            "    };\n"+
                            "    \n"+
                            "    //adds all keys into one array\n"+
                            "    for (d = 0; d < layersWithKeys.length; d++)\n"+
                            "    {\n"+
                            "        for (k = 1; k <= layersWithKeys[d].numKeys; k++)\n"+
                            "        {\n"+
                            "            if(keyArr.length != 0)\n"+
                            "            {\n"+
                            "                bol = false;\n"+
                            "                for (g = 0; g < keyArr.length; g++)\n"+
                            "                {\n"+
                            "                    if(keyArr[g].time == layersWithKeys[d].key(k).time)\n"+
                            "                    {\n"+
                            "                        bol = true;\n"+
                            "                    }\n"+
                            "                    if(bol == false && g == keyArr.length - 1)\n"+
                            "                    {\n"+
                            "                        keyArr.push(layersWithKeys[d].key(k));\n"+
                            "                    };\n"+
                            "                };\n"+
                            "            }else\n"+
                            "            {\n"+
                            "                keyArr.push(layersWithKeys[d].key(k));\n"+
                            "            };\n"+
                            "        };\n"+
                            "    };\n"+
                            "    \n"+
                            "    //sort array in chronological order\n"+
                            "    keyArr.sort(function(a, b){return a.time - b.time});\n"+
                            "};\n"+
                            "\n"+
                            "//linear sine wave frequency solve\n"+
                            "if(n > 0 && keyArr[0].time < time)\n"+
                            "{\n"+
                            "    phase = freq.valueAtTime(keyArr[0].time)*(keyArr[0].time - inPoint);\n"+
                            "    for (i = 1; i < keyArr.length; i++)\n"+
                            "    {\n"+
                            "        if (keyArr[i].time > time) break;\n"+
                            "        phase += (freq.valueAtTime(keyArr[i-1].time) + freq.valueAtTime(keyArr[i].time))*(keyArr[i].time - keyArr[i-1].time)/2;\n"+
                            "    };\n"+
                            "    phase += (freq.value + freq.valueAtTime(keyArr[i-1].time))*(time - keyArr[i-1].time)/2;\n"+
                            "}else\n"+
                            "{\n"+
                            "    phase = freq.value*(time - inPoint);\n"+
                            "};\n"+
                            "\n"+
                            "phase;";
                        
        return str;
    };

    function pinBonesExp(id, t)
    {
        var pinId       =   id;
        var totalPins   =   t;
        var str         =   "//get pen index from chain\n"+
                            "id="+pinId+";\n"+
                            "\n"+
                            "//collect pens default position value\n"+
                            "penArr = [];\n"+
                            "for(p=1;p<id+1;p++)\n"+
                            "{\n"+
                            "    penArr[p] =  effect('pin'+p+'Pos')('Point');\n"+
                            "};\n"+
                            "\n"+
                            "//sets the chain array up for updated values\n"+
                            "chainArr = penArr;\n"+
                            "for(i=1;i<id+1;i++)\n"+
                            "{\n"+
                            "    parentPoint = chainArr[i];\n"+
                            "    for(c=i+1;c<id+1;c++)\n"+
                            "    {\n"+
                            "        point = chainArr[c];\n"+
                            "\n"+
                            "        /*runs through wavelength math*/\n"+
                            "        delta = point - parentPoint;\n"+
                            "        angletoFollow = effect('pin'+i+'Rot')('Angle');\n"+
                            "        angle = Math.atan2(delta[1], delta[0])+degreesToRadians(angletoFollow);\n"+
                            "        \n"+
                            "        /*gets distance between points and turns it into radius*/\n"+
                            "        dif = penArr[i]-penArr[c];\n"+
                            "        a = dif[0];\n"+
                            "        b = dif[1];\n"+
                            "        radius = Math.sqrt((a*a)+(b*b));\n"+
                            "        \n"+
                            "        /*sets new position and save it for next calulation*/\n"+
                            "        chainArr[c] = parentPoint + [Math.cos(angle), Math.sin(angle)]*radius;\n"+
                            "    };\n"+
                            "};\n"+
                            "chainArr[id];\n"+
                            "refLayer = this;\n"+
                            "pos = refLayer.effect('SubDelay')('Slider')*(id/("+totalPins+"*2));\n"+
                            "fallOffLoc = (id-1)/"+totalPins+";\n"+
                            "amp = refLayer.effect('SubAmp')('Slider')*refLayer.effect('SubFallOff')('Slider').valueAtTime(fallOffLoc)*thisComp.layer('MASTER_HR_controller').effect('masterSubFallOff')('Slider').valueAtTime(fallOffLoc)*comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('globalSubFallOff')('Slider').valueAtTime(fallOffLoc);\n"+
                            "delay = 1-(pos*(1/refLayer.effect('SubFreq')('Slider')));\n"+
                            "tempAmp = refLayer.effect('SubWaveMath')('Angle').valueAtTime(time+delay)*amp;\n"+
                            "angle =refLayer.effect('SubWaveDirection')('Angle')+thisComp.layer('MASTER_HR_controller').effect('masterSubWaveDirection')('Angle')+comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('globalSubWaveDirection')('Angle')+effect('pin'+id+'Rot')('Angle');\n"+
                            "aRad =degreesToRadians( angle - 90);\n"+
                            "x=tempAmp*Math.cos(aRad);\n"+
                            "y=tempAmp*Math.sin(aRad);\n"+
                            "[chainArr[id][0]+x, chainArr[id][1]+y];";
        return str;
    };
    
    


    function subPointExp(id, ln, tp, v1, v2)
    {
        var pinId       =   id;
        var layerName   =   ln;
        var totalPins   =   tp;
        var str         =   "pointFromParent= "+pinId+";\n"+
                            "refLayer = thisComp.layer('"+layerName+"');\n"+
                            "pos = refLayer.effect('SubDelay')('Slider')*(pointFromParent/("+totalPins+"*2));\n"+
                            "fallOffLoc = (pointFromParent-1)/"+totalPins+";\n"+
                            "amp = refLayer.effect('SubAmp')('Slider')*refLayer.effect('SubFallOff')('Slider').valueAtTime(fallOffLoc)*thisComp.layer('MASTER_HR_controller').effect('masterSubFallOff')('Slider').valueAtTime(fallOffLoc)*comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('globalSubFallOff')('Slider').valueAtTime(fallOffLoc);\n"+
                            "delay = 1-(pos*(1/refLayer.effect('SubFreq')('Slider')));\n"+
                            "tempAmp = refLayer.effect('SubWaveMath')('Angle').valueAtTime(time+delay)*amp;\n"+
                            "angle =refLayer.effect('SubWaveDirection')('Angle')+thisComp.layer('MASTER_HR_controller').effect('masterSubWaveDirection')('Angle')+comp('GLOBAL_HR_controller').layer('GLOBAL_HR_controller').effect('globalSubWaveDirection')('Angle');\n"+
                            "aRad =degreesToRadians( angle - 90);\n"+
                            "x=tempAmp*Math.cos(aRad);\n"+
                            "y=tempAmp*Math.sin(aRad);\n"+
                            "["+v1+"+x, "+v2+"+y];";
        return str;
    };
    function buildAFPExp(s)
    {
        var str         =   scriptTitle+"\n"+
                            "if(thisComp.layer('MASTER_HR_controller').effect('TurnOffHairRig')('Checkbox') == false)\n"+
                            "{\n"+
                            "\n"+
                                s+"\n"+
                            "\n"+
                            "}else\n"+
                            "{\n"+
                            "   value;\n"+
                            "};";
        return str;
    }
    function aboutTxt()
    {
        var str         =   "Version "+scriptVersion+"\n"+
                            "\n"+
                            "Script by Anthony Possobon\n"+
                            "anthonypossobon@gmail.com";

        return str;
    };

    function notesTxtUpdate()
    {
        var str         =   "";
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Mar 13, 2020)\n";        
        var noteArr     = ["Fixed a bug where if you choose the puppet pin bone structure and duplicated your hair layers, the expressions of the duplicated layers reference the original layer instead of its own."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Feb 8, 2020)\n";        
        var noteArr     = ["Added to MASTER_HR_controller a 'Use useWindStartPoint' controller that turns on and off the function of 'useWindStartPoint'.",
                            "Set SubFallOff first keyframe to 0 instead of .2",
                            "Added 'Animation Loops every(sec)' controller to display when the loop occurs when adjusting Freq controller.",
                            "Added masterSubDelay and globalSubDelay."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(April 28, 2019)\n";        
        var noteArr     = ["Added to MASTER_HR_controller a 'windStartPoint' controller that lets you choose the order you want all hairs in the comp to animate in.",
                            "Added windOrderPosition controller to each hair that decides where it is in the ordering stack.",
                            "Added globalDelay and globalAmp."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Feb 2, 2019)\n";        
        var noteArr     = ["Fixed a bug where if After Effects's language is set to anything other than English it doesn't run. Now should work with languages other than English.",
                            "If AFPDelay is launched through the launcher it now will close any instances of itself!"];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Dec 29, 2018)\n";        
        var noteArr     = ["Fixed a bug for CC 2019 where an error would appear after placing a key in masterFreq."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Dec 14, 2018)\n";        
        var noteArr     = [ "Can now run the script again on a preexisting hair or hairs to repair missing controllers or to reset the hairs to the default setting instead of manually deleting controllers and expressions. DOES NOT support the Null bone stucture."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Dec 11, 2018)\n";        
        var noteArr     = [ "Bug fix where an error would occure for version before CC 2018."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Dec 6, 2018)\n";        
        var noteArr     = [ "Updated the script to be AE 2019 CC compliant."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Dec 4, 2018)\n";        
        var noteArr     = [ "Added new a controller breakdown section in the help panel.",
                            "Optimized some naming conventions throughout script.",
                            "Added SubDelay controller",
                            "Created descriptions for controllers."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Nov 5, 2018)\n";        
        var noteArr     = [ "Added masterFallOff and globalFallOff controllers.",
                            "Added masterSubFallOff and globalSubFallOff controllers.",
                            "Added masterSubValue and globalSubValue controllers.",
                            "Added masterSubWaveDirection and globalSubWaveDirection controllers. Wind like.",
                            "Added masterSubOffset, masterOffsetRandom, masterOffsetSpacing to make it seem like a gust of wind.",
                            "Added TurnOffHairRig to the master controller to have a off switch",
                            "Now you can change the layer index to determine animation order with layerIndex controller."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Nov 4, 2018)\n";        
        var noteArr     = [ "Frequency is now animatable. It switchs on as soon as there as been a keyframe added to freq, masterFreq, and/or globalFreq.",
                            "Reduce keyframes to Falloff. Now only one at time 0 and another at time 1.",
                            "Global hair controller comp is longer now"];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "(Oct 31, 2018)\n";        
        var noteArr     = [ "Integration of 2 separate bones paths, pin bones and null bones, into one script.",
                            "New UI panel when launch.",
                            "Corrected wave math to pin point bones equation.",
                            "Added subwave math to pin point bones equations.",
                            "Rename layer function added"];
                            
        for (var i = 0; i < noteArr.length; i++) 
        {
            str += "- "+noteArr[i]+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        return str;
    };
    function controllerTxtUpdate()
    {
        var str         =   "";
        //////////////////////////////////////////////////////////////////////////////
        str += "/////LAYER CONTROLLERS//////\n";        
        var noteArr     = [ "layerIndex: \nMultiplied by masterSubOffsetSpacing and globalOffsetSpacing to offset the order of which the layer animates in time. This value automatically assumes its index from its location in the comp stack. If a value is entered, then it will assume the new value. NOT TO BE ANIMATED.",
                            "RandomSeed: \nMultiplied by masterOffsetRandom, will randomly order this layers animation in time from other layers. NOT TO BE ANIMATED.",
                            "Freq: \nFrequency is how often it loops per 1 second. 1 = loops in one second. .5 = loops in two seconds. 2 = loops every half second. Can be anmiated.",
                            "Amp: \nAmplitude is the highest and lowest rotation value the layers bones will animate. Can be anmiated.",
                            "Animation Loops every(sec): \nThis controller is to display when the loop occurs when adjusting Freq controller. Changing this will have no affect.",
                            "WindOrderPosition: \nWhen enabling 'Use windStartPoint' in the MASTER_HR_controller, this value is the point that is registered with 'Use windStartPoint' controller.",
                            "FallOff: \nFall off is the power of amplitude per puppet pin distributed over the animated keys from 0 to 1. 0 in the timeline is where the first pin gets its value where as 1 in the timeline is where the last pin gets its value. The value it takes is multiplied by the pins amplitude. NOT TO BE ANIMATED.",
                            "Offset: \nOffsets this layers location for where the loop begins in frames. NOT TO BE ANIMATED.",
                            "Delay: \nOffsets each puppet pin in time from its parent puppet pin. Also known as spacing of animation per puppet pin. NOT TO BE ANIMATED.",
                            "WaveMath: \nDO NOT ADJUST THIS. The math used to animate each bone. NOT TO BE ANIMATED.",
                            "PhaseLocator: \nDO NOT ADJUST THIS. The math used to allow for animatable frequency. NOT TO BE ANIMATED.",
                            "SubFreq: \nSub-wave Frequency is how often it loops per 1 second. Can be anmiated.",
                            "SubAmp: \nSub-wave Amplitude is the highest and lowest position value in pixels the layers bones will animate. Can be anmiated.",
                            "SubWaveDirection: \nBecause sub-wave uses position, SubWaveDirection is used for which direction you'd like for the position point to head. Can be anmiated.",
                            "SubOffset: \nOffsets this layers sub-wave location for where the loop begins in frames. NOT TO BE ANIMATED.",
                            "SubDelay: \nOffsets each puppet pin in time from its parent puppet pin. NOT TO BE ANIMATED.",
                            "SubFallOff: \nSub Fall off is the power of amplitude per puppet pin distributed over the animated keys from 0 to 1. NOT TO BE ANIMATED.",
                            "SubPhaseLocator: \nDO NOT ADJUST THIS. The math used to allow for animatable sub-wave frequency. NOT TO BE ANIMATED.",
                            "pin[pinNumber]Rot: \nSaves the puppet pins rotation for rigging use. Can be anmiated.",
                            "pin[pinNumber]Pos: \nDO NOT ADJUST THIS. Save the initial distance between puppet pins. NOT TO BE ANIMATED."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += noteArr[i]+"\n"+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "\n";
        str += "/////MASTER CONTROLLERS : 'MASTER_HR_controller'//////\n";        
        var noteArr     = [ "TurnOffHairRig: \nQuickly turn off and on the script after use to help with performance with other animates and setup. NOT TO BE ANIMATED.",
                            "Ascending > Descending: \nChanges the order of the layerIndex per layer when multiplied by masterOffsetSpacing and globalOffsetSpacing. NOT TO BE ANIMATED.",
                            "Use windStartPoint: \nWhen enabled, all the hairs in this comp when animation in the order closest to the windStartPoint controller. Disabled, hair layers will animate in the order of the layerIndex controller number. NOT TO BE ANIMATED.",
                            "masterOffset: \nOffsets every layer's starting animation location, in frames, within the composition. NOT TO BE ANIMATED.",
                            "masterOffsetSpacing: \nMultiplied by layerIndex, this creates spacing for every layer in the composition to animate. NOT TO BE ANIMATED.",
                            "masterOffsetRandom: \nMultiplied by RandomSeed, will randomly order all layer animations in the composition. NOT TO BE ANIMATED.",
                            "masterAmp: \nMultiplies Amp to all layers in the composition. Can be anmiated.",
                            "masterFreq: \nMultiplies Freq to all layers in the composition. Can be anmiated.",
                            "masterDelay: \nOffsets each puppet pin in time from its parent puppet pin in this comp. NOT TO BE ANIMATED.",
                            "masterFallOff: \nMultiplies Falloff to all layers in the composition. NOT TO BE ANIMATED.",
                            "masterSubOffset: \nAdds to SubOffset to all layers in the composition. NOT TO BE ANIMATED.",
                            "masterSubOffsetSpacing: \nMultiplied by layerIndex and globalOffsetSpacing to offset the order of which the layer animates in time. NOT TO BE ANIMATED.",
                            "masterSubOffsetRandom: \nMultiplied by RandomSeed, will randomly order the composition layer's sub-wave animation in time. NOT TO BE ANIMATED.",
                            "masterSubValue: \nAdds to SubAmp to all layers in the composition. Can be animated.",
                            "masterSubAmp: \nMultiplies SubAmp to all layers in the composition. Can be animated.",
                            "masterSubWaveDirection: \nAdds to SubWaveDirection to all layers in the composition. Can be animated.",
                            "masterSubFreq: \nMultiplies SubFreq to all layers in the composition. Can be animated.",
                            "masterSubDelay: \nOffsets each puppet pin sub wave in time from its parent puppet pin in this comp. NOT TO BE ANIMATED.",
                            "masterSubFallOff: \nMultiplies SubFallOff to all layers in the composition. NOT TO BE ANIMATED."];

        for (var i = 0; i < noteArr.length; i++) 
        {
            str += noteArr[i]+"\n"+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        str += "\n";
        str += "\n";
        str += "/////GLOBAL CONTROLLERS : 'GLOBAL_HR_controller'//////\n";        
        var noteArr     = [ "globalOffsetSpacing: \nMultiplied by layerIndex, this creates spacing for every layer in the project to animate. NOT TO BE ANIMATED.",
                            "globalSubOffsetSpacing: \nMultiplied by layerIndex, this creates spacing for every layer in the project to animate. NOT TO BE ANIMATED.",
                            "globalAmp: \nMultiplies Amp to all layers in the project. Can be anmiated.",
                            "globalFreq: \nMultiplies Freq to all layers in the project. Can be anmiated. Great for wind!",
                            "globalDelay: \nOffsets each puppet pin in time from its parent puppet pin in your project. NOT TO BE ANIMATED.",
                            "globalFallOff: \nMultiplies Falloff to all layers in the project. NOT TO BE ANIMATED.",
                            "globalSubValue: \nAdds to SubAmp to all layers in the project. Can be animated.",
                            "globalSubAmp: \nMultiplies SubAmp to all layers in the project. Can be animated.",
                            "globalSubWaveDirection: \nAdds to SubWaveDirection to all layers in the project. Can be animated.",
                            "globalSubFreq: \nMultiplies SubFreq to all layers in the project. Can be animated.",
                            "globalSubDelay: \nOffsets each puppet pin sub wave in time from its parent puppet pin in your project. NOT TO BE ANIMATED.",
                            "globalSubFallOff: \nMultiplies SubFallOff to all layers in the project. NOT TO BE ANIMATED."];
                            
        for (var i = 0; i < noteArr.length; i++) 
        {
            str += noteArr[i]+"\n"+"\n";
        };
        //////////////////////////////////////////////////////////////////////////////
        return str;
    };
    app.endUndoGroup();
};

