import vtk
import time
from pymongo.mongo_client import MongoClient
from trame.app import get_server, asynchronous
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import vuetify, trame, vtk as vtk_widgets


from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkCommonDataModel import vtkDataObject
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader
from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor


from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkLightKit,
)

from pprint import pprint

from ColorModule import LookupTable, ColorPreset

    
class MyInteractorStyle(vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        self.AddObserver('LeftButtonPressEvent', self.left_button_press_event)
        self.AddObserver('LeftButtonReleaseEvent', self.left_button_release_event)
        self.start_time = None

    def left_button_press_event(self, obj, event):
        self.start_time = time.time()
        self.OnLeftButtonDown()
        return
    
    def left_button_release_event(self, obj, event):
        elapsed_time = time.time() - self.start_time
        if elapsed_time < 100/1000:
            clickPos = self.GetInteractor().GetEventPosition()
            if app.annotation_mode:
                app.ReadMousePosition(clickPos)
        self.OnLeftButtonUp()
        return
        
# -----------------------------------------------------------------------------
# 3D Visualize model and annotation
# -----------------------------------------------------------------------------
class MyApp:
    def __init__(self, server=None):
        if server is None:
            server = get_server()

        self.server = server
        self.state  = server.state
        self.ctrl   = server.controller

        # Initialize database parameter
        self.uri                        = []
        self.client                     = []
        self.database                   = []
        self.collection                 = []
        self.documents                  = []
        self.total_documents            = []
        self.documents_list             = []

        # Initialize gui parameters
        self.dialog_open                = False

        # Initialize the editedItem list with the same length as the documents_list
        self.state.editedItem           = [] 
        self.choosing_idx               = []
        
        # Initialize the App
        self.renderer                   = vtkRenderer()
        self.renderWindow               = vtkRenderWindow()
        self.renderWindowInteractor     = vtkRenderWindowInteractor()

        self.camera                     = []
        

        # Visual var 
        self.colors                     = vtkNamedColors()
        self.lightkit                   = vtkLightKit()

        # Initiate vtk mapper, actor, texture
        self.mesh_mapper                = vtkPolyDataMapper()
        self.mesh_actor                 = vtkActor()
        self.warp                       = vtk.vtkWarpVector()
        self.warp_mapper                = vtkDataSetMapper()
        self.warp_actor                 = vtkActor()
        self.cube_axes                  = vtkCubeAxesActor()
        self.texture                    = vtk.vtkTexture()
        self.texture_mapper             = vtkPolyDataMapper()
        self.texture_actor              = vtkActor()
        self.glyph                      = vtk.vtkGlyph3D()
        self.points                     = vtk.vtkPoints()
        self.glyph_data                 = vtk.vtkPolyData()
        self.glyph_mapper               = vtkPolyDataMapper()
        self.glyph_actor                = vtkActor()
        self.anno_transform             = vtk.vtkTransform()
        self.box_widgets                = vtk.vtkBoxWidget()

        self._running = False

        # State parameter
        self.annotation_mode            = False

        # Readder parameter
        self.reader                     = vtkXMLUnstructuredGridReader()
        self.reader_obj                 = vtk.vtkOBJReader()
        self.texture_reader             = vtk.vtkJPEGReader()

        # Parameters that contain data
        self.dataset_arrays             = []
        self.fields                     = []
        self.default_array              = []
        self.default_min                = 0
        self.default_max                = 0
        self.warp_scale                 = 1

        # Color var
        self.mesh_lut                   = []

        # # Initialize the App
        self.Initialize()

        # State listeners
        self.state.change("mesh_representation")(self.UpdateMeshRepresentation)
        self.state.change("mesh_color_array_idx")(self.UpdateMeshColorByName)
        self.state.change("mesh_color_preset")(self.UpdateMeshColorPreset)
        self.state.change("warp_color_array_idx")(self.UpdateWarpColorByName)
        self.state.change("warp_color_preset")(self.UpdateWarpColorPreset)
        self.state.change("mesh_opacity")(self.UpdateMeshOpacity)
        self.state.change("warp_opacity")(self.UpdateWarpOpacity)
        self.state.change("scale_for_warp")(self.UpdateWarpScale)
        self.state.change("cube_axes_visibility")(self.UpdateCubeAxesVisibilty)
        self.state.change("annotation_trigger")(self.UpdateAnnotationMode)

# -----------------------------------------------------------------------------
# General APIs (Visibility)
# -----------------------------------------------------------------------------
    def register_method(self):
        trame.register_state_update("open_dialog",self.open_dialog)

    def Initialize(self, **kwargs):

        print('Start Initialze')
        self.SetUpDatabase()
        self.InitializeEditedItem()
        self.SetUpRender()
        self.SetUpLight()
        self.SetUpCamera()
        self.ReadOBJ()
        self.ReadJPG()
        self.InitializeMapper(self.mesh_mapper)
        self.InitializeActor(self.mesh_actor, self.mesh_mapper)
        self.InitializeTexture()
        self.InitializeGlyph()
        self.SetUpCubeAxes()
        self.SetUpInteractor()
        print('Initialze finished')
        self._running = True
    
    def SetUpDatabase(self):
        self.uri        = "mongodb+srv://SuperAdmin:admin@cluster0.gins5pf.mongodb.net/?retryWrites=true&w=majority"
        self.client     = MongoClient(self.uri)
        self.database   = self.client.AnnotationDB
        self.collection = self.database.AnnotationCL 
        self.documents  = self.collection.find({})
        self.total_documents = self.collection.count_documents({})
        self.documents_list  =list(self.documents)
    
    def InitializeEditedItem(self):
            # Initialize the editedItem list with the same length as the documents_list
        self.state.editedItem = [
            {
                "name" : doc["name"],
                "x"    : doc["x"],
                "y"    : doc["y"],
                "z"    : doc["z"],
                "level": doc.get("level", 1),  # Assuming 'level' is an optional field with a default value of 1
            }
            for doc in self.documents_list
        ]
    
    def SetUpRender(self):
        self.renderer.SetBackground(self.colors.GetColor3d('slate_grey')) #ghost white good
        self.renderWindow.AddRenderer(self.renderer)
        
    def SetUpInteractor(self):
        #if annote == True:
        print('Setting up interactor')
        style = MyInteractorStyle()
        self.renderWindowInteractor.SetRenderWindow(self.renderWindow)
        self.renderWindowInteractor.SetInteractorStyle(style)
        self.renderWindowInteractor.Initialize()
        #self.renderWindowInteractor.Start()

    def boxcall(self):
        print('Clicked')

    def SetUpLight(self):
        self.lightkit.AddLightsToRenderer(self.renderer)
        self.lightkit.SetHeadLightWarmth(0.5)
        self.lightkit.SetFillLightWarmth(0.5)
        self.lightkit.SetKeyLightWarmth(0.5)
    
    def SetUpCamera(self):
        self.camera = self.renderer.GetActiveCamera()    
        # This view is okk, but we have to wirte method later for cal proper view automatically   
        p = {'position'         : (175.57928933895226, -48.246428725103065, 40.884611931851765), 
             'focal point'      : (63.9077934374408, 35.45726816337757, 8.713665132410494), 
             'view up'          : (-0.21329675699056322, 0.08935923577768858, 0.9728922964226493), 
             'distance'         : 143.2194179839187, 
             'clipping range'   : (0.01, 1000.01), 
             'orientation'      : (-35.76370477694476, -73.92907216100338, -83.67747559782863)
             }
        
        self.camera.SetPosition(p['position'])
        self.camera.SetFocalPoint(p['focal point'])
        self.camera.SetViewUp(p['view up'])
        self.camera.SetDistance(p['distance'])
        self.camera.SetClippingRange(p['clipping range'])
    
    def GetCurrentCameraPosition(self):
        self.camera = self.renderer.GetActiveCamera()      
        p = dict()
        p['position']       = self.camera.GetPosition()
        p['focal point']    = self.camera.GetFocalPoint()
        p['view up']        = self.camera.GetViewUp()
        p['distance']       = self.camera.GetDistance()
        p['clipping range'] = self.camera.GetClippingRange()
        p['orientation']    = self.camera.GetOrientation()

    def SetUpCubeAxes(self):
        axis1Color = self.colors.GetColor3d("Salmon")
        axis2Color = self.colors.GetColor3d("PaleGreen")
        axis3Color = self.colors.GetColor3d("LightSkyBlue")
        axeColor   = self.colors.GetColor3d("White")

        self.renderer.AddActor(self.cube_axes)
        self.cube_axes.SetBounds(self.mesh_actor.GetBounds())
        self.cube_axes.SetCamera(self.renderer.GetActiveCamera())
        self.cube_axes.SetXLabelFormat("%6.1f")
        self.cube_axes.SetYLabelFormat("%6.1f")
        self.cube_axes.SetZLabelFormat("%6.1f")
        self.cube_axes.GetTitleTextProperty(0).SetColor(axis1Color)
        self.cube_axes.GetLabelTextProperty(0).SetColor(axis1Color)
        self.cube_axes.GetXAxesLinesProperty().SetColor(axeColor)
        #self.cube_axes.GetXAxesGridlinesProperty().SetColor(axis1Color)
        self.cube_axes.GetTitleTextProperty(1).SetColor(axis2Color)
        self.cube_axes.GetLabelTextProperty(1).SetColor(axis2Color)
        self.cube_axes.GetYAxesLinesProperty().SetColor(axeColor)
        self.cube_axes.GetTitleTextProperty(2).SetColor(axis3Color)
        self.cube_axes.GetLabelTextProperty(2).SetColor(axis3Color)
        self.cube_axes.GetZAxesLinesProperty().SetColor(axeColor)
        self.cube_axes.SetFlyModeToOuterEdges()
        self.renderer.ResetCamera()

    def ReadVTK(self):
        self.reader.SetFileName('./VTKdata/data_nodal_Consolidation1 [Phase_1]_step_8_soil.vtu')
        self.reader.Update()

    def ReadOBJ(self):
        self.reader_obj.SetFileName('./3DMeshData/Sepulvada dam Project_simplified_3d_mesh.obj')
        self.reader_obj.Update()

    def ReadJPG(self):
        self.texture_reader.SetFileName('./3DMeshData/Sepulvada dam Project_texture.jpg')
        self.texture_reader.Update()
    
    def ExtractDataSet(self):
            self.fields = [
                (self.reader.GetOutput().GetPointData(), vtkDataObject.FIELD_ASSOCIATION_POINTS),
                (self.reader.GetOutput().GetCellData(), vtkDataObject.FIELD_ASSOCIATION_CELLS),
                  ]
            for field in self.fields:
                field_arrays, association = field
                for i in range(field_arrays.GetNumberOfArrays() - 1):
                    array = field_arrays.GetArray(i)
                    array_range = array.GetRange()
                    print(i,': ', array.GetName())
                    self.dataset_arrays.append(
                        {
                            "text": array.GetName(),
                            "value": i,
                            "range": list(array_range),
                            "type": association,
                        }
                    )
            self.default_array = self.dataset_arrays[0]
            self.default_min, self.default_max = self.default_array.get("range")
    
    def InitializeMapper(self, mapper):
        mapper.SetInputData(self.reader_obj.GetOutput())

    def InitializeActor(self, actor, mapper):
        actor.SetMapper(mapper)
        self.renderer.AddActor(actor)

    def InitializeTexture(self):
        # Texture
        self.texture.SetInputConnection(self.texture_reader.GetOutputPort())
        self.texture_mapper.SetInputData(self.reader_obj.GetOutput())
        # Mapper
        #self.texture_mapper.AutomaticPlaneGenerationOn()
        self.texture_mapper.Update()
        # Actor 
        self.mesh_actor.SetTexture(self.texture)
        self.mesh_actor.SetMapper(self.texture_mapper)
        
    def InitializeWarp(self):
        self.warp.SetInputConnection(self.reader_obj.GetOutputPort())
        self.warp.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, 'Displacement')
        self.warp.SetScaleFactor(1)
        self.warp.Update()

    def InitializeWarpMapper(self):
        self.warp_mapper.SetInputConnection(self.warp.GetOutputPort())
    
    def InitializeWarpActor(self):
        self.warp_actor.SetMapper(self.warp_mapper)
    
    def InitializeGlyph(self):
        glyph_source = vtk.vtkConeSource()
        glyph_source.SetResolution(10)
        glyph_source.SetDirection(0, 0, -1)
        glyph_source.Update()

        for doc in self.documents_list:
            self.points.InsertNextPoint(doc['x'], doc['y'], doc['z'])

        self.glyph_data.SetPoints(self.points)

        self.glyph.SetSourceConnection(glyph_source.GetOutputPort())  # Set the input source for the glyphs
        self.glyph.SetInputData(self.glyph_data)
        self.glyph.SetScaleModeToScaleByScalar()  # Set the scaling mode for the glyphs
        self.glyph.SetScaleFactor(1)  # Set the scale factor for the glyphs
        self.glyph.Update()

        self.glyph_mapper.SetInputConnection(self.glyph.GetOutputPort())

        self.glyph_actor.SetMapper(self.glyph_mapper)

        self.glyph_actor.GetProperty().SetColor(0, 1, 0)
        self.renderer.AddActor(self.glyph_actor)

        self.UpdateView()
    
    def UpdateAnnotationMode(self, annotation_trigger, **kwargs):
        self.annotation_mode = annotation_trigger

    def UpdateMeshRepresentation(self, mesh_representation, **kwargs):
        self.UpdateRepresentation(self.mesh_actor, mesh_representation)
        self.UpdateRepresentation(self.warp_actor, mesh_representation)

    def ReadMousePosition(self, clickPos):        
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(1/1000)
        picker.Pick(clickPos[0], clickPos[1], 0, self.renderer)
        picked_pos = picker.GetPickPosition()
        print(f"Picked position: ({picked_pos[0]:.2f}, {picked_pos[1]:.2f}, {picked_pos[2]:.2f})")

    def UpdateRepresentation(self, actor, rep_type):
        property = actor.GetProperty()
        if rep_type == 0:
            property.SetRepresentationToPoints()
            property.SetPointSize(1)
            property.EdgeVisibilityOff()      
        elif rep_type == 1:
            property.SetRepresentationToWireframe()
            property.SetPointSize(1)
            property.EdgeVisibilityOff()   
        elif rep_type == 2:
            property.SetRepresentationToSurface()
            property.SetPointSize(1)
            property.EdgeVisibilityOff()      
        elif rep_type == 3:
            property.SetRepresentationToSurface()
            property.SetPointSize(1)
            property.EdgeVisibilityOn()   

    def UpdateWarpScale(self, scale_for_warp, **kwargs):
        self.warp_scale = scale_for_warp
        self.warp.SetScaleFactor(self.warp_scale)
        self.InitializeWarpMapper()
        self.InitializeWarpActor()
        self.UpdateView()

    def UpdateMeshOpacity(self, mesh_opacity, **kwargs):
        self.UpdateOpacity(self.mesh_actor, mesh_opacity)

    def UpdateWarpOpacity(self, warp_opacity, **kwargs):
        self.UpdateOpacity(self.warp_actor, warp_opacity)

    def UpdateOpacity(self, actor, magnitude):
        actor.GetProperty().SetOpacity(magnitude)
        self.UpdateView()
    
    def UpdateCubeAxesVisibilty(self, cube_axes_visibility, **kwargs):
        self.cube_axes.SetVisibility(cube_axes_visibility)
        self.GetCurrentCameraPosition()
        self.UpdateView()

    def UpdateMeshColorByName(self, mesh_color_array_idx, **kwargs):
        array = self.dataset_arrays[mesh_color_array_idx]
        self.ColorByArray(self.mesh_actor, array)
        self.UpdateView()

    def UpdateWarpColorByName(self, warp_color_array_idx, **kwargs):
        array = self.dataset_arrays[warp_color_array_idx]
        self.ColorByArray(self.warp_actor, array)
        self.UpdateView()

    def ColorByArray(self, actor, array):
        _min, _max = array.get("range")
        mapper = actor.GetMapper()
        mapper.SelectColorArray(array.get("text"))
        mapper.GetLookupTable().SetRange(_min, _max)
        if array.get("type") == vtkDataObject.FIELD_ASSOCIATION_POINTS:
            mapper.SetScalarModeToUsePointFieldData()
        else:
            mapper.SetScalarModeToUseCellFieldData()
        mapper.SetScalarVisibility(True)
        mapper.SetUseLookupTableScalarRange(True)

    def UpdateMeshColorPreset(self, mesh_color_preset, **kwargs):
        self.mesh_lut = ColorPreset.UsePreset(self.mesh_actor, mesh_color_preset)
        self.UpdateView()
    
    def UpdateWarpColorPreset(self, warp_color_preset, **kwargs):
        self.warp_lut = ColorPreset.UsePreset(self.warp_actor, warp_color_preset)
        self.UpdateView()



    # -----------------------------------------------------------------------------
    # General APIs (UI)
    # -----------------------------------------------------------------------------
    # Selection Change
    def actives_change(self, ids):
        _id = ids[0]
        if _id == "1":  # Mesh
            self.state.active_ui = "mesh_ui"
        elif _id == "2":  # Warp
            self.state.active_ui = "annotation_ui"
        else:
            self.state.active_ui = "nothing"


    # Visibility Change
    def visibility_change(self, event):
        _id = event["id"]
        _visibility = event["visible"]

        if _id == "1":  # Mesh
            self.mesh_actor.SetVisibility(_visibility)
        elif _id == "2":  # Warp
            self.warp_actor.SetVisibility(_visibility)

        self.UpdateView()
    
    def UpdateView(self):
        if self._running:
            self.ctrl.view_update()

