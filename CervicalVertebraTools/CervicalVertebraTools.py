
#======================================================================================
#  3D Slicer [1] plugin that uses elastix toolbox [2] Plugin for Automatic Vertebra   # 
#  Image Segmentation and other useful features extraction[3]                         #.
#  More info can be found at [4].                                                     #
#  Sample vertebra datasets can be downloaded using Slicer Datastore module            #
#                                                                                     #
#  Contributers:                                                                      #   
#      - Christopher L. Guy,   guycl@vcu.edu              : Original source code.     #
#      - Ibraheem Al-Dhamari,  idhamari@uni-koblenz.de    : Plugin design.            #
#      - Michel Peltriaux,     mpeltriaux@uni-koblenz.de  : Programming & testing.    #
#      - Anna Gessler,         agessler@uni-koblenz.de    : Programming & testing.    #
#      - Jasper Grimmig        jgrimmig@uni-koblenz.de    : Programming & testing.    #
#      - Pepe Eulzer           eulzer@uni-koblenz.de      : Programming & testing.    #  
#  [1] https://www.slicer.org                                                         #
#  [2] http://elastix.isi.uu.nl                                                       #
#  [3] TODO: add paper Al-Dhamari et al.,(2018),                                      #
#                                                 f                                    #
#  [4] https://mtixnat.uni-koblenz.de                                                 #
#                                                                                     #
#  Updated: 9.1.2019                                                                 #    
#                                                                                     #  
#======================================================================================

import os, re , datetime, time ,shutil, unittest, logging, zipfile, urllib2, stat,  inspect
import sitkUtils, sys ,math, platform, subprocess  
import numpy as np, SimpleITK as sitk
import vtkSegmentationCorePython as vtkSegmentationCore
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *   
from copy import deepcopy
from collections import defaultdict
from os.path import expanduser
from os.path import isfile
from os.path import basename
from PythonQt import BoolResult
from shutil import copyfile
from decimal import *

import Elastix
import SegmentStatistics
#TODO:

# 1. test user inputs
# 2. test windows
# 3. cleaning 
# 4. remove temps nodes and files 
# 5. test again


# Public version: without methods   
# Documentation
# Video tutorials
# Uploas all
# VisSimTools and sample data to google drive
 
#   Registration download all stuff for both registration and segmentation.
#   use registration module and commong functions:  
#   Remove inverted transform, it was using in case switching moving and fixed 
# Later:
# - Checking if all above are needed 
# - Cleaning, optimizing, commenting.  
# - Testing in both Windows and Linux. 
# - Supporting DICOM. 
# - Supporting illegal filename.  
# - Using  SlierElastix binaries.   
# - Visualizing the interimediate steps. 
# 
#  
# Terminology
#  img         : ITK image 
#  imgNode     : Slicer Node
#  imgPath     : wholePath + Filename
#  imgFnm      : Filename without the path and the extension
#  imgFileName : Filename without the path

#===================================================================
#                           Main Class
#===================================================================

