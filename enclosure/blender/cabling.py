"""Editable cable dressing and a separate, conceptual multidrop layout.

Connector pin order comes from the 2026-08-31 EasyEDA PCB PAD_NET records.
Colours are a proposed harness convention, not a standard Ethernet pinout.
"""
import math


def build_cabling(*, bpy, groups, root, rubber, silver, mint, socket, steel,
                  box, material, parent_to, visibility):
    jacket = material("O89 | Cat5e - graphite jacket 5.2 mm", (0.013, 0.020, 0.025), 0.47)
    orange = material("O89 | Pair - orange", (0.65, 0.14, 0.025), 0.46)
    white = material("O89 | Pair - white insulation", (0.68, 0.71, 0.69), 0.5)
    blue = material("O89 | Pair - blue", (0.025, 0.19, 0.48), 0.46)
    green = material("O89 | Signal reference - green", (0.035, 0.29, 0.12), 0.5)
    grey = material("O89 | CAN pair - grey", (0.11, 0.14, 0.16), 0.5)
    red = material("O89 | Power - red", (0.48, 0.028, 0.020), 0.5)
    strap_mat = material("O89 | Cable straps - matte charcoal", (0.009,0.011,0.014), 0.68)
    strap_mat.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.20
    braid = material("O89 | Expandable braided cable sleeve", (0.006,0.008,0.010), 0.68)
    nodes, links = braid.node_tree.nodes, braid.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Specular IOR Level"].default_value = 0.12
    uv = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    links.new(uv.outputs["UV"],separate.inputs[0])
    def math_node(operation, a, b=None, name=None):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        if name:
            node.name = name
        for value, socket in ((a,node.inputs[0]),(b,node.inputs[1])):
            if value is None:
                continue
            if isinstance(value,(int,float)):
                socket.default_value = value
            else:
                links.new(value,socket)
        return node.outputs[0]
    around = math_node("MULTIPLY",separate.outputs["X"],math.tau*32,"Braid repeats around circumference")
    along = math_node("MULTIPLY",separate.outputs["Y"],math.tau*60,"Braid repeats along sleeve")
    ridges = []
    for direction in ("ADD","SUBTRACT"):
        phase = math_node(direction,around,along)
        wave = math_node("ABSOLUTE",math_node("SINE",phase))
        ridges.append(math_node("POWER",wave,5))
    weave = math_node("MAXIMUM",*ridges)
    colour = nodes.new("ShaderNodeValToRGB")
    colour.color_ramp.elements[0].color = (0.003,0.004,0.005,1)
    colour.color_ramp.elements[1].color = (0.011,0.015,0.019,1)
    links.new(weave,colour.inputs[0])
    links.new(colour.outputs["Color"],bsdf.inputs["Base Color"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.38
    bump.inputs["Distance"].default_value = 0.00012
    links.new(weave,bump.inputs["Height"])
    links.new(bump.outputs["Normal"],bsdf.inputs["Normal"])
    panel = material("O89 | Wiring example housings", (0.014, 0.020, 0.025), 0.5)
    # Layout labels remain legible under the wide camera's softer illumination.
    label_mat = material("O89 | Wiring typography", (0.56, 0.63, 0.67), 0.65)
    bsdf = label_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Emission Color"].default_value = (0.56, 0.63, 0.67, 1)
    bsdf.inputs["Emission Strength"].default_value = 0.45

    def visible(obj, mode):
        expression = {"beauty": "not show or layout", "layout": "not show or not layout",
                      "both": "not show"}[mode]
        visibility(obj, {"show": "show_cables", "layout": "show_bus_layout"}, expression)

    def cable(name, points, radius, mat=rubber, mode="beauty", extend=False):
        points = list(points)
        if extend:
            points.append((points[-1][0], -0.40, points[-1][2]))
        curve = bpy.data.curves.new(name, "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 12 if len(points) < 20 else 3
        curve.bevel_resolution = 4
        curve.bevel_depth = radius
        curve.use_fill_caps = True
        spline = curve.splines.new("BEZIER")
        spline.bezier_points.add(len(points)-1)
        for bp, point in zip(spline.bezier_points, points):
            bp.co = point
            bp.handle_left_type = bp.handle_right_type = "AUTO"
        obj = bpy.data.objects.new(name, curve)
        groups["wiring" if mode == "layout" else "cables"].objects.link(obj)
        curve.materials.append(mat)
        parent_to(obj, root)
        visible(obj, mode)
        obj["source_kind"] = "conceptual bus layout" if mode == "layout" else "render cable routing"
        return obj

    def label(body, x, y, size=0.004, align="LEFT", z=0.012):
        data = bpy.data.curves.new("Wiring | " + body, "FONT")
        data.body, data.size = body, size
        data.align_x, data.align_y = align, "CENTER"
        data.space_character = 1.05
        obj = bpy.data.objects.new(data.name, data)
        groups["wiring"].objects.link(obj)
        obj.location = (x, y, z)
        data.materials.append(label_mat)
        parent_to(obj, root)
        visible(obj, "layout")
        return obj

    # Small service breakouts: one twisted signal pair and a third conductor.
    # Pin 1 is left at these bottom connectors in the board's top-view frame.
    def breakout(ref, x, wire_bus=False, mode="beauty", can_bus=False):
        pair_x = x + (0.00175 if wire_bus else -0.00175)
        pair_mat = grey if can_bus else (blue if wire_bus else orange)
        pins = (2, 3) if wire_bus else (1, 2)
        paths = []
        for phase, pin, mat in ((0, pins[0], pair_mat), (math.pi, pins[1], white)):
            points = []
            for i in range(73):
                t = i/72
                angle = phase + t*math.tau*1.8
                centre_x = x + (pair_x-x)*min(1.0,t*5)
                points.append((centre_x + math.cos(angle)*0.00055,
                               -0.097+t*0.017, 0.0055+math.sin(angle)*0.00055))
            pin_x = x+(pin-2)*0.0035
            points.extend(((pin_x, -0.076, 0.0055), (pin_x, -0.0705, 0.0055)))
            obj = cable(ref+" | twisted conductor pin "+str(pin), points, 0.00047, mat, mode)
            obj["net"] = ("OW_DATA_F" if pin == 2 else "GND") if wire_bus else ("A" if pin == 1 else "B")
            if can_bus:
                obj["net"] = "CANH" if pin == 1 else "CANL"
            paths.append(points)
        # A thin coloured tracer identifies the white conductor's pair.
        stripe = [(px+0.00014, py, pz+0.00045) for px,py,pz in paths[1]]
        cable(ref+" | white conductor colour tracer", stripe, 0.00008, pair_mat, mode)
        third_pin = 1 if wire_bus else 3
        third_x = x + (third_pin-2)*0.0035
        obj = cable(ref+" | "+("OW_VCC" if wire_bus else "GND"),
            [(x+(-0.0009 if wire_bus else 0.0009),-0.097,0.005),
             (third_x,-0.082,0.005),(third_x,-0.0705,0.0055)],
            0.00047, orange if wire_bus else green, mode)
        obj["pin"] = third_pin

    # A two-dimensional bundle keeps the actual jackets inside the common sleeve.
    # Positions are (x,z), in metres; the sleeve centre is z=9.6 mm.
    bundle = [(-0.006,0.0050),(-0.006,0.0108),(0.000,0.0050),
              (0.000,0.0108),(0.006,0.0050),(0.006,0.0108)]
    left_bundle = [(-0.0095,0.0090),(-0.006,0.0153),(-0.002,0.0153)]
    right_bundle = [(0.004,0.0153),(0.0096,0.0098)]
    for i, x_mm in enumerate((-34,-21,-8,5,18,31)):
        x = x_mm/1000
        end_x,end_z = bundle[i]
        is_cat5 = i in (1,2,3,5)
        if is_cat5:
            breakout("CN"+str({1:2,2:3,3:4,5:8}[i]), x, i == 5,
                     "both" if i in (1,5) else "beauty")
        elif i == 4:
            breakout("CN5", x, can_bus=True)
        if i == 0:
            for offset, mat, net in ((-0.00254,red,"V_IN_RAW"),(0.00254,rubber,"GND")):
                cable("CN1 | "+net,[(x+offset,-0.073,0.0055),(x+offset,-0.081,0.0055),
                      (x+offset*0.3,-0.091,0.0055)],0.0009,mat,"both")
        start_y = -0.089 if i == 0 else -0.096
        obj = cable("Harness | Bottom " + str(i+1), [(x,start_y,0.0055),
            (x*0.60+end_x*0.40,-0.119,0.0055*0.60+end_z*0.40),
            (end_x,-0.146,end_z),(end_x,-0.180,end_z),(end_x,-0.245,end_z)],
            0.0026 if is_cat5 else (0.0025 if i == 0 else 0.0018), jacket if is_cat5 else rubber, extend=True)
        obj["cable_type"] = "Cat5e illustration - 5.2 mm OD" if is_cat5 else ("Dedicated DC power" if i == 0 else "Dedicated CAN twisted-pair cable")
    for i, (name, y_mm) in enumerate((("SEL",14),("SNS",-14.5),("TNK",-28))):
        y, side_x = y_mm/1000, -0.075-(2-i)*0.004
        rail_x = -0.0818+i*0.0028
        end_x,end_z = left_bundle[i]
        pins = 2 if name == "SNS" else 3
        for pin in range(pins):
            pin_y = y+(pin-(pins-1)/2)*0.0035
            cable("Harness | Left "+name+" conductor "+str(pin+1),
                [(-0.059,pin_y,0.0058),(-0.064,pin_y,0.0058),(-0.072,y-0.003,0.0058)],0.00044)
        cable("Harness | Left "+name,[(-0.071,y-0.003,0.0058),(side_x,y-0.005,0.0058),
            (rail_x,-0.066,0.006),(rail_x+0.004,-0.091,0.006),(-0.047+i*0.002,-0.120,0.006),
            (end_x,-0.146,end_z),(end_x,-0.180,end_z),(end_x,-0.245,end_z)],0.00115,extend=True)
    for i, y_mm in enumerate((0,-41.5)):
        y = y_mm/1000
        end_x,end_z = right_bundle[i]
        cable("Harness | Right VE.Direct "+str(i+1),[(0.047,y,0.007),(0.047,y,0.014),
            (0.073+i*0.003,y-0.009,0.015),(0.076+i*0.0028,-0.066,0.008),
            (0.071+i*0.002,-0.091,0.008),(0.045+i*0.002,-0.119,0.007),
            (end_x,-0.146,end_z),(end_x,-0.180,end_z),(end_x,-0.245,end_z)],0.00105,extend=True)

    def management_visibility(obj):
        visibility(obj,{"show":"show_cables","layout":"show_bus_layout","wrap":"show_cable_sleeve"},
                   "not show or layout or not wrap")

    def sleeve(name, rings, mat, centre_x=0, centre_z=0.0096, thickness=0.0006):
        # Open-ended mesh rings with UVs keep the mouth hollow and the weave editable.
        segments = 96
        vertices, faces = [],[]
        for y,rx,rz in rings:
            for i in range(segments):
                angle = math.tau*i/segments
                vertices.append((centre_x+rx*math.cos(angle),y,centre_z+rz*math.sin(angle)))
        for ring in range(len(rings)-1):
            for i in range(segments):
                j = (i+1)%segments
                faces.append((ring*segments+i,ring*segments+j,(ring+1)*segments+j,(ring+1)*segments+i))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices,[],faces)
        mesh.update()
        uv_map = mesh.uv_layers.new(name="Braided sleeve UV")
        for polygon in mesh.polygons:
            ring,i = divmod(polygon.index,segments)
            v0 = (rings[0][0]-rings[ring][0])/(rings[0][0]-rings[-1][0])
            v1 = (rings[0][0]-rings[ring+1][0])/(rings[0][0]-rings[-1][0])
            for loop,coord in zip(polygon.loop_indices,((i/segments,v0),((i+1)/segments,v0),((i+1)/segments,v1),(i/segments,v1))):
                uv_map.data[loop].uv = coord
            polygon.use_smooth = True
        obj = bpy.data.objects.new(name,mesh)
        groups["management"].objects.link(obj)
        mesh.materials.append(mat)
        parent_to(obj,root)
        solidify = obj.modifiers.new("Sleeving wall thickness","SOLIDIFY")
        solidify.thickness = thickness
        solidify.offset = -1
        management_visibility(obj)
        obj["source_kind"] = "render cable management - illustrative"
        return obj

    sleeve("Management | Common braided sleeve",[
        (-0.145,0.014,0.014),(-0.152,0.0128,0.0128),
        (-0.166,0.0125,0.0125),(-0.245,0.0125,0.0125),(-0.420,0.0125,0.0125)],braid)
    sleeve("Management | Sleeve mouth hem",[
        (-0.1445,0.0142,0.0142),(-0.1462,0.0140,0.0140)],strap_mat,thickness=0.00045)
    sleeve("Management | Sleeve retaining band",[
        (-0.161,0.0131,0.0131),(-0.165,0.0131,0.0131)],strap_mat,thickness=0.0005)
    for name,cx,cz,rx,rz in (("Left",-0.079,0.006,0.0048,0.0023),
                             ("Right",0.0774,0.008,0.0034,0.0022)):
        sleeve("Management | "+name+" cable retaining strap",[
            (-0.064,rx,rz),(-0.068,rx,rz)],strap_mat,cx,cz,0.0005)
        clasp = box("Management | "+name+" strap clasp",(cx,-0.066,cz+rz+0.0002),
            (0.0035,0.0048,0.0008),strap_mat,"management",root,edge=0.00025)
        management_visibility(clasp)
        clasp["source_kind"] = "render cable management - illustrative"

    # Independent teaching layout, using the same three physical connector tails.
    # RS-485 enters/exits devices along one trunk; 1-Wire uses short sensor taps.
    cable("Layout | Dedicated 12 V",[(-0.034,-0.089,0.0055),(-0.040,-0.118,0.006),
          (-0.070,-0.150,0.006)],0.0025,mode="layout")
    cable("Layout | RS485 1 feed",[(-0.021,-0.096,0.0055),(-0.012,-0.126,0.006),
          (0.060,-0.139,0.006),(0.138,-0.139,0.006)],0.0026,jacket,"layout")
    for start, end in ((0.182,0.268),(0.312,0.398)):
        cable("Layout | RS485 continuation",[(start,-0.139,0.006),(end,-0.139,0.006)],0.0026,jacket,"layout")
    for n, x in enumerate((0.16,0.29,0.42),1):
        obj = box("Layout | RS485 device "+str(n),(x,-0.139,0.010),(0.044,0.048,0.017),panel,"wiring",root,edge=0.003)
        visible(obj,"layout")
        label("0"+str(n),x,-0.133,0.006,"CENTER",0.019)
        label("RS-485",x,-0.147,0.0028,"CENTER",0.019)
        label("DEVICE "+str(n),x,-0.178,0.0034,"CENTER")
    label("RS-485 / ONE BUS, SEVERAL DEVICES",0.130,-0.069,0.0056)
    label("Cat5e twisted pair  /  daisy chain",0.130,-0.085,0.0038)
    label("Termination at the two bus ends",0.130,-0.196,0.0035)
    cable("Layout | 1-Wire main trunk",[(0.031,-0.096,0.0055),(0.040,-0.112,0.006),
          (0.081,-0.102,0.006),(0.099,-0.070,0.006),(0.099,0.005,0.006),
          (0.128,0.026,0.006),(0.160,0.026,0.006),(0.440,0.026,0.006)],0.0026,jacket,"layout")
    label("1-WIRE / ONE BUS, SEVERAL SENSORS",0.130,0.080,0.0056)
    label("Cat5e twisted pair  /  short sensor taps",0.130,0.064,0.0038)
    for n, x in enumerate((0.16,0.29,0.42),1):
        cable("Layout | 1-Wire short tap "+str(n),[(x,0.026,0.006),(x,0.011,0.006)],0.00125,rubber,"layout")
        obj = box("Layout | sensor tap "+str(n),(x,0.026,0.006),(0.009,0.007,0.007),panel,"wiring",root,edge=0.001)
        visible(obj,"layout")
        # Probe geometry is an illustrative sensor, not imported device CAD.
        cable("Layout | Temperature probe "+str(n),[(x,0.011,0.006),(x,-0.013,0.006)],0.003,steel,"layout")
        label("SENSOR "+str(n),x,-0.032,0.0034,"CENTER")
    label("FIELD WIRING",-0.078,0.139,0.009)
    label("One jacket. Multiple devices.",-0.078,0.119,0.0042)
    label("12 V",-0.078,-0.164,0.0042)
    label("Separate power cable",-0.078,-0.175,0.0032)
    label("BUS TOPOLOGY CONCEPT  /  distances not to scale",-0.078,-0.217,0.0031)

    notes = bpy.data.texts.new("Cable conventions and bus layout")
    notes.write("""CABLE VISUALS / PROPOSED CONVENTION
Cat5e shown only for the three RS-485 ports and bottom 1-Wire.
RS-485: orange=A (pin 1), white/orange=B (2), green=GND (3).
1-Wire: orange=OW_VCC (1), blue=OW_DATA_F (2), white/blue=GND (3).
CAN: grey=CANH (1), white/grey=CANL (2), green=GND (3); dedicated jacket.
Remaining Cat5e cores stay insulated inside the jacket in this illustration.
Colours are a proposed convention, not a standard Cat5e/Ethernet bus pinout.
Pin order: PAD_NET records in ProPrj_origin89_2026-08-31.epro2, PCB document.
CN8 and CN11 share OW_VCC, OW_DATA_F and GND; they are not separate buses.
12 V uses a separate power cable. LNK requires the specified VH harness;
VE.Direct uses dedicated leads. CAN and the left-side leads are separate.

The presentation harness converges into a common 25 mm braided sleeve.
Every lead keeps its individual jacket; the sleeve is an outer organiser.
Side retaining straps gather the leads before the shared downward run.
O89 Controls > show_cable_sleeve hides the sleeve and straps for editing.
Sleeve diameter, texture and strap placement are visual design choices.

Wiring view is a conceptual bus layout with illustrative device bodies.
RS-485 is a daisy chain; termination belongs at the two bus ends, matched
to the cable and transceiver configuration. The 1-Wire trunk has short taps.
No maximum distance, device count, power budget or arbitrary star is implied.
Actual cable selection depends on length, driver, environment and connectors.
""")