# -----------------------------------------------------------------------------
# UI Elements
# -----------------------------------------------------------------------------
    def pipeline_widget(self):
        trame.GitTree(
            sources=(
                "pipeline",
                [
                    {"id": "1", "parent": "0", "visible": 1, "name": "Mesh"},
                    {"id": "2", "parent": "1", "visible": 1, "name": "Annotate"},
                ],
            ),
            actives_change=(self.actives_change, "[$event]"),
            visibility_change=(self.visibility_change, "[$event]"),
        )

    def standard_buttons(self):
        vuetify.VCheckbox(
            v_model=("cube_axes_visibility", True),
            on_icon="mdi-cube-outline",
            off_icon="mdi-cube-off-outline",
            classes="mx-1",
            hide_details=True,
            dense=True,
        )
        vuetify.VCheckbox(
            v_model="$vuetify.theme.dark",
            on_icon="mdi-lightbulb-off-outline",
            off_icon="mdi-lightbulb-outline",
            classes="mx-1",
            hide_details=True,
            dense=True,
        )
        vuetify.VCheckbox(
            v_model=("annotation_trigger", False),
            on_icon="mdi-circle-outline",
            off_icon="mdi-circle-off-outline",
            classes="mx-1",
            hide_details=True,
            dense=True,
        )
        with vuetify.VBtn(icon=True, click="$refs.view.resetCamera()"):
            vuetify.VIcon("mdi-crop-free")

    def ui_card(self, title, ui_name):
        with vuetify.VCard(v_show=f"active_ui == '{ui_name}'"):
            vuetify.VCardTitle(
                title,
                classes="grey lighten-1 py-1 grey--text text--darken-3",
                style="user-select: none; cursor: pointer",
                hide_details=True,
                dense=True,
            )
            content = vuetify.VCardText(classes="py-2")
        return content

    def mesh_card(self):
        with self.ui_card(title="Mesh", ui_name="mesh_ui"):
            vuetify.VSlider(
                # Opacity
                v_model=("mesh_opacity", 1.0),
                min=0,
                max=1,
                step=0.1,
                label="Opacity",
                classes="mt-1",
                hide_details=True,
                dense=True,
            )
    def warp_card(self):
        with self.ui_card(title="Warp", ui_name="warp_ui"):
            vuetify.VSlider(
                v_model=("scale_for_warp", 1.0),
                min=1,
                max=1000,
                step=1,
                label="Warp scale",
                classes="mt-1",
                hide_details=True,
                dense=True,
            )
            with vuetify.VRow(classes="pt-2", dense=True):
                with vuetify.VCol(cols="6"):
                    vuetify.VSelect(
                        #Color By
                        label="Color by",
                        v_model=("warp_color_array_idx", 0),
                        items=("array_list", app.dataset_arrays),
                        hide_details=True,
                        dense=True,
                        outlined=True,
                        classes="pt-1",
                    )
                with vuetify.VCol(cols="6"):
                    vuetify.VSelect(
                        # Color Map
                        label="Colormap",
                        v_model=("warp_color_preset", LookupTable.Rainbow),
                        items=(
                            "colormaps",
                            [
                                {"text": "Rainbow", "value": 0},
                                {"text": "Inv Rainbow", "value": 1},
                                {"text": "Greyscale", "value": 2},
                                {"text": "Inv Greyscale", "value": 3},
                            ],
                        ),
                        hide_details=True,
                        dense=True,
                        outlined=True,
                        classes="pt-1",
                    )
            vuetify.VSlider(
                v_model=("warp_opacity", 1.0),
                min=0,
                max=1,
                step=0.1,
                thumb_label=True,
                label="Opacity",
                classes="mt-1",
                hide_details=True,
                dense=True,
            )

    def annotation_card(self):
        with self.ui_card(title="Annotation", ui_name="annotation_ui"):
            with vuetify.VList(shaped=True, v_model=("abc", 0)):
                for idx, doc in enumerate(self.documents_list):
                    with vuetify.VListItem():
                        with vuetify.VListItemIcon():
                            vuetify.VIcon("mdi-food")
                        with vuetify.VListItemContent():
                            vuetify.VListItemTitle(doc['name'])
                        vuetify.VBtn(class_="mb-2", children=["Edit"],
                                     click=self.open_dialog)
                        self.choosing_idx = idx

            with vuetify.VDialog(v_model=("dialog", False), max_width="500px") as dialog:
                with vuetify.VCard():
                    vuetify.VCardTitle(children=['New entry'])
                    vuetify.VCardText()
                    with vuetify.VContainer():
                        with vuetify.VRow():
                            for prop, label in [
                                ("editedItem.name", "Name"),
                                ("editedItem.x", "x"),
                                ("editedItem.y", "y"),
                                ("editedItem.z", "z"),
                                ("editedItem.level", "level"),
                            ]:
                                with vuetify.VCol(cols="12", sm="6", md="4"):
                                    vuetify.VTextField(v_model=(prop,), label=label)
                    with vuetify.VCardActions():
                        vuetify.VSpacer()
                        vuetify.VBtn(color="blue darken-1", text=True, children=["Cancel"],
                                     click="close_dialog()")
                        vuetify.VBtn(color="blue darken-1", text=True, children=["Save"],
                                     click="save_changes()")

    def open_dialog(self):
        self.state.selected_idx = self.choosing_idx
        self.state.editedItem = self.documents_list[self.choosing_idx]
        self.state["dialog"] = True

    def close_dialog(self):
        self.state["dialog"] = False

    def save_changes(self):
        # Update the documents_list with the edited_item
        self.documents_list[self.state.selected_idx] = self.state.editedItem
        # Save the updated annotation to the database
        self.update_annotation_in_db(self.state.editedItem)
        # Close the dialog after saving changes
        trame.set_state("dialog", False)

    def update_annotation_in_db(self, annotation):
        # Implement the function to update the annotation in the database
        pass
# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

server = get_server()
app    = MyApp(server)
app.state.setdefault("active_ui", "annotation_ui")

# -----------------------------------------------------------------------------
# GUIs
# -----------------------------------------------------------------------------
with SinglePageWithDrawerLayout(server) as layout:

    layout.title.set_text("Geoverse Vision Technology")
    with layout.toolbar:
        # toolbar components
        vuetify.VSpacer()
        vuetify.VDivider(vertical=True, classes="mx-2")
        app.standard_buttons()

    with layout.drawer as drawer:
        # drawer components
        drawer.width = 325
        app.pipeline_widget()
        vuetify.VDivider(classes="mb-2")
        app.mesh_card()
        app.annotation_card()

    with layout.content:
        # content components
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
            # ------------ For Local View -------------
            # view = vtk_widgets.VtkLocalView(
            #     app.renderWindow, namespace="view", mode="local", interactive_ratio=1
            # )
            # ------------ Remote View ---------------
            view = vtk_widgets.VtkRemoteView(
                app.renderWindow, ref = "view",
            )
            # ----------------------------------------
            app.ctrl.view_update = view.update
            app.ctrl.view_reset_camera = view.reset_camera

# -----------------------------------------------------------------------------
# START
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()
    