class VertebraTools(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Vertebra Tools"
        parent.categories = ["VisSimTools"]
        parent.dependencies = []
        parent.contributors = ["Christopher Guy",
                               "Ibraheem Al-Dhamari",
                               "Michel Peltriauxe",
                               "Anna Gessler",
                               "Jasper Grimmig",
                               "Pepe Eulzer"  
         ]
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        #TODO: add sponsor
        parent.acknowledgementText = " This work is sponsored by ................ "
        self.parent = parent
  #end def init
#end class vertebraSeg

    
#===================================================================
#                           Main Widget
#===================================================================
class VertebraToolsWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    print(" ")
    print("=======================================================")   
    print("   VisSIm Cervical Spine Vertebra Tools               ")
    print("=======================================================")           
        
    ScriptedLoadableModuleWidget.setup(self)
    
    # to access logic class functions and setup global variables
    self.logic = VertebraToolsLogic()
    # Set default VisSIm location in the user home 
    #TODO: add option user-defined path when installed first time 
    self.vtVars = self.logic.setGlobalVariables(True)
    
    #=================================================================
    #                     Create the GUI interface
    #=================================================================   
    # Create main collapsible Button 
    self.mainCollapsibleBtn = ctk.ctkCollapsibleButton()
    self.mainCollapsibleBtn.setStyleSheet("ctkCollapsibleButton { background-color: DarkSeaGreen  }")
    self.mainCollapsibleBtn.text = "VisSim Cervical Spine Tools"
    self.layout.addWidget(self.mainCollapsibleBtn)
    self.mainFormLayout = qt.QFormLayout(self.mainCollapsibleBtn)
  
    # Create input Volume Selector
    self.inputSelectorCoBx = slicer.qMRMLNodeComboBox()
    self.inputSelectorCoBx.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelectorCoBx.setFixedWidth(200)
    self.inputSelectorCoBx.selectNodeUponCreation = True
    self.inputSelectorCoBx.addEnabled = False
    self.inputSelectorCoBx.removeEnabled = False
    self.inputSelectorCoBx.noneEnabled = False
    self.inputSelectorCoBx.showHidden = False
    self.inputSelectorCoBx.showChildNodeTypes = False
    self.inputSelectorCoBx.setMRMLScene( slicer.mrmlScene )
    self.inputSelectorCoBx.setToolTip("select the input image")
    self.mainFormLayout.addRow("Input image: ", self.inputSelectorCoBx)

    # use qtcombobox
    self.vILbl = qt.QLabel()
    self.vILbl.setText("Which Vertebra? 1-7")        
    self.vILbl.setFixedHeight(20)
    self.vILbl.setFixedWidth(150)
    
    #TODO: include head and shoulders
    self.vtIDCoBx = qt.QComboBox()
    self.vtIDCoBx.addItems(["C1","C2","C3","C4","C5","C6","C7"])
    self.vtIDCoBx.setCurrentIndex(2)
    self.vtIDCoBx.setFixedHeight(20)
    self.vtIDCoBx.setFixedWidth(100)        
    #self.vtIDCoBx.setReadOnly(False) # The point can only be edited by placing a new Fiducial
    # if changed , the default value will change  
    self.vtIDCoBx.connect("currentIndexChanged(int)", self.onVtIDCoBxChange)                  
    #self.mainFormLayout.addRow( self.vILbl,  self.vtIDCoBx )        
      
    # Create a textbox for vertebra location
    # TODO activate input IJK values as well
    Pt = [0,0,0]
    self.inputPointEdt = qt.QLineEdit()
    self.inputPointEdt.setFixedHeight(20)
    self.inputPointEdt.setFixedWidth(100)
    self.inputPointEdt.setText(str(Pt))
    self.inputPointEdt.connect("textChanged(QString)", self.onInputPointEdtChanged)                                  
    #self.inputPointEdt.connect("textEdited(str)", self.onInputPointEdtEdited)                                  

    self.mainFormLayout.addRow( self.inputPointEdt, self.vtIDCoBx)    

    # use qtcombobox
    self.vtMthdLbl = qt.QLabel()
    self.vtMthdLbl.setText("Which Method?")        
    self.vtMthdLbl.setFixedHeight(20)
    self.vtMthdLbl.setFixedWidth(150)
    
    self.vtMethods = ["Vertebra","Vertebral body","Vertebral endplates","Vertebral endplates outside","Vertebral endplates inside"]
    self.vtMethodIDCoBx = qt.QComboBox()
    #TODO: check the names
    self.vtMethodIDCoBx.addItems(self.vtMethods)
    self.vtMethodIDCoBx.setCurrentIndex(0)
    self.vtMethodIDCoBx.setFixedHeight(20)
    self.vtMethodIDCoBx.setFixedWidth(200)        
    #self.vtIDCoBx.setReadOnly(False) # The point can only be edited by placing a new Fiducial  
    # if changed , the default value will change
    self.vtMethodIDCoBx.connect("currentIndexChanged(int)", self.onVtMethodIDCoBxChange)                                 
    self.mainFormLayout.addRow( self.vtMthdLbl,  self.vtMethodIDCoBx )    

    # Add check box for extracting ligaments points 
    self.ligPtsChkBx = qt.QCheckBox("Ligaments points")
    self.ligPtsChkBx.checked = True
    self.ligPtsChkBx.stateChanged.connect(self.onLigPtsChkBxChange)
    # Add check box for extracting muscle points 
    self.musPtsChkBx = qt.QCheckBox("Muscle points")
    self.musPtsChkBx.checked = True
    self.musPtsChkBx.stateChanged.connect(self.onMusPtsChkBxChange)
    self.mainFormLayout.addRow(self.ligPtsChkBx,self.musPtsChkBx)

    # Add check box for using iso resampled models
    self.hrChkBx = qt.QCheckBox()
    self.hrChkBx.checked = True
    self.hrChkBx.text = "Resampling"
    self.hrChkBx.stateChanged.connect(self.onHrChkBxChange)
 
    # Add check box for using MR models
    #TODO: add the model and implementation 
    self.mrChkBx = qt.QCheckBox()
    self.mrChkBx.checked = False
    self.mrChkBx.text = "MRI model"
    #self.mainFormLayout.addRow(self.hrChkBx, self.mrChkBx)

    # Create a time label
    self.timeLbl = qt.QLabel("  Time: 00:00")
    self.timeLbl.setFixedWidth(500)   
    self.tmLbl = self.timeLbl
    
    # Create a button to run segmentation
    self.applyBtn = qt.QPushButton("Run")
    self.applyBtn.setFixedHeight(50)
    self.applyBtn.setFixedWidth (150)
    self.applyBtn.setStyleSheet("QPushButton{ background-color: DarkSeaGreen  }")
    self.applyBtn.toolTip = ('How to use:' ' Load an images into Slicer. Pick vertebra locations using the buttons and the Slicer Fiducial tool ')
    self.applyBtn.connect('clicked(bool)', self.onApplyBtnClick)
    self.mainFormLayout.addRow(self.applyBtn, self.timeLbl)
    self.runBtn = self.applyBtn

    # Create a button to scale and translate to center of mass
    self.extractScaledModelBtn = qt.QPushButton("Scaling")
    self.extractScaledModelBtn.setFixedHeight(20)
    self.extractScaledModelBtn.setFixedWidth (150)
    self.extractScaledModelBtn.enabled =False
    self.extractScaledModelBtn.toolTip = ('Scale model and points to 1 mm and translate them to the model center of mass ')
    self.extractScaledModelBtn.connect('clicked(bool)', self.onExtractScaledModelBtnClick)

    # Create a button to display result folder
    self.openResultFolderBtn = qt.QPushButton("open output folder")
    self.openResultFolderBtn.setFixedHeight(20)
    self.openResultFolderBtn.setFixedWidth (150)
    self.openResultFolderBtn.setStyleSheet("QPushButton{ background-color: DarkSeaGreen  }")
    self.openResultFolderBtn.toolTip = ('Scale model and points to 1 mm and translate them to the model center of mass ')
    self.openResultFolderBtn.connect('clicked(bool)', self.onOpenResultFolderBtnClick)
    
    self.mainFormLayout.addRow(self.extractScaledModelBtn,self.openResultFolderBtn)

    self.layout.addStretch(1) # Collapsible button is held in place when collapsing/expanding.
    lm = slicer.app.layoutManager();    lm.setLayout(2)

  def cleanup(self):#nothing to do
    pass
  #enddef

  def onVtMethodIDCoBxChange(self):
      #print(self.vtMethodIDCoBx.setCurrentText)
      self.logic.vtVars = self.logic.setVtMethodID(self.vtMethodIDCoBx.currentIndex,self.logic.vtVars)  
  #enddef

  #------------------------------------------------------------------------
  #                        Vertebra Selection
  #------------------------------------------------------------------------
  def onVtIDCoBxChange(self):
      self.inputVolumeNode=self.inputSelectorCoBx.currentNode()
      self.vtID = self.vtIDCoBx.currentIndex + 1   
      self.logic.inputVolumeNode  =  self.inputVolumeNode 
      self.logic.inputFiducialNode = None
      nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
      for f in nodes:
          if ((f.GetName() == self.inputVolumeNode.GetName()+"_vtLocations") ):
             #replace  current 
             print("inputFiducialNode exist")
             self.logic.inputFiducialNode = f  
             newNode= False
            #endif
      #endfor    

      self.logic.setVtID(self.vtID, self.logic.inputVolumeNode , self.logic.inputFiducialNode)
      self.logic.locateVertebra(self.inputVolumeNode, self.vtID, self.inputPointEdt)    
      #self.onInputFiducialBtnClick()
  #enddef

  def onInputPointEdtChanged(self,point):
      self.vtID = self.vtIDCoBx.currentIndex + 1   
      self.logic.setVtIDfromEdt(point,self.vtID)
  #enddef
    
  # resample or not  
  # TODO: automate the process
  def onHrChkBxChange(self):      
      self.logic.setHrChk(self.hrChkBx.checked)
  #enddef

  # extract ligaments points 
  def onLigPtsChkBxChange(self):      
      nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
      self.logic.setLigChk(self.ligPtsChkBx.checked, nodes)
  #enddef
  
  # extract muscle points 
  def onMusPtsChkBxChange(self):      
      nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
      self.logic.setMusChk(self.musPtsChkBx.checked,nodes)
  #enddef

  
  def onApplyBtnClick(self):
    self.runBtn.setText("...please wait")
    self.runBtn.setStyleSheet("QPushButton{ background-color: red  }")
    slicer.app.processEvents  
    self.stm=time.time()
    print("time:" + str(self.stm))
    self.timeLbl.setText("                 Time: 00:00")

    self.vtID = self.vtIDCoBx.currentIndex + 1
    self.inputNode = self.inputSelectorCoBx.currentNode()
    pointSelected = self.inputPointEdt.text =="[0,0,0]"
    try: 
       if  (not self.inputNode is None) and (not pointSelected) and (not self.logic.inputFiducialNode is None):
            # create an option to use IJK point or fidicual node
            # inputImage, FiducialPoint, vertebraID, isExteranl ,C7Editbox
            self.logic.run(self.inputNode ,self.logic.inputFiducialNode, self.vtID ,False)
            self.extractScaledModelBtn.setStyleSheet("QPushButton{ background-color: DarkSeaGreen  }")
            self.extractScaledModelBtn.enabled = True
       else:
            print("error in input")
    except Exception as e:
            print("STOPPED: error in input")
            print(e)
    #endtry        
            
    self.etm=time.time()
    tm=self.etm - self.stm
    self.timeLbl.setText("Time: "+str(tm)+"  seconds")
    self.runBtn.setText("Run")
    self.runBtn.setStyleSheet("QPushButton{ background-color: DarkSeaGreen  }")
    slicer.app.processEvents()
  #enddef
  
  def onExtractScaledModelBtnClick(self):
      self.logic.extractScaledModel(self.logic.vtResultSegNode,self.logic.vtVars['segNodeCoM'],self.vtVars['subVarsFnm'])
      if self.ligPtsChkBx.checked:
          self.logic.extractScaledModel(self.logic.vtResultLigPtsNode,self.logic.vtVars['segNodeCoM'],self.vtVars['subVarsFnm'])      
      #endif
      if self.musPtsChkBx.checked:
          self.logic.extractScaledModel(self.logic.vtResultMusPtsNode,self.logic.vtVars['segNodeCoM'],self.vtVars['subVarsFnm'])
      #endif
      self.logic.msgBox("Done! scaled model is saved.")
      #TODO: add option for show/hide the result. 
      
  def onOpenResultFolderBtnClick(self):
      output = expanduser("~/VisSimTools")   + "/outputs"
      self.logic.openResultsFolder(output)
  #enddef      

  def s2b(self,s):
        return s.lower() in ("yes", "true", "t", "1")
  #enddef

#===================================================================
#                           Logic
#===================================================================
class VertebraToolsLogic(ScriptedLoadableModuleLogic):


  ElastixLogic = Elastix.ElastixLogic()
  ElastixBinFolder = ElastixLogic.getElastixBinDir() 
  vtVars = {}

  def s2b(self,s):
        return s.lower() in ("yes", "true", "t", "1")
  #enddef
  
  #set global paths and parameters
  def setGlobalVariables(self, isExternalCall):
    print("SpineToolsLogic: initializing global variables:")  
    #self.VTl.setGlobalVariables(True)
    #define a dictonary
    self.vtVars['vissimPath']           = os.path.join(expanduser("~"),"VisSimTools")
    self.vtVars['elastixBinPath']       = os.path.join(self.ElastixBinFolder, "elastix")
    self.vtVars['transformixBinPath']   =  os.path.join(self.ElastixBinFolder, "transformix")  
    self.vtVars['othersWebLink']        = "https://mtixnat.uni-koblenz.de/owncloud/index.php/s/UhqdBivFHWfejDM/download"
    self.vtVars['noOutput']             = " >> /dev/null"
    self.vtVars['outputPath']           = os.path.join(self.vtVars['vissimPath'],"outputs")
    self.vtVars['parsPath']             = self.vtVars['vissimPath']  + ",pars,parSpiSeg.txt" 
    self.vtVars['parsPath']             = os.path.join(*self.vtVars['parsPath'].split(","))
    self.vtVars['modelPath']            = self.vtVars['vissimPath']  + ",models,modelSpine" 
    self.vtVars['modelPath']            = os.path.join(*self.vtVars['modelPath'].split(","))
    self.vtVars['imgType']              = ".nrrd"
    self.vtVars['vtID']                 = "7"
    vtMethods   = ["Vertebra","Vertebral body","Vertebral endplates","Vertebral endplates outside","Vertebral endplates inside"]
    vtMethodsegT= [",Default",",SVB"   ,",SVBSr"    , ",SVBSrSh"    , ",SVBSrMd"]
    vtMethodsgT = ["S.seg"   ,"SVB.seg","SVBSr.seg" , "SVBSrSh.seg" , "SVBSrMd.seg"]
    self.vtVars['vtMethodID']           = "0"
    self.vtVars['segT']                 = vtMethodsegT[int(self.vtVars['vtMethodID'])] 
    self.vtVars['sgT']                  = vtMethodsgT[int(self.vtVars['vtMethodID'])] 
    self.vtVars['Styp']                 = "Ct"  
    self.vtVars['vtPtsLigDir']          =  ",PtsLig"
    self.vtVars['vtPtsLigSuff']         =  "Lp"
    self.vtVars['vtPtsMusDir']          =  ",PtsMus"
    self.vtVars['vtPtsMusSuff']         =  "Mp"
    self.vtVars['modelCropImgLigPtsTmpPath'] =   self.vtVars['modelPath'] +"," +self.vtVars['vtPtsLigDir']+","+self.vtVars['Styp']
    self.vtVars['modelCropImgLigPtsTmpPath'] =   os.path.join(*self.vtVars['modelCropImgLigPtsTmpPath'].split(","))  
    self.vtVars['modelCropImgMusPtsTmpPath'] =   self.vtVars['modelPath'] +"," +self.vtVars['vtPtsMusDir']+","+self.vtVars['Styp']
    self.vtVars['modelCropImgMusPtsTmpPath'] =   os.path.join(*self.vtVars['modelCropImgMusPtsTmpPath'].split(","))  
    self.vtVars['subVarsTemplateFnm']        = self.vtVars['modelPath'] +","+self.vtVars['vtPtsLigDir']+",simPackSubVars.txt"  
    self.vtVars['subVarsTemplateFnm']        =   os.path.join(*self.vtVars['subVarsTemplateFnm'].split(","))  
	
    self.vtVars['dispViewTxt']               = "Yellow"
    self.vtVars['dispViewID']                = "7"
    self.vtVars['downSz']                    = "160"
    self.vtVars['winOS']                     = "False"
    self.vtVars['ligChk']                    = "True"
    self.vtVars['musChk']                    = "True"
    self.vtVars['hrChk']                     = "True"
    self.vtVars['segNodeCoM']                = "[ 0 , 0 , 0 ]"
    self.vtVars['croppingLength']            = "[ 80 , 80 , 60 ]"
    self.vtVars['RSxyz']                     = "[ 0.5, 0.5 , 0.5 ]"
    # change the model type from vtk to stl 
    msn=slicer.vtkMRMLModelStorageNode()
    msn.SetDefaultWriteFileExtension('stl')
    slicer.mrmlScene.AddDefaultNode(msn)

    #   for key, value in self.vtVars.iteritems():
    #       if ("Path" in key) or ("path" in key):
    #          self.vtVars[key] = self.vtVars[key].replace('/', '\\')    
            #endif
		#endfor
	#endif
    if sys.platform == 'win32':
           self.vtVars['elastixBinPath']       = os.path.join(self.ElastixBinFolder, "elastix.exe")
           self.vtVars['transformixBinPath']   = os.path.join(self.ElastixBinFolder, "transformix.exe")
    #endif   

    self.checkVisSimTools(self.vtVars)
    return self.vtVars
    
  # Check if image is valid
  def hasImageData(self,inputVolumeNode):
    #check input image 
    if not inputVolumeNode:
      logging.debug('hasImageData failed: no input volume node')
      return False
    if inputVolumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in input volume node')
      return False
    return True
  #enddef

  # set resampling option
  def setLigChk(self,ligChk,nodes):
        self.vtVars['ligChk'] = str(ligChk)
        #self.vtPtsLigTxt     = "Ligaments points"     
        #self.vtVars['vtPtsLigDir']     = "PtsLig" 
        #self.vtVars['vtPtsLigSuff']    = "Lp"
        ligName = "_LigPts_C" # + self.vtVars['vtID'] 
        # Set unvisible 
        for f in nodes:
            if (ligName in f.GetName() ):
               f.GetDisplayNode().SetVisibility(self.s2b(self.vtVars['ligChk']))
               print("Ligaments points detection:" + str(ligChk))
               #break
            #endif
        #endfor
  #enddef

  # set resampling option
  def setMusChk(self,musChk,nodes):
        self.vtVars['musChk'] = str(musChk) #this return "True"
        #self.vtPtsMusTxt     = "Muscles points"     
        #self.vtVars['vtPtsMusDir']     = "PtsMus" 
        #self.vtVars['vtPtsMusSuff']    = "Mp"
        musName = "_MusPts_C"  #+self.vtVars['vtID']
        # Set unvisible 
        for f in nodes:
            if (musName in f.GetName() ):
               f.GetDisplayNode().SetVisibility(self.s2b(self.vtVars['musChk']))
               print("Muscle points detection:" + str(self.s2b(self.vtVars['musChk'])))      
            #endif
        #endfor

  #enddef

  # set resampling option
  def setHrChk(self,hrChk):
      self.vtVars['hrChk'] = str(hrChk)
  #enddef
  
  def setmrChk(self,mrChk):
      self.mrChk = mrChk
      if mrChk:       
            self.vtVars['Styp']="Mr"
      else:
            self.vtVars['Styp']="Ct"    
      #endif
  #enddef    

  def setVtID(self,idx,inputVolumeNode , inputFiducialNode):
      self.vtVars['vtID']=str(idx)
      print(self.vtVars['vtID']+ " is selected")
      self.inputVolumeNode = inputVolumeNode
      self.inputFiducialNode = inputFiducialNode 
      #remove old points 
        
      # Check if a markup node exists
      newNode = True
      print(self.inputVolumeNode.GetName()+"_vtLocations")
      self.inputFiducialNode = None
      nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
      for f in nodes:
          if ((f.GetName() == self.inputVolumeNode.GetName()+"_vtLocations") ):
             #replace  current 
             print("inputFiducialNode exist")
             self.inputFiducialNode = f  
             newNode= False
            #endif
      #endfor      
      if not (self.inputFiducialNode is None):
         ls = slicer.modules.markups.logic()
         ls.SetActiveListID(self.inputFiducialNode)
         print(ls.GetActiveListID())
         noPts = self.inputFiducialNode.GetNumberOfFiducials() 
         newFid= True
         for j in range (0, noPts):
             if self.inputFiducialNode.GetNthFiducialLabel(j)==("C"+self.vtVars['vtID']) :
                newFid= False 
                print("C"+self.vtVars['vtID'] +" exist, removing old point at: " +str(j))
                #get the new location
                self.inputFiducialNode.RemoveMarkup(j)      
             #endif
         #endfor
      else:
         print("inputFiducialNode does not exist")

         
      #endif  
      
  #enddef
  
  # check if vertebra location is available
  def setVtIDfromEdt(self,point,vtID):
        # no external call
        #print("no external call, point= " + point)
        self.vtVars['vtID'] = str(vtID)
        isExternalCall = False
        print("point changed,  " + str(vtID) + " is selected")      
        #TODO: add option to use point from text for cropping   
        return isExternalCall     
  #enddef

  def setVtMethodID(self,idx,vtVars):
      #Available methods
      vtMethods   = ["Vertebra","Vertebral body","Vertebral endplates","Vertebral endplates outside","Vertebral endplates inside"]
      vtMethodsegT= [",Default",",SVB"   ,",SVBSr"    , ",SVBSrSh"    , ",SVBSrMd"]
      vtMethodsgT = ["S.seg"   ,"SVB.seg","SVBSr.seg" , "SVBSrSh.seg" , "SVBSrMd.seg"]

      vtVars['vtMethodID'] = str(idx)
      vtVars['segT']       = vtMethodsegT[idx]
      vtVars['sgT']        = vtMethodsgT[idx]  
      """
      if   idx==0:
           vtVars['segT'] = ",Default"    
           vtVars['sgT']  ="S.seg" 
      elif idx==1:
           vtVars['segT'] = ",SVB" 
           vtVars['sgT']  = "SVB.seg"
      elif idx==2:
           vtVars['segT'] = ",SVBSr" 
           vtVars['sgT']  ="SVBSr.seg"         
      elif idx==3:
           vtVars['segT'] = ",SVBSrSh" 
           vtVars['sgT']  ="SVBSrSh.seg"         
      elif idx==4:
           vtVars['segT'] = ",SVBSrMd" 
           vtVars['sgT']  ="SVBSrMd.seg"         
      print(vtMethodTxt + " method is selected")
      #endif         
      """ 
      return vtVars    
  #enddef


  def locateVertebra(self, inputVolumeNode, vtID,  inputPointEdt):
        # redefine to be used in the logic class.
        self.inputVolumeNode   = inputVolumeNode
        self.inputPointEdt     = inputPointEdt  
        self.vtVars['vtID']= str(vtID)
        print(" ..... getting vertebra location in the input image")  
        # Reset global point label
        self.inputPoint = [0,0,0]
        self.inputPointEdt.setText(str(self.inputPoint))
        # Check if a volume is selected
        if not self.inputVolumeNode:
           print >> sys.stderr, "You need to pick a input volume first before locating vertebra."
           return -1
        #endif
        
        #  Display Sagittal during locating the vertebra
        disp_logic = slicer.app.layoutManager().sliceWidget(self.vtVars['dispViewTxt']).sliceLogic()
        disp_cn = disp_logic.GetSliceCompositeNode()
        disp_cn.SetBackgroundVolumeID(self.inputVolumeNode.GetID())
        lm = slicer.app.layoutManager()
        #slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpGreenSliceView 8
        #slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpYellowSliceView 7       
        lm.setLayout(int(self.vtVars['dispViewID']))
        # Fit slice to window
        sliceNodes = slicer.util.getNodes('vtkMRMLSliceNode*')
        layoutManager = slicer.app.layoutManager()
        for sliceNode in sliceNodes.values():
            sliceWidget = layoutManager.sliceWidget(sliceNode.GetLayoutName())
            if sliceWidget:
                sliceWidget.sliceLogic().FitSliceToAll()
            #endif
        #endfor
       
        #TODO: remove this part, it is already implemented in setVtID
        # Check if a markup node exists
        newNode = True
        nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for f in nodes:
            if ((f.GetName() == inputVolumeNode.GetName()+"_vtLocations") ):
                #replace  current 
                self.inputFiducialNode = f  
                newNode= False
            #endif
        #endfor
        
        #this is implemented in setVtID
        if newNode:
           self.inputFiducialNode = slicer.vtkMRMLMarkupsFiducialNode()
           self.inputFiducialNode.SetName(inputVolumeNode.GetName()+"_vtLocations")
           slicer.mrmlScene.AddNode(self.inputFiducialNode)
        #endif   
        self.inputFiducialNode.GetDisplayNode().SetTextScale(2)
        self.inputFiducialNode.GetDisplayNode().SetSelectedColor(1,0,0)           

        # Start Fiducial Placement Mode in Slicer for one node only
        placeModePersistance = 0 # one node only
        slicer.modules.markups.logic().StartPlaceMode(placeModePersistance)

        # Observe scene for updates
        self.addObs = self.inputFiducialNode.AddObserver(self.inputFiducialNode.MarkupAddedEvent,   self.onInputFiducialNodeMarkupAddedEvent)
        self.modObs = self.inputFiducialNode.AddObserver(self.inputFiducialNode.PointModifiedEvent, self.onInputFiducialNodePointModifiedEvent)
        self.rmvObs = self.inputFiducialNode.AddObserver(self.inputFiducialNode.MarkupRemovedEvent, self.onInputFiducialNodeMarkupRemovedEvent)

  #enddef

  def onInputFiducialNodeMarkupAddedEvent(self, caller, event):
        # it seems this action happened after adding new fiducial
        print("Fiducial adding event!")
        #remove previous observer
        caller.RemoveObserver(self.addObs)
        noPts = caller.GetNumberOfFiducials() 
        rasPt = [0,0,0] 
        caller.SetNthFiducialLabel(noPts-1, "C"+self.vtVars['vtID'])
        caller.GetNthFiducialPosition(noPts-1,rasPt)
        self.inputPoint = self.ptRAS2IJK(caller, noPts-1, self.inputVolumeNode)
        self.inputPointEdt.setText(str(self.inputPoint))
        #self.inputPointEdt.setText(str(rasPt))
        print(" ..... vertebra location RAS: " + str(rasPt))  
        print(" ..... vertebra location in the fixed image set to: " + str(self.inputPoint))
  #enddef
  
  
  #--------------------------------------------------------------------------------------------
  #    RAS to  IJK Event
  #--------------------------------------------------------------------------------------------
  # The fiducial point saved in RAS, we need to convert to IJK
  #  more info in our wiki 
  def onInputFiducialNodePointModifiedEvent(self, caller, event):
      print("Fiducial modified event!")
      #caller.RemoveObserver(self.modObs)
      # get the new IJK position and display it
      rasPt = [0,0,0] 
      i = caller.GetAttribute('Markups.MovingMarkupIndex')
      if not (i is None):
         i=int(i)
         caller.GetNthFiducialPosition(i,rasPt)
         #self.inputPointEdt.setText(str(rasPt))
         self.inputPoint = self.ptRAS2IJK(caller, i, self.inputVolumeNode)
         self.inputPointEdt.setText(str(self.inputPoint))

      #endif   
  #enddef

  def onInputFiducialNodeMarkupRemovedEvent(self, caller, event):
      print("Fiducial removed event!")
      caller.RemoveObserver(self.rmvObs)
      #i = caller.GetNumberOfFiducials()-1
      #print("number of rmaining fiducials: " + str(i))
      
  def openResultsFolder(self,outputPath):
      if outputPath is None:
         outputPath =self.vtVars['outputPath'] 
      #endif
      if sys.platform == 'darwin':
        os.system('open ' + outputPath)
      elif sys.platform == 'linux2':
        os.system('xdg-open ' + outputPath)
      elif sys.platform == 'win32':
        s = 'explorer  ' + outputPath
        s = s.replace('/', '\\')        
        os.system(s)
      #endif
  #enddef
  
  #--------------------------------------------------------------------------------------------
  #                        run elastix
  #--------------------------------------------------------------------------------------------      
  def runElastix(self, elastixBinPath, fixed, moving, output, parameters, verbose, line):
       print ("************  Compute the Transform **********************")
       Cmd =elastixBinPath + " -f " + fixed +" -m "+ moving  + " -out " + output  + " -p " + parameters + verbose
       print("Executing: " + Cmd)
       #cTI=os.system(cmd)
       si = None
       if sys.platform == 'win32':
         si = subprocess.STARTUPINFO()
         si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
       #endif  
       cTI = subprocess.call(Cmd , shell = (sys.platform == 'linux2') , startupinfo=si )
       errStr="elastix error at line"+ line +", check the log files"
       self.chkElxER(cTI,errStr) # Check if errors happen during elastix execution
       return cTI
  #enddef

  #--------------------------------------------------------------------------------------------
  #                        run transformix
  #--------------------------------------------------------------------------------------------      
  def runTransformix(self,transformixBinPath, img, output, parameters, verbose, line):
      print ("************  Apply transform **********************")
      si = None
      if sys.platform == 'win32':
         si = subprocess.STARTUPINFO()
         si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
      #endif  		
      # Apply the transformation to the segmentation image:
      Cmd = transformixBinPath + " -in " + img + " -out " + output  + " -tp " + parameters +" -def all " +verbose
      print("Executing... " + str(Cmd))
      #cTS=os.system(Cmd)
      cTS = subprocess.call(Cmd , shell = (sys.platform == 'linux2') , startupinfo=si )
      errStr="transformix error at line"+ line +", check the log files"
      self.chkElxER(cTS,errStr) # Check if errors happen during elastix execution
      return cTS
  #enddef

  #--------------------------------------------------------------------------------------------
  #                       Cropping Process  
  #--------------------------------------------------------------------------------------------
  # Using the location as a center point, we cropp around it using the defined cropLength 
  def runCropping(self, inputVolume, point, vtIDt,croppingLengthT, samplingLengthT, hrChkT):
        print("================= Begin cropping ... =====================")
        # Create a temporary node as workaround for bad path or filename 
        #TODO: create a temp folder and remove temp node before display
        vtID = int(vtIDt)
        croppingLength =   self.t2v(croppingLengthT)
        samplingLength =   self.t2v(samplingLengthT)
        hrChk          =   self.s2b(hrChkT)
        
        print("Vertebra "+str(vtID)+ " location: " + str(point) + "   cropping length: " + str(croppingLength) )
        #Remove old cropping node
        nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        for f in nodes:
            if ("inputimage_crop" in f.GetName()):
                slicer.mrmlScene.RemoveNode(f )
            #endif
        #endfor
        # resampling spacing  
        self.RSx= samplingLength[0] ; self.RSy=samplingLength[1];     self.RSz= samplingLength[2]

        #Get input image information 
        spacing = inputVolume.GetSpacing()
        imgData = inputVolume.GetImageData()
        dimensions = imgData.GetDimensions()
        
        # compute cropping bounds from image information and cropping parameters
        croppingBounds = [[0,0,0],[0,0,0]];   size = [0,0,0];    lower = [0,0,0] ;     upper = [0,0,0]
        for i in range(0,3):
            size[i] = int((croppingLength[i]/spacing[i])/2)
            lower[i] = int(point[i]) - int(size[i])
            upper[i] = dimensions[i] - int(point[i]+size[i])
            # Check if calculated boundaries exceed image dimensions
            if lower[i] < 0:
                    lower[i] = 0
            #endif        
            if upper[i] > dimensions[i]:
                   upper[i] = int(dimensions[i])
            #endif
        #endfor   
        croppingBounds = [lower,upper]
        # Call SimpleITK CropImageFilter
        print("Cropping with " + str(croppingBounds[0]) + " and " + str(croppingBounds[1]) + ".")
        #self.inputCropPath = "bla blaa blaaa"

        inputImage = sitkUtils.PullVolumeFromSlicer(inputVolume.GetID())
        cropper = sitkUtils.sitk.CropImageFilter()
        croppedImage = cropper.Execute(inputImage, croppingBounds[0], croppingBounds[1])          
        nodeName = str(inputVolume.GetName()) +"_C"+str(vtID) +"_crop"
        inputCropPath = os.path.splitext(inputVolume.GetStorageNode().GetFileName())[0] +"_C"+str(vtID) +"_crop.nrrd"
        # Make a node with cropped image 
        sitkUtils.PushVolumeToSlicer(croppedImage, None, nodeName , 'vtkMRMLScalarVolumeNode' )
        crNodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        for f in crNodes:
            if nodeName in f.GetName():
                 f.SetName(nodeName) 
                 break         
            #endif
        #endfor  
        #tmpName= self.vtVars['vissimPath']+"/inputImage" +self.vtVars['imgType']
        #slicer.util.saveNode( inputVolumeNode, tmpName)
        #[success, inputVolume] = slicer.util.loadVolume(tmpName, returnNode=True)    
        #inputVolume.SetName("inputImage")

        croppedNode = slicer.util.getNode(nodeName)
        
        #inputCropPath = os.path.splitext(inputVolume.GetStorageNode().GetFileName())[0] +"_C"+str(vtID) +"_crop.nrrd"                                  
        #inputCropPath = self.vtVars['vissimPath']+"/inputImage"  +"_C"+str(vtID) +"_crop.nrrd"                                  
        inputCropPath = self.vtVars['vissimPath']+",inputImage"  +"_C"+str(vtID) +"_crop.nrrd"                                  
        print(inputCropPath.split(","))
        inputCropPath = os.path.join(*inputCropPath.split(","))                         
        print("cropped:     "+inputCropPath)
        slicer.util.saveNode( croppedNode, inputCropPath)
        #-------------------------------------------------------
        # Resampling: this produces better looking models  
        #-------------------------------------------------------
        if hrChk:
           #Run slicer cli module: resample scalar volume
           #inputCropIsoPath = os.path.splitext(inputVolume.GetStorageNode().GetFileName())[0] +"_C"+str(vtID) +"_crop_iso.nrrd"  
           inputCropIsoPath = self.vtVars['vissimPath']+",inputImage"  +"_C"+str(vtID) +"_crop_iso.nrrd"                                  
           inputCropIsoPath = os.path.join(*inputCropIsoPath.split(","))                         
           print("iso cropped: "+inputCropIsoPath)
           resampleSpacing = " ["+ str(self.RSx) + "," + str(self.RSy) + "," + str(self.RSz) + "] "
           #TODO: Get Slicer PATH
           SlicerPath =os.path.abspath(os.path.join(os.path.abspath(os.path.join(os.sys.executable, os.pardir)), os.pardir))
           SlicerBinPath =   os.path.join(SlicerPath,"Slicer")  
           ResampleBinPath = SlicerPath +",lib,Slicer-4.10,cli-modules,ResampleScalarVolume"
           ResampleBinPath =  os.path.join(*ResampleBinPath.split(",")) 		   
           resamplingCommand = SlicerBinPath + " --launch " + ResampleBinPath   
           si = None 
           if sys.platform == 'win32':
              #note: in windows, no need to use --launch
              resamplingCommand = ResampleBinPath + ".exe"
              print(os.path.getsize(resamplingCommand))
              si = subprocess.STARTUPINFO()
              si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		   #endif

           cmdPars = " -i linear -s "+ resampleSpacing + inputCropPath +" "+inputCropIsoPath  
           Cmd = resamplingCommand  + cmdPars
           print("Executing ... "+Cmd)
           #os.system(cmd)
           subprocess.call(Cmd , shell = (sys.platform == 'linux2') , startupinfo=si )
           #inputCropPath = inputCropIsoPath
           print(" Cropping and resampling are done !!! ")
        #endif

        #slicer.mrmlScene.RemoveNode(croppedNode )

        #inputCropPath    = inputCropPath.strip("'")
        print(" Cropped image is saved in : [%s]" % inputCropPath)
        print(" Cropping is done !!! ")          

        return inputCropPath
  
  #===========================================================================================
  #                       Segmentation Process 
  #--------------------------------------------------------------------------------------------        
  # This method perform the atlas segementation steps
  def run(self, inputVolumeNode, inputFiducialNode, vtID, isExternalCall):
      #to be used fromoutside we need to do:
      # import VertebraTools
      # logic= VertebraTools.VertebraToolsLogic()
      # logic.run(with the parameters above)
        """
        Run the actual algorithm
        """
        if isExternalCall:
           print(" External call!")
           # this functionshould be changed in case of external call
           self.vtVars = self.setGlobalVariables(isExternalCall)
        else:
           print(" No external call!")
        
        vtID = int(vtID)
        print (vtID)    
   
        # set the correct models path:
		
        self.modelCropImgLigPtsPath = self.vtVars['modelCropImgLigPtsTmpPath'] +str(vtID)+self.vtVars['vtPtsLigSuff']+".fcsv"
        #self.modelCropImgLigPtsPath =  os.path.join(*self.modelCropImgLigPtsPath.split(",") )
        self.modelCropImgMusPtsPath = self.vtVars['modelCropImgMusPtsTmpPath'] + str(vtID)+self.vtVars['vtPtsMusSuff']+".fcsv"
		

        # we need to run this again in case of external call

        #endif
        modelCropPath       = self.vtVars['modelPath']+  ',Default'+",Mdl" + self.vtVars['Styp']+ str(vtID)        +self.vtVars['imgType'] 
        modelCropPath       =   os.path.join(*modelCropPath.split(","))
        print(modelCropPath.split(","))
        print(modelCropPath)
        modelCropSegPath    = self.vtVars['modelPath'] + self.vtVars['segT']+",Mdl"+self.vtVars['Styp']+ str(vtID)+ self.vtVars['sgT'] +self.vtVars['imgType'] 
        modelCropSegPath    =   os.path.join(*modelCropSegPath.split(","))


        self.hasImageData(inputVolumeNode)
        #inputVolumeNode   = inputVolumeNode
        #inputFiducialNode = inputFiducialNode
 

        # TODO: externalcall can be 0=internal, 1:test or 2=spine:
          
        logging.info('Processing started')

        if not os.path.exists(self.vtVars['outputPath']):
           os.mkdir(self.vtVars['outputPath'])      
        else:
           #only for this vertebra
           self.removeOtputsFolderContents()
        #endif
        # results paths        
        resTransPath  = os.path.join(self.vtVars['outputPath'] ,"TransformParameters.0.txt")
        resOldDefPath = os.path.join(self.vtVars['outputPath'] , "deformationField"+self.vtVars['imgType'])
        resDefPath    = os.path.join(self.vtVars['outputPath'] , inputVolumeNode.GetName()+"C"+str(vtID)+"_dFld"+self.vtVars['imgType'])
        
        #remove old result files:
        if os.path.isfile(resOldDefPath):
           os.remove(resOldDefPath) 
        if os.path.isfile(resDefPath):
           os.remove(resDefPath)
        
        # check if the model is found
        if not isfile(modelCropPath): 
            print >> sys.stderr, "ERROR: model is not found"            
            print("modelPath: " + modelCropPath)
            return False
        # endif

        inputPath = inputVolumeNode.GetStorageNode().GetFileName()
        inputFnm  = basename(os.path.splitext(inputPath)[0])    
        
        #remove old results
        resultSegNodeName    = inputVolumeNode.GetName()    + "_Seg_C"      +str(vtID)           
        resultLigPtsNodeName = inputVolumeNode.GetName()    + "_LigPts_C"   +str(vtID)
        resultMusPtsNodeName = inputVolumeNode.GetName()    + "_MusPts_C"   +str(vtID)                      
        resultTransformNodeName =  inputVolumeNode.GetName()+ "_Transform_C"+str(vtID)
        #tableNodeName =  inputVolumeNode.GetName()+ "_Table_C"+str(vtID)
        # Remove old Fiducial nodes
        nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        #for f in nodes:
        #    if ((f.GetName() == "VertebraLocationPoint") ):
        #        #slicer.mrmlScene.RemoveNode(f)
        #        # removing should be part of locating
        #        for i in range(f.GetNumberOfFiducials()):
        #            if ("C"+str(self.vtID))   in  f.GetNthFiducialLabel(i): 
        #                #f.RemoveMarkup(i)
        #            #endif
        #        #endfor
        #    #endif
            
        # Get IJK point from the fiducial to use in cropping  
        newFid= True
        for j in range (inputFiducialNode.GetNumberOfFiducials() ):
             if inputFiducialNode.GetNthFiducialLabel(j)==("C"+str(vtID)) :
                break
              #endif
        #endfor
        inputPoint = self.ptRAS2IJK(inputFiducialNode,j,inputVolumeNode)

        #Remove old results
        for node in slicer.util.getNodes():
            if ( resultLigPtsNodeName    == node): slicer.mrmlScene.RemoveNode(node) #endif
            if ( resultMusPtsNodeName    == node): slicer.mrmlScene.RemoveNode(node) #endif
            if ( resultSegNodeName       == node): slicer.mrmlScene.RemoveNode(node) #endif
            if ( resultTransformNodeName == node): slicer.mrmlScene.RemoveNode(node) #endif
        #endfor    
        #try:  slicer.mrmlScene.RemoveNode(slicer.util.getNode(resultMusPtsNodeName))
         
        # TODO: add better condition
        if  np.sum(inputPoint)== 0 :
            print("Error: select vertebra point")
            return False
        #endif  

        print ("************  Cropping  **********************")
        self.vtVars['intputCropPath'] = self.runCropping(inputVolumeNode, inputPoint, vtID ,self.vtVars['croppingLength'], self.vtVars['RSxyz'],  self.vtVars['hrChk'] )                     
        [success, croppedNode] = slicer.util.loadVolume(self.vtVars['intputCropPath'], returnNode=True)
        print(self.vtVars['intputCropPath'])
        croppedNode.SetName(inputVolumeNode.GetName()+"_C"+str(vtID)+"Crop")                                                        
        print ("************  Register model to cropped input image **********************")
        cTI = self.runElastix(self.vtVars['elastixBinPath'],self.vtVars['intputCropPath'],  modelCropPath, self.vtVars['outputPath'], self.vtVars['parsPath'], self.vtVars['noOutput'], "554")
       
		#genrates deformation field 
        cTR = self.runTransformix(self.vtVars['transformixBinPath'],modelCropPath, self.vtVars['outputPath'], resTransPath, self.vtVars['noOutput'], "556")
        # rename fthe file:
        os.rename(resOldDefPath,resDefPath)
        
        print ("************  Load deformation field Transform  **********************")
        [success, vtTransformNode] = slicer.util.loadTransform(resDefPath, returnNode = True)
        vtTransformNode.SetName(resultTransformNodeName)

        print ("************  Transform segmentation  **********************")
        print(modelCropSegPath)
        [success, vtResultSegNode] = slicer.util.loadSegmentation(modelCropSegPath, returnNode = True)
        vtResultSegNode.SetName(resultSegNodeName)
        vtResultSegNode.SetAndObserveTransformNodeID(vtTransformNode.GetID()) # movingAllMarkupNode should be loaded, the file contains all points
        slicer.vtkSlicerTransformLogic().hardenTransform(vtResultSegNode) # apply the transform
        vtResultSegNode.CreateClosedSurfaceRepresentation() 
        
        # for surfaces, do grow margin with 1 mm
        if int(self.vtVars['vtMethodID']) >1  :
           self.runMargining(vtResultSegNode,croppedNode ,1)
        #endif

        print(self.vtVars['subVarsTemplateFnm'])
        self.vtVars['subVarsFnm'] =  self.vtVars['outputPath']+"/"+ inputVolumeNode.GetName() + "_spkSubVars.txt"
        print(self.vtVars['subVarsFnm'])        
        #cR =  copyfile(self.vtVars['subVarsTemplateFnm'], self.subVarsFnm)
        if not os.path.exists(self.vtVars['subVarsFnm']):
           cR =  shutil.copy(self.vtVars['subVarsTemplateFnm'], self.vtVars['subVarsFnm'])
           print(cR)
        #endif
              
        if self.s2b(self.vtVars['ligChk']):            
           print ("************  Transform Ligaments Points **********************")
           modelCropImgLigPtsPath = self.vtVars['modelPath'] +","+self.vtVars['vtPtsLigDir']+","+self.vtVars['Styp']+ str(vtID)+self.vtVars['vtPtsLigSuff']+".fcsv"
           modelCropImgLigPtsPath = os.path.join(*modelCropImgLigPtsPath.split(","))
           print(self.modelCropImgLigPtsPath)
           [success, vtResultLigPtsNode] = slicer.util.loadMarkupsFiducialList  (modelCropImgLigPtsPath, returnNode = True)
           vtResultLigPtsNode.GetDisplayNode().SetTextScale(1)
           vtResultLigPtsNode.GetDisplayNode().SetSelectedColor(1,0,0)           
           vtResultLigPtsNode.SetName(resultLigPtsNodeName)

           vtResultLigPtsNode.SetAndObserveTransformNodeID(vtTransformNode.GetID()) # movingAllMarkupNode should be loaded, the file contains all points
           slicer.vtkSlicerTransformLogic().hardenTransform(vtResultLigPtsNode) # apply the transform
           # needed in extract scaled model
           self.vtResultLigPtsNode = vtResultLigPtsNode
       
        #endif 

        if self.s2b(self.vtVars['musChk']):
           print ("************  Transform Muscles Points **********************")
           modelCropImgMusPtsPath = self.vtVars['modelPath']+","+self.vtVars['vtPtsMusDir']+","+self.vtVars['Styp']+ str(vtID)+self.vtVars['vtPtsMusSuff']+".fcsv"
           modelCropImgMusPtsPath = os.path.join(*modelCropImgMusPtsPath.split(","))
           print(self.modelCropImgMusPtsPath)
           [success, vtResultMusPtsNode] = slicer.util.loadMarkupsFiducialList  (modelCropImgMusPtsPath, returnNode = True)
           vtResultMusPtsNode.GetDisplayNode().SetTextScale(1)
           vtResultMusPtsNode.GetDisplayNode().SetSelectedColor(0,0,1)           
           vtResultMusPtsNode.SetName(resultMusPtsNodeName)

           vtResultMusPtsNode.SetAndObserveTransformNodeID(vtTransformNode.GetID()) # movingAllMarkupNode should be loaded, the file contains all points
           slicer.vtkSlicerTransformLogic().hardenTransform(vtResultMusPtsNode) # apply the transform
           # needed in extract scaled model
           self.vtResultMusPtsNode = vtResultMusPtsNode

        #endif 
        
        #remove temporary nodes
        #slicer.mrmlScene.RemoveNode(self.resImgPtsNode )
          
        # Display the result if no error
        # Clear vertebra location labels
        if  (cTI==0) and (cTR==0):
             # change the model type from vtk to stl 
             msn=slicer.vtkMRMLModelStorageNode()
             msn.SetDefaultWriteFileExtension('stl')
             slicer.mrmlScene.AddDefaultNode(msn)

             print("display result")
             self.dispVolume(inputVolumeNode)
        
             print("get vertebra information")
             tableName =  inputVolumeNode.GetName()+"_tbl"
             # create only if it does not exist
             try:
                 resultsTableNode =  slicer.util.getNode(tableName)
             except:             
                 resultsTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode")
                 resultsTableNode.SetName(tableName)
                 resultsTableNode.AddEmptyRow()    
                 resultsTableNode.GetTable().GetColumn(0).SetName("Vertebra")
                 resultsTableNode.AddColumn()
                 resultsTableNode.GetTable().GetColumn(1).SetName("Volume mm3")
                 resultsTableNode.AddColumn()
                 resultsTableNode.GetTable().GetColumn(2).SetName("CoM X")
                 resultsTableNode.AddColumn()
                 resultsTableNode.GetTable().GetColumn(3).SetName("CoM Y")
                 resultsTableNode.AddColumn()
                 resultsTableNode.GetTable().GetColumn(4).SetName("CoM Z")
             #endif
                     
             resultsTableNode = self. getVertebraInfo( vtResultSegNode, croppedNode, vtID, resultsTableNode)
        
             resultsTableNode.RemoveRow(resultsTableNode.GetNumberOfRows())   
             #segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
             #segStatLogic.showTable(resultsTableNode)
             slicer.app.layoutManager().setLayout( slicer.modules.tables.logic().GetLayoutWithTable(slicer.app.layoutManager().layout))
             slicer.app.applicationLogic().GetSelectionNode().SetActiveTableID(resultsTableNode.GetID())
             slicer.app.applicationLogic().PropagateTableSelection()
             
             
        else:
            print("error happened during segmentation ")
        #endif
        
        #Remove temporary nodes:
        os.remove(self.vtVars['intputCropPath'])     
        if not  isExternalCall:     
            slicer.mrmlScene.RemoveNode(croppedNode )
        #endif
        
        #remove the temprary loaded labelmap  
        #slicer.mrmlScene.RemoveNode(self.resultNode )
        

        self.removeOldFiles(self.vtVars['outputPath'])                            
        print("================= vertebra analysis is complete  =====================")
        logging.info('Processing completed')
        # needed in extract scaled model
        self.vtResultSegNode = vtResultSegNode
        return True
    #enddef
 
  #--------------------------------------------------------------------------------------------
  #                       Check Elastix error
  #--------------------------------------------------------------------------------------------
  # This method checks if errors happen during elastix execution
  def chkElxER(self,c, s):
        if c>0:
           qt.QMessageBox.critical(slicer.util.mainWindow(),'segmentation', s)
           print(s)  
           return False
        else: 
            print("done !!!")
        #endif
 #enddef 
  
  # segmenteditor effect on the resulted segmentations 
  # this function is called by functions like doSmoothing and doMargining
  def getSegmentationEditor(self,segNode,masterNode):
            # Create segment editor to get access to effects
           segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
           segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
           segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
           segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
           segmentEditorWidget.setSegmentationNode(segNode)
           segmentEditorWidget.setMasterVolumeNode(masterNode)
           return segmentEditorWidget, segmentEditorNode

  # smoothing segmentation effect    
  #TODO: add more options   
  def runSmoothing(self,segNode,masterNode,KernelSizeMm):       
           # Smoothing
           [segEditorW,segEditorN]= self.getSegmentationEditor(segNode,masterNode)               
           for i in range (0,segNode.GetSegmentation().GetNumberOfSegments()):
               segmentID = segNode.GetSegmentation().GetNthSegmentID(i)
               segEditorW.setActiveEffectByName("Smoothing")
               segEditorW.setCurrentSegmentID(segmentID)
               effect = segEditorW.activeEffect()
               effect.setParameter("SmoothingMethod", "MEDIAN")
               effect.setParameter("KernelSizeMm", KernelSizeMm)
               effect.self().onApply()
           #endfor
           # Clean up
           segEditorW = None
           slicer.mrmlScene.RemoveNode(segEditorN)
  #enddef

  # Margin segmentation effect
  # MarginSizeMm>0 Grow, else Shrink          
  def runMargining(self,segNode,masterNode,MarginSizeMm):
           #Dilation and Eroding
           [segEditorW,segEditorN]= self.getSegmentationEditor(segNode,masterNode)               
           for i in range (0,segNode.GetSegmentation().GetNumberOfSegments()):
               segmentID = segNode.GetSegmentation().GetNthSegmentID(i)
               segEditorW.setActiveEffectByName("Margin")
               segEditorW.setCurrentSegmentID(segmentID)
               effect = segEditorW.activeEffect()
               effect.setParameter("MarginSizeMm", MarginSizeMm) 
               effect.self().onApply()
           #endfor
           # Clean up
           segEditorW = None
           slicer.mrmlScene.RemoveNode(segEditorN)
  #enddef

  #--------------------------------------------------------------------------------------------
  #                        Calculate center of mass and volume of a vertebra
  #--------------------------------------------------------------------------------------------
  def getVertebraInfo(self, segNode, masterNode, vtID, resultsTableNode):
        segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
        segStatLogic.getParameterNode().SetParameter("Segmentation", segNode.GetID())
        segStatLogic.getParameterNode().SetParameter("ScalarVolume", masterNode.GetID())
        segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.enabled","False")
        segStatLogic.getParameterNode().SetParameter("ScalarVolumeSegmentStatisticsPlugin.voxel_count.enabled","False")
        segStatLogic.computeStatistics()
        
        #TODO:
        #remove old rows for same vertebra
        for i in range (resultsTableNode.GetNumberOfRows()):
            if "C"+str(vtID) == resultsTableNode.GetCellText(i,0):
               print( "C"+str(vtID) + " tale row exists, old values will be removed.") 
               resultsTableNode.RemoveRow(i)   
        #endif
         
        #export to temporary table then copy to the final table
        resultsTmpTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode")
        resultsTmpTableNode.SetName("tmpTable")
        segStatLogic.exportToTable(resultsTmpTableNode)
        idx = resultsTableNode.GetNumberOfRows()-1
        resultsTableNode.AddEmptyRow()    
        resultsTableNode.SetCellText(idx,0,"C"+str(vtID))                          # vertebra
        resultsTableNode.SetCellText(idx,1, resultsTmpTableNode.GetCellText(0,1) ) # volume size
        # if this is C7 compute center of mass        
        if (vtID ==7) and(self.vtVars['vtMethodID']== "0"): # for testing
            segID = segNode.GetSegmentation().GetSegmentIdBySegmentName("C"+str(vtID))
            modelNode = segNode.GetClosedSurfaceRepresentation(segID)
            com = vtk.vtkCenterOfMass(); com.SetInputData(modelNode);   com.Update()
            segNodeCoM = com.GetCenter()
            resultsTableNode.SetCellText(idx,2,str(segNodeCoM[0])) 
            resultsTableNode.SetCellText(idx,3,str(segNodeCoM[1])) 
            resultsTableNode.SetCellText(idx,4,str(segNodeCoM[2]))
            self.vtVars['segNodeCoM']=str(segNodeCoM)
        #endif
        slicer.mrmlScene.RemoveNode(resultsTmpTableNode)
        print("Measurements are completed !!! ")
        return resultsTableNode
  #enddef


  #convert dictonary text to vector
  def t2v(self,txt):
      vector = [0,0,0]
      print(txt)
      t = txt.strip("]").strip("[").strip("(").strip(")")
      t = t.split(",")
      for i in range(3):
          vector[i] =float(t[i])
      return vector 
  #enddef
   
  #--------------------------------------------------------------------------------------------
  #                        Calculate length and volume of scalas
  #--------------------------------------------------------------------------------------------
  # can be called externally 
  # input is a model and C7com
  def extractScaledModel(self,inputNode,C7com,subVarsFnm):
        # we can call with model or points nodes
        #C7comPt = C7com 
        C7comPt = self.t2v(C7com)
        
        print("================= Preparing model for simulation  =====================")
        if (C7comPt ==[0.0,0.0,0.0]): # for C7
            print("C7 center of mass is missing, no output ...!")
            return -1       
        #endif
             
        print("Center of Mass" + str(C7comPt) )
        #change model type to stl
        msn=slicer.vtkMRMLModelStorageNode()
        msn.SetDefaultWriteFileExtension('stl')
        slicer.mrmlScene.AddDefaultNode(msn)

        # We need Vertebra 7 location  
        # create a new transform  
        mm2mTransfromNode = slicer.vtkMRMLLinearTransformNode()
        mm2mTransfromNode.SetName("mm2mTransform")
        #self.vtCOMLbl.setText("C7 Center of Mass= " +   "%.4f " % C7CoM[0] +" , "+  "%.4f" % C7CoM[1] +" , "+  "%.4f" % C7CoM[2])           

        #Add Scaling
        mm = mm2mTransfromNode.GetMatrixTransformToParent()
        mm.SetElement(0,0,0.001);      mm.SetElement(1,1,0.001);   mm.SetElement(2,2,0.001)       
        mm2mTransfromNode.SetMatrixTransformToParent(mm)

        # Add Scaled translation          
        d = -1000.0
        mm.SetElement(0,3,C7comPt[0]/d) ;  mm.SetElement(1,3,C7comPt[1]/d); mm.SetElement(2,3, C7comPt[2]/d)
        mm2mTransfromNode.SetMatrixTransformToParent(mm)

        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        # Clone the input model to create a scaled node
        itemIDToClone = shNode.GetItemByDataNode(inputNode)
        clonedItemID = slicer.modules.subjecthierarchy.logic().CloneSubjectHierarchyItem(shNode, itemIDToClone)
        inputNodeOut = shNode.GetItemDataNode(clonedItemID)
        inputNodeOut.SetName(inputNode.GetName()+"_scaled")
 
        #Apply transform to the inputnode            
        inputNodeOut.SetAndObserveTransformNodeID(mm2mTransfromNode.GetID())
        slicer.vtkSlicerTransformLogic().hardenTransform(inputNodeOut)
           
        # check if a model    
        if inputNode.GetClassName() == "vtkMRMLSegmentationNode":
           # convert segmentation to a model
           outputModelHNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelHierarchyNode')
           slicer.modules.segmentations.logic().ExportAllSegmentsToModelHierarchy(inputNodeOut, outputModelHNode)
           #save scaled model
           msn=slicer.vtkMRMLModelStorageNode()
           msn.SetDefaultWriteFileExtension('stl')
           slicer.mrmlScene.AddDefaultNode(msn)
           #save all segments as STL 
           # TODO: test on endplates
           for i in range (0, outputModelHNode.GetNumberOfChildrenNodes()): 
               #outputModelNode = outputModelHNode.GetNthChildNode(0).GetModelNode()
               outputModelNode = outputModelHNode.GetNthChildNode(i).GetModelNode()
               fnm  = self.vtVars['outputPath']  + "/"+inputNode.GetName()+"_"+outputModelNode.GetName()+"_scaled.stl"
               sR = slicer.util.saveNode(outputModelNode, fnm )       
               print(sR)
               print(fnm)
           #endfor
           print("Model is scaled and translated to center of mass !!! ")

        elif inputNode.GetClassName() == "vtkMRMLMarkupsFiducialNode":
               fnm  = self.vtVars['outputPath']  + "/"+inputNodeOut.GetName()+".fcsv"
               sR = slicer.util.saveNode(inputNodeOut, fnm )                   
               print(sR)
               print(fnm)
               print("points are scaled and translated to center of mass !!! ")
               #TODO: copy the template file if it does not exist:
               #TODO: replace removing output folder by removing specific contents
               print(subVarsFnm)
               #spkFile= open(self.subVarsFnm ,"w+")
               spkFile= open(subVarsFnm ,"r")
               #loop through the file line by line 
               content = spkFile.readlines()
               content = [x.strip() for x in content] 
               spkFile.close()

               #The idea is read the content to a new file                                    
               os.remove(subVarsFnm)
               print("Number of Points : " + str(inputNodeOut.GetNumberOfFiducials()))
               for i in range (0,inputNodeOut.GetNumberOfFiducials()):# ptsNodesNo):
                   ras=[0,0,0]
                   inputNodeOut.GetNthFiducialPosition(i,ras)        
                   pName =inputNodeOut.GetNthFiducialLabel(i)
                   #Px =  '%.16E' % Decimal(ras[0]); Py =  '%.16E' % Decimal(ras[1]) ;    Pz =  '%.16E' % Decimal(ras[2])
                   Px = str(ras[0]); Py =str(ras[1]) ;    Pz = str(ras[2]); st1= " )  =  " ; st2="!  value of substitution variable"
                   PnX= pName+"_x" ; PnY= pName+"_y" ; PnZ= pName+"_z" ; sp1 =21 ;   sp2 = 24 ;              
                   l1="subvar.str  (              $_"+PnX.ljust(sp1)+ st1  + Px.ljust(sp2) +  st2
                   l2="subvar.str  (              $_"+PnY.ljust(sp1)+ st1  + Py.ljust(sp2) +  st2
                   l3="subvar.str  (              $_"+PnZ.ljust(sp1)+ st1  + Pz.ljust(sp2) +  st2
                   # find the point part in the txt file
                   j=0                  
                   while j <len(content):
                         if  pName in content[j]:
                             print(content[j])
                             content[j]   = l1
                             content[j+1] = l2
                             content[j+2] = l3
                             j = j+2
                         #endif
                         j = j+1
                    #end while
                          
               #endfor i
               spkFile= open(subVarsFnm ,"w+")
               for line in content:
                    line=line+"\n"
                    spkFile.write(line);  
                #endfor
               spkFile.close()
               print("save the text file in the output folder ")

               # loop therough the points and add them in the correct place
               
               # find current body
               # find the part of the points
               #    ! *** Intervertebral Disc                    ******   
               #    ! *** Facettes                               ******           
               #    ! *** Ligament Points C7-C6                  ******
               #    ! *** Muscle Points C7                       ******
               # Add the point in 3 rows x,y,z
               #    subvar.str  (              $_pointName_x          )  =  ''                      !  value of substitution variable
               
        else:
            print(inputNode.GetClassName() +" is not supported class ...")
            print(inputNode)
            
        self.removeOldFiles(self.vtVars['outputPath'])            
        #TODO: if markupnode write a text file compitable to simpack
        #TODO: remove nodes from scene
        #TODO: Message box, models are saved in path
  #enddef

  def exportPoints2txtFile(self,inputPoints):
      pass
      # create a template file for the input vertebra
      # loope through the points
      # add to the template file in the correct location and format
      
      
      
      
  #enddef
        
  def dispVolume(self,inputVolumeNode):
        lm = slicer.app.layoutManager();    lm.setLayout(4)
        r_logic = lm.sliceWidget("Red").sliceLogic()
        r_cn = r_logic.GetSliceCompositeNode()
        r_cn.SetBackgroundVolumeID(inputVolumeNode.GetID())
        y_logic = lm.sliceWidget("Yellow").sliceLogic()
        y_cn = y_logic.GetSliceCompositeNode()
        y_cn.SetBackgroundVolumeID(inputVolumeNode.GetID())
        g_logic = lm.sliceWidget("Green").sliceLogic()
        g_cn = g_logic.GetSliceCompositeNode()
        g_cn.SetBackgroundVolumeID(inputVolumeNode.GetID())

        #center 3D view and zoom in 3 times
        v3DDWidget = lm.threeDWidget(0)
        v3DDWidgetV = v3DDWidget.threeDView()
        v3DDWidgetV.resetFocalPoint() 
        v3DDWidgetV.zoomFactor =3
        v3DDWidgetV.zoomIn()
        v3DDWidgetV.zoomFactor =0.05 # back to default value

#------------------------------------------------------
#                  IJK to RAS  
#------------------------------------------------------
# This function convert an IJK point to RAS point 
#  input:  a point vector and volume node
#  output: a point vector                     
  def ptIJK2RAS(self,ptIJK,inputImg):
        #TODO: add option for printing                   
        # create a IJK2RAs transformation matrix 
        ijk2rasM = vtk.vtkMatrix4x4()
        inputImg.GetIJKToRASMatrix(ijk2rasM)
        ptRAS=np.zeros((len(ptIJK),3))
        ijk= ptIJK
        # create a 4 elements array to get the converted values
        ijkv=[ijk[0],ijk[1],ijk[2],1]             
        rasPt=ijk2rasM.MultiplyDoublePoint(ijkv)
        ptRAS=rasPt[0:3]
        #print("IJK= " + str(ptIJK)+ "   RAS= " + str(ptRAS))
        return  ptRAS       

#------------------------------------------------------
#                 RAS  to IJK 
#------------------------------------------------------   
# This function convert RAS ro an IJK point 
#  input:  a point vector and volume node
#  output: a point vector                     
  def ptRAS2IJK(self,ptRAS,i,inputImg): 
        #TODO: add option for printing                   
        # create a RAS2IJK transformation matrix 
        ras2ijkM = vtk.vtkMatrix4x4()
        inputImg.GetRASToIJKMatrix(ras2ijkM)       
        ras=[0,0,0]
        #i = int(i)
        print(type(i))
        ptRAS.GetNthFiducialPosition(i,ras)        
        # create a 4 elements array to get the converted values
        rasv=[ras[0],ras[1],ras[2],1]             
        ptIJKf=np.zeros(3);
        ijkPt=ras2ijkM.MultiplyPoint(rasv)
        ptIJKf[0]=ijkPt[0];ptIJKf [1]=ijkPt[1];ptIJKf [2]=ijkPt[2];
        ptIJK = ptIJKf.astype(np.int64)
        #print("RAS= " + str(ras)+ "   IJK= " + str(ptIJK))
        return  ptIJK       
 
  def removeOldFiles(self, outputPath):
      #remove old files if exist
      try:    
          if os.path.isdir(outputPath.strip()): 
             print("removing old output folder!")
             #shutil.rmtree(self.vtVars['outputPath'])
             resfiles = os.listdir(outputPath) 
             oPath= outputPath +"/"
             for fnm in resfiles:
                 print(fnm)
                 if "IterationInfo" in fnm:
                     os.remove(os.path.join(oPath, fnm))
                 elif  "result" in fnm:
                     os.remove(os.path.join(oPath, fnm))
                 elif  ".log" in fnm:
                     os.remove(os.path.join(oPath, fnm))
                 elif  "TransformParameters" in fnm:
                     os.remove(os.path.join(oPath, fnm))
                 #endif
             #endfor                        
           #endif   
      except:
          print("nothing to delete ...")
  #enddef

  def checkVisSimTools(self,vtVars ):
        # TODO: optimise this part to download only the missing files        
        # Check if elastix exist or download it 
        print(" Defaults paths: " + vtVars['vissimPath'])
        print("      VisSimTools folder: " + vtVars['vissimPath'])
        if isfile(vtVars['elastixBinPath'].strip()): 
           print("elastix binaries are found in " + vtVars['elastixBinPath'] )
        else: 
            print("elastix binaries are missing, trying to download ... ")
            self.msgBox("elastix binaries are missing!")
        #endif
        # check if other files exist
        if isfile(vtVars['parsPath'].strip()): 
           print("Other files are found !" )
           print("  Parameter file: " + vtVars['parsPath'])
           print("  Output folder : " + vtVars['outputPath'])            
           #print("  Cropping Length: " + str(croppingLength))           
        else: 
            print("Other files are  missing, trying to download ... ")
            self.msgBox("important files are missing and will be downloaded!")
            try:                               
                print("Downloading VisSimTools others ...")
                vissimZip = expanduser("~/VisSimToolsTmp.zip")
                with open(vissimZip ,'wb') as f:
                     uFile = urllib2.urlopen(vtVars['othersWebLink'])              
                     chunk = 10024096
                     while 1:
                           data = uFile.read(chunk)
                           f.write(data)                   
                           if not data:
                              f.close()                               
                              print "done!"
                              break
                           #endIf
                           print "Reading ...  %s bytes"%len(data) 
                     #endWhile                               
                print("Extracting to user home ")
                zip_ref = zipfile.ZipFile(vissimZip, 'r')
                zip_ref.extractall(expanduser("~/"))
                zip_ref.close()  
                #remove the downloaded zip file     
                os.remove(vissimZip)   
                # change permission of bin folder for Linux
                if int(self.vtVars['downSz'])==0:   
                   print("Making binaries executable for Linux ")
                   md=  stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH |stat.S_IXGRP |stat.S_IXOTH
                   os.chmod(vtVars['elastixBinPath'].strip()    ,  md)
                   os.chmod(vtVars['transformixBinPath'].strip(),  md)
                   os.chmod(vtVars['elastixBinPath'].strip(),  md)
                #endif 
                msg.setInformativeText("VisSimTools folder is downloaded and ready to use!")
                msg.exec_()                      
                                          
            except Exception as e:
                  print("Error: can not download and extract VisSimTools ...")
                  print(e)   
                  return -1
            #end try-except  
  #enddef
  
  def msgBox(self,txt):
      msg = qt.QMessageBox()
      msg.setIcon(qt.QMessageBox.Information)
      msg.setText("information:")
      msg.setInformativeText(txt)
      msg.setWindowTitle("VisSimTools")
      msg.exec_()
  #enddef
  
  def removeOtputsFolderContents(self):
      try:
          for file in os.listdir(self.vtVars['outputPath']):
              filePath = os.path.join(self.vtVars['outputPath'], file)
              if os.path.isfile(filePath):
                 os.remove(filePath)
             #endif
          #endfor        			
      except Exception as e:
            print("nothing to delete ...")
            print(e)
       #endtry 
  #enddefr 
              
                                     
#===================================================================
#                           Test
#===================================================================
class VertebraToolsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  logic = VertebraToolsLogic()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)
    self.vtVars    = self.logic.setGlobalVariables(True)
    self.logic.removeOtputsFolderContents()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.testSlicerVertebraTools()

  def testSlicerVertebraTools(self):

    self.delayDisplay("Starting the test")
    self.stm=time.time()
    print("time:" + str(self.stm))
    
    # to get the links from datastore open http://slicer.kitware.com/midas3/community/23 then select a file and click share to get
    # the download link
    # TODO: fix datastore link download problem, the file is created before downloaded   
    #   imgLaWeb = "http://slicer.kitware.com/midas3/download/item/381221/P100001_DV_L_a"

    fnm = os.path.join(*(self.logic.vtVars['outputPath'] +",imgA"+self.logic.vtVars['imgType']).split(",")) 
    if not os.path.exists(fnm):
       try:         
           print("Downloading vertebra sample image ...")
           import urllib
           imgCtWebLink = "https://mtixnat.uni-koblenz.de/owncloud/index.php/s/Wiaqr0vfCr10h44/download"
           imgMrWebLink = "https://mtixnat.uni-koblenz.de/owncloud/index.php/s/nnwKxqavP4ORv9y/download"
           urllib.urlretrieve (imgCtWebLink ,fnm )
       except Exception as e:
              print("Error: can not download sample file  ...")
              print(e)   
              return -1
       #end try-except 
    #endif
    [success, inputVolumeNode] = slicer.util.loadVolume( fnm, returnNode=True)
    
    # create a fiducial node for vertebra location for cropping    
    #RASpt  = [-1.169, -12.078, -57.042] #CTC3 
    #RASpt = [-2.870, 43.614, 107.779]
    #RASpt  = [-1.169, -15.156, -39.855] #CTC2
    #RASpt = [-2.167, 46.822, 127.272]
    RASpt  =[0.390,  -23.553,  -115.521] #CTC7
    #RASpt = [-4.276, 6.942, 54.510]

    inputFiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
    inputFiducialNode.CreateDefaultDisplayNodes()
    inputFiducialNode.SetName(inputVolumeNode.GetName()+"_VertebraLocationPoints")  
    inputFiducialNode.AddFiducialFromArray(RASpt)
    
    #inputFiducialNode.AddFiducial(RASpt[0],RASpt[1],RASpt[2])
    # Which vertebra
    vtID = 7
    # C7 center of mass
    # run the segmentation
    self.logic.run(inputVolumeNode, inputFiducialNode, vtID, True)    
    # extract scaled model 
    vtResultSegNode    = slicer.util.getNode(inputVolumeNode.GetName()+"_Seg_C"    +str(vtID)) 
    vtResultLigPtsNode = slicer.util.getNode(inputVolumeNode.GetName()+"_LigPts_C" +str(vtID))
    self.logic.extractScaledModel(vtResultSegNode ,self.logic.vtVars['segNodeCoM'],self.logic.vtVars['subVarsFnm'] )
    self.logic.extractScaledModel(vtResultLigPtsNode,self.logic.vtVars['segNodeCoM'],self.logic.vtVars['subVarsFnm'] )      
    # 
    #slicer.mrmlScene.RemoveNode(croppedNode )

    self.etm=time.time()
    tm=self.etm - self.stm
    print("Time: "+str(tm)+"  seconds")
    
    self.delayDisplay('Test passed!')
  #enddef

    