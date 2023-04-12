import vtk
import asyncio
from trame.app import get_server, asynchronous
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import vuetify, trame, vtk as vtk_widgets

from vtkmodules.vtkCommonDataModel import vtkDataObject
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader
from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor


from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkLightKit,
)

from ColorModule import LookupTable, ColorPreset

# -----------------------------------------------------------------------------
# Wavelet Application
# -----------------------------------------------------------------------------
class MyApp:
    def __init__(self, server=None):
        if server is None:
            server = get_server()

        self.server = server
        self.state  = server.state
        self.ctrl   = server.controller

        # Initialize the App
        # self.ctrl.on_server_ready.add(self.Initialize)

        # Initialize viewer var
        self.renderer                   = vtkRenderer()
        self.renderWindow               = vtkRenderWindow()
        self.renderWindowInteractor     = vtkRenderWindowInteractor()

        # Visual var 
        self.colors                     = vtkNamedColors()
        self.lightkit                   = vtkLightKit()

        # Initiate vtk mapper, actor
        self.mesh_mapper                = vtkDataSetMapper()
        self.mesh_actor                 = vtkActor()
        self.warp                       = vtk.vtkWarpVector()
        self.warp_mapper                = vtkDataSetMapper()
        self.warp_actor                 = vtkActor()

        self._running = False

        # Readder parameter
        self.reader                     = vtkXMLUnstructuredGridReader()

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
        # self.ctrl.on_server_ready.add(self.Initialize)
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

# -----------------------------------------------------------------------------
# General APIs (Visibility)
# -----------------------------------------------------------------------------
    def Initialize(self, **kwargs):
       
        print('Start Initialze')
        self.SetUpRender()
        self.SetUpLight()
        self.SetUpCamera()
        self.ReadVTK()
        self.ExtractDataSet()
        self.InitializeMapper(self.mesh_mapper)
        self.InitializeMapper(self.warp_mapper)
        self.InitializeActor(self.mesh_actor, self.mesh_mapper)
        self.InitializeActor(self.warp_actor, self.warp_mapper)
        self.InitializeWarp()
        self.InitializeWarpMapper()
        self.InitializeWarpActor()
        print('Initialze finished')
        self._running = True

    def SetUpRender(self):
        self.renderer.SetBackground(self.colors.GetColor3d('ghost_white'))
        self.renderWindow.AddRenderer(self.renderer)
        self.renderWindowInteractor.SetRenderWindow(self.renderWindow)
        self.renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

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
        print(p)

    def ReadVTK(self):
        self.reader.SetFileName('./VTKdata/data_nodal_Consolidation1 [Phase_1]_step_8_soil.vtu')
        self.reader.Update()
    
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
        mapper.SetInputConnection(self.reader.GetOutputPort())

    def InitializeActor(self, actor, mapper):
        actor.SetMapper(mapper)
        self.renderer.AddActor(actor)

    def InitializeWarp(self):
        self.warp.SetInputConnection(self.reader.GetOutputPort())
        self.warp.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, 'Displacement')
        self.warp.SetScaleFactor(1)
        self.warp.Update()

    def InitializeWarpMapper(self):
        self.warp_mapper.SetInputConnection(self.warp.GetOutputPort())
    
    def InitializeWarpActor(self):
        self.warp_actor.SetMapper(self.warp_mapper)

    def UpdateMeshRepresentation(self, mesh_representation, **kwargs):
        self.UpdateRepresentation(self.mesh_actor, mesh_representation)
        self.UpdateRepresentation(self.warp_actor, mesh_representation)
        self.UpdateView()

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
        print('bf', mesh_opacity)
        self.UpdateOpacity(self.mesh_actor, mesh_opacity)
        print('af', mesh_opacity)

    def UpdateWarpOpacity(self, warp_opacity, **kwargs):
        print('bf',warp_opacity)
        self.UpdateOpacity(self.warp_actor, warp_opacity)
        print('af',warp_opacity)

    def UpdateOpacity(self, actor, magnitude):
        actor.GetProperty().SetOpacity(magnitude)
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
        print('Active changed')
        _id = ids[0]
        if _id == "1":  # Mesh
            self.state.active_ui = "mesh_ui"
        elif _id == "2":  # Warp
            self.state.active_ui = "warp_ui"
        else:
            self.state.active_ui = "nothing"
        print(self.state.active_ui)


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
                    {"id": "2", "parent": "1", "visible": 1, "name": "Warp"},
                ],
            ),
            actives_change=(self.actives_change, "[$event]"),
            visibility_change=(self.visibility_change, "[$event]"),
        )

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
            vuetify.VSelect(
                # Representation
                v_model = ("mesh_representation", 3),
                items=(
                    "representations",
                    [
                        {"text": "Points", "value": 0},
                        {"text": "Wireframe", "value": 1},
                        {"text": "Surface", "value": 2},
                        {"text": "SurfaceWithEdges", "value": 3},
                    ],
                ),
                label="Representation",
                hide_details=True,
                dense=True,
                outlined=True,
                classes="pt-1",
            )
            with vuetify.VRow(classes="pt-2", dense=True):
                with vuetify.VCol(cols="6"):
                    vuetify.VSelect(
                        # Color By
                        label="Color by",
                        v_model=("mesh_color_array_idx", 0),
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
                        v_model=("mesh_color_preset", LookupTable.Rainbow),
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
                label="Opacity",
                classes="mt-1",
                hide_details=True,
                dense=True,
            )

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

server = get_server()
app    = MyApp(server)
app.state.setdefault("active_ui", "mesh_ui")

# -----------------------------------------------------------------------------
# GUIs
# -----------------------------------------------------------------------------
with SinglePageWithDrawerLayout(server) as layout:

    layout.title.set_text("Viewer")
    with layout.toolbar:
        # toolbar components
        vuetify.VSpacer()
        vuetify.VDivider(vertical=True, classes="mx-2")

    with layout.drawer as drawer:
        # drawer components
        drawer.width = 325
        app.pipeline_widget()
        vuetify.VDivider(classes="mb-2")
        app.mesh_card()
        app.warp_card()

    with layout.content:
        # content components
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
            view = vtk_widgets.VtkRemoteLocalView(
                app.renderWindow, namespace="view", mode="local", interactive_ratio=1
            )
            app.ctrl.view_update = view.update
            app.ctrl.view_reset_camera = view.reset_camera
            app.ctrl.on_server_ready.add(view.update)

# -----------------------------------------------------------------------------
# START
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()
