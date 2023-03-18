import argparse
import math
import random
import os
from matplotlib.patches import Polygon
from shapely import geometry
from anytree import Node, AnyNode, RenderTree
from tqdm import tqdm
from xml.dom import minidom
import svg.path
import json
import collections

point = collections.namedtuple('point', ['x', 'y'])


def prepare_svg(doc):
    paths = []
    for element in doc.getElementsByTagName("path"):
        paths.extend(list(svg.path.parse_path(element.getAttribute("d"))))

    # print(paths)
    result = []
    last_move = 0
    for i in paths[1:]:
        if isinstance(i, svg.path.Move):
            # print(paths[last_move:paths.index(i)], paths.index(i))
            result.append(paths[last_move:paths.index(i)])
            last_move = paths.index(i)
    result.append(paths[last_move:len(paths) - 1])
    return result


def get_point_at(path, distance):
    pos = path.point(distance)
    return point(round(pos.real, 6), -round(pos.imag, 6))


def points_from_doc(doc, density=1):
    paths = prepare_svg(doc)
    points = []

    # for element in doc.getElementsByTagName("path"):
    #     paths.append(list(svg.path.parse_path(element.getAttribute("d"))))

    # print(paths)

    total = 0
    for sublist in paths:
        total += len(sublist)
        points.append([])

    pgbar = tqdm(desc="parsing polygons from svg", total=total, unit="paths")
    for i in range(len(paths)):
        index = 0
        for j in range(len(paths[i])):
            if pgbar is not None:
                pgbar.update()
            step = int(paths[i][j].length() * density)
            for k in range(0, step + 1):
                try:
                    distance = k / (step)
                except ZeroDivisionError:
                    distance = 0
                args = paths[i][j], distance
                points[i].append(get_point_at(*args))
                # processes.append(Process(target=get_point_at, args=args))
            index += step + 1

    # for i in processes:
    #     i.start()
    # for i in processes:
    #     i.join()
    pgbar.close()
    return points


def getDoc(path):
    try:
        print("opening ", path)
        return minidom.parseString(open(path).read())
    except Exception as e:
        print(e)
        print("maybe you tried to open something as an svg that is not and svg. try the -i flag")


def PyQt_display(inp, lines):
    try:
        import sys
        from PyQt5.QtWidgets import QApplication
        import pyqtgraph as pg
    except ImportError:
        print("missing PyQt dependencies. See the githubpage for help")
    else:
        App = QApplication.instance()
        if not App:
            App = QApplication(sys.argv)
        plot = pg.plot()
        # screen = pg.ScatterPlotItem()
        # plot.addItem(screen)
        # for path in inp:
        #     screen.addPoints(pos=path, pen=inp.index(path))
        if lines:
            legend = pg.LegendItem((80, 60), offset=(70, 20))
            legend.setParentItem(plot.graphicsItem())

            for path in inp:
                x = [i[0] for i in path]
                y = [i[1] for i in path]

                legend.addItem(plot.plot(x, y, pen=inp.index(
                    path)), f"{inp.index(path) + 1}")
        else:
            screen = pg.ScatterPlotItem()
            plot.addItem(screen)
            for path in inp:
                screen.addPoints(pos=path, pen=inp.index(path))

        pg.show()


def scale_offset_mirror(inp, scale, offset, dont_mirror):
    for poly in range(len(inp)):
        for p in range(len(inp[poly])):
            if dont_mirror:
                inp[poly][p] = point(
                    (inp[poly][p][0] + offset[0]) * scale, (inp[poly][p][1] + offset[1]) * scale)
            else:
                inp[poly][p] = point(
                    (-inp[poly][p][0] + offset[0]) * scale, (inp[poly][p][1] + offset[1]) * scale)
    return inp


def remove_duplicate_points_from_path(inp, pgbar=None):
    # print("removing duplicate points")
    result = []
    for i in range(1, len(inp) - 1):
        if not pointAreClose(inp[i], inp[i + 1]) and not pointAreClose(inp[i], inp[0]):
            result.append(inp[i])
        if pgbar is not None:
            pgbar.update()
    return [inp[0]] + result + [inp[0]]


def remove_duplicate_points(inp):
    max_points = sum([len(i) for i in inp])
    pgbar = tqdm(desc="removing duplicate points",
                 total=max_points, unit="points")
    result = []
    for i in inp:
        result.append(remove_duplicate_points_from_path(i, pgbar))
    pgbar.close()
    return result


def pointAreClose(a, b):
    return (math.isclose(a.x, b.x) and math.isclose(a.y, b.y))


def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def is_between(a, c, b):
    if (math.isclose(a[0], b[0]) and math.isclose(b[0], c[0])) or (
        math.isclose(a[1], b[1]) and math.isclose(b[1], c[1])):
        return True
    else:
        crossproduct = (c.y - a.y) * (b.x - a.x) - (c.x - a.x) * (b.y - a.y)

        # compare versus epsilon for floating point values, or != 0 if using integers
        if abs(crossproduct) > 0.001:
            return False

        dotproduct = (c.x - a.x) * (b.x - a.x) + (c.y - a.y) * (b.y - a.y)
        if dotproduct < 0:
            return False

        squaredlengthba = (b.x - a.x) * (b.x - a.x) + (b.y - a.y) * (b.y - a.y)
        if dotproduct > squaredlengthba:
            return False

        return True


def remove_redundant_points_from_path(inp, pgbar):
    if inp == []:
        return []
    result = []
    for i in range(1, len(inp) - 1):
        if not is_between(inp[i - 1], inp[i], inp[i + 1]):
            result.append(inp[i])
        if pgbar is not None:
            pgbar.update()
    return [inp[0]] + result + [inp[0]]


def remove_redundant_points(inp):
    max_points = sum([len(i) for i in inp])
    pgbar = tqdm(desc="removing redundant points",
                 total=max_points, unit="points")
    result = []
    for i in inp:
        result.append(remove_redundant_points_from_path(i, pgbar))
    pgbar.close()
    return result


def polygon_in_polygon(polygona, polygonb):
    polygona = geometry.Polygon(polygona)
    polygonb = geometry.Polygon(polygonb)
    return polygona.contains(polygonb)


def get_closest_points(polygona, polygonb):
    pointa = 0
    pointb = 0
    current_distance = distance(polygona[0], polygonb[0])
    for a in polygona:
        for b in polygonb:
            dist = distance(a, b)
            if dist < current_distance:
                current_distance = distance(a, b)
                pointa = polygona.index(a)
                pointb = polygonb.index(b)
    return pointa, pointb


def stich_hole_into_polygon(hole, polygon):
    h, p = get_closest_points(hole, polygon)
    return polygon[:p + 1] + hole[h:] + hole[:h + 1] + polygon[p:]


def pop_bubbles(inp):
    inp = dict(enumerate(inp))
    pgbar = tqdm(desc="popping bubbles", total=(
                                                   len(inp) * 2) + 2, unit="polygons")

    def push_down(node: Node, pgbar):
        pgbar.update()
        for child in node.children:
            for child2 in child.siblings:
                if polygon_in_polygon(inp[child2.name], inp[child.name]):
                    child2.children += tuple([child])
        for i in node.children:
            push_down(i, pgbar)

    def pull_up(node: Node, pgbar):
        pgbar.update()
        if node.name != -1 and len(node.ancestors) % 2 == 1:
            for i in node.children:
                pull_up(i, pgbar)
                inp[node.name] = stich_hole_into_polygon(
                    inp[i.name], inp[node.name])
                inp.pop(i.name)

        else:
            for i in node.children:
                pull_up(i, pgbar)

    tree = Node(-1)
    tree.children = reversed(tuple(map(Node, inp.keys())))
    push_down(tree, pgbar)
    pull_up(tree, pgbar)
    pgbar.close()
    return list(inp.values())


def generateScript(inp, script_path, width=0.1, name="menga", layer="bplace", wire_bend=2):
    total = 0
    for path in inp:
        for point in path:
            total += 1
    pgbar = tqdm(desc="generating script", total=total, unit="points")
    script = f"set wire_bend {wire_bend};CHANGE layer {layer}; CHANGE rank 3; CHANGE pour solid\n"
    for path in inp:
        if len(path) > 2:
            script += f"polygon {name} {width}mm "
            for point in path:
                pgbar.update()
                script += f" ({round(point.x, 3)}mm {round(point.y, 3)}mm) "
            script += ";\n"
    open(script_path, "w").write(script)
    pgbar.close()
    print("script was saved to ", script_path)


def exportPoints(array, path):
    json.dump(array, open(path, "w"), indent=2)
    print("copy of the polygonsa saved to ", path)


def importPoints(path):
    data = json.load(open(path))
    for i in range(len(data)):
        for j in range(len(data[i])):
            data[i][j] = point(*data[i][j])
    print("imported polygon data from ", path)
    return data


mylist = []


def svg2eagle(
    source,
    destination="",

    density=1,
    scale=1,
    offset=(0, 0),
    dont_mirror=True,

    import_polygons=False,

    export_polygons=False,

    dont_pop_bubbles=False,
    dont_remove_duplicates=False,
    dont_remove_redundancies=False,

    width=0.1,
    name="menga",
    layer="bplace",
    wire_bend=2,

    preview_dots=True,
    preview_lines=True,
):
    global mylist
    if destination == "":
        if exportPoints:
            destination = "points.json"
        else:
            destination = "script.scr"
    source = os.path.abspath(source)
    destination = os.path.abspath(destination)

    if not os.path.isfile(source):
        raise FileNotFoundError(f"{source} was not found")

    if os.path.isdir(destination):
        destination = os.path.join(destination, "script.scr")

    if import_polygons:
        mylist = importPoints(source)
    else:
        mylist = points_from_doc(getDoc(source), density=density)
    mylist = scale_offset_mirror(mylist, scale, offset, dont_mirror)
    if not dont_pop_bubbles:
        mylist = pop_bubbles(mylist)
    if not dont_remove_duplicates:
        mylist = remove_duplicate_points(mylist)
    if not dont_remove_redundancies:
        mylist = remove_redundant_points(mylist)
    if preview_dots:
        PyQt_display(mylist, False)
    if preview_lines:
        PyQt_display(mylist, True)
    if export_polygons:
        exportPoints(mylist, destination)
    else:
        generateScript(mylist, destination, width=width,
                       name=name, layer=layer, wire_bend=wire_bend)


def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--density", default=1, type=float, required=False,
                    help="how many points per mm should be generated on each line")
    ap.add_argument("-s", "--scale", default=1, type=float,
                    required=False, help="scale multiplier")
    ap.add_argument("-o", "--offset", default=(0, 0), type=float,
                    required=False, help="offset the points by:", nargs=2)
    ap.add_argument("-m", "--dont-mirror", action="store_true", required=False, help="don't mirror the polygon." +
                                                                                     "(use it if you want to print on the front of a circuit. default is back but you can change it by changing the layer)")

    ap.add_argument("-i", "--import-polygons", action="store_true", required=False,
                    help="import polygons instead of generating it from an svg")

    ap.add_argument("-e", "--export-polygons", action="store_true",
                    required=False, help="export polygons instead of generating the scipt")

    ap.add_argument("-b", "--dont-pop-bubbles", action="store_true",
                    required=False, help="don't remove pop bubbles that form inside the polygon-formations")
    ap.add_argument("-x", "--dont-remove-duplicates", action="store_true",
                    required=False, help="don't remove duplicate points from the polygon")
    ap.add_argument("-X", "--dont-remove-redundancies", action="store_true", required=False,
                    help="dont't remove redunatnd points from the polygon" +
                         "(for now this only means points that are on a straight line and dont change the line angle get removed as they are useless)")

    ap.add_argument("-w", "--width", default=0.1, type=float,
                    required=False, help="line width in EAGLE™")
    ap.add_argument("-n", "--name", default="menga", type=str,
                    required=False, help="name of the generated polygons")
    ap.add_argument("-l", "--layer", default="bplace", type=str, required=False,
                    help="layer the polygons will be printed on " +
                         "('tplace' is the top slkscreen, while 'bplace' is the bottom silkscreen. Note that if you are printing" +
                         "somrthing on the back of a circuit you need to mirror it)")
    ap.add_argument("-j", "--wire-bend", default=2, choices=['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'],
                    required=False, help="type of wire bend to be used")

    ap.add_argument("-p", "--preview-dots", action="store_true", required=False,
                    help="preview the polygon dots before generating the script. (faster)" +
                         "(needs pyqtgraph, pyqt and its dependecies installed. See the github page for help)")
    ap.add_argument("-P", "--preview-lines", action="store_true", required=False,
                    help="preview the polygons lines before generating the script. (slower)" +
                         "(needs pyqtgraph, pyqt and its dependecies installed. See the github page for help)")

    ap.add_argument("source", type=str,
                    help="path to source svg or to import json")
    ap.add_argument("destination", default="", type=str,
                    help="destination path for export or script")

    print(json.dumps(vars(ap.parse_args()), indent=2))
    svg2eagle(**vars(ap.parse_args()))


class Tee:
    def __init__(self, variable, terminal, window):
        self.variable = variable
        self.terminal = terminal
        self.window = window

    def write(self, data):
        self.variable.append(data)
        self.terminal.write(data)
        self.terminal.flush()
        self.window.updateConsoleOutput()

    def writelines(self, data):
        self.variable.extend(data)
        self.terminal.writelines(data)
        self.terminal.flush()
        self.window.updateConsoleOutput()

    def flush(self, *args, **kwargs):
        pass


def gui():
    try:
        import traceback
        import sys
        from PyQt5 import QtGui
        from PyQt5.QtCore import Qt, QTimer, QStringListModel, QThread, QSettings
        from PyQt5.QtGui import QKeyEvent, QPixmap, QPalette, QImage, QColor, QIcon
        from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QTabWidget, \
            QGridLayout, QTextEdit, QComboBox, QCompleter, QLineEdit, QMainWindow, QSplitter, QListWidget, QGroupBox, \
            QRadioButton, \
                QSpinBox, QDoubleSpinBox, QComboBox, QLabel, QSizePolicy, QFileDialog, QListWidgetItem

    except ImportError:
        print("missing PyQt dependencies. See the githubpage for help")
    else:
        output = []

        class MainWindow(QWidget):
            def __init__(self):
                super().__init__()

                sp = QWidget().sizePolicy()
                sp.setHorizontalPolicy(QSizePolicy.Minimum)

                self.setWindowFlag(Qt.Dialog)

                self.settings = QSettings("menga", "svg2eagleGUI", self)
                self.settings.sync()
                print(self.settings.value("input_path", os.getenv('~'), str))

                self.input_path = self.settings.value("input_path", os.getenv('~'), str)
                self.output_path = self.settings.value("output_path", os.getenv('~'), str)

                self.splitter = QSplitter()
                self.options_layout = QVBoxLayout()
                self.iofile_layout = QVBoxLayout()


                self.inputs = json.loads(self.settings.value("input_paths", "[]", str))
                self.outputs = json.loads(self.settings.value("output_paths", "[]", str))

                self.input_file_list = QListWidget()
                # self.input_file_list.setToolTip("single click to set a path as inputs, double click to set it as output")
                self.input_file_list_add_to_input_button = QPushButton()
                self.input_file_list_add_to_input_button.setText("Add to input")
                self.input_file_list_add_to_input_button.clicked.connect(self.input_file_list_add_to_input)
                self.input_file_list_add_to_output_button = QPushButton()
                self.input_file_list_add_to_output_button.setText("Add to output")
                self.input_file_list_add_to_output_button.clicked.connect(self.input_file_list_add_to_output)
                self.output_file_list = QListWidget()
                # self.output_file_list.setToolTip("single click to set a path as inputs, double click to set it as output")
                self.output_file_list_add_to_input_button = QPushButton()
                self.output_file_list_add_to_input_button.setText("Add to input")
                self.output_file_list_add_to_input_button.clicked.connect(self.output_file_list_add_to_input)
                self.output_file_list_add_to_output_button = QPushButton()
                self.output_file_list_add_to_output_button.setText("Add to output")
                self.output_file_list_add_to_output_button.clicked.connect(self.output_file_list_add_to_output)

                self.input_list_layout = QVBoxLayout()
                self.input_buttons_layout = QHBoxLayout()

                self.input_buttons_layout.addWidget(self.input_file_list_add_to_input_button)
                self.input_buttons_layout.addWidget(self.input_file_list_add_to_output_button)
                self.input_list_layout.addWidget(self.input_file_list)
                self.input_list_layout.addLayout(self.input_buttons_layout)

                self.output_list_layout = QVBoxLayout()
                self.output_buttons_layout = QHBoxLayout()

                self.output_buttons_layout.addWidget(self.output_file_list_add_to_input_button)
                self.output_buttons_layout.addWidget(self.output_file_list_add_to_output_button)
                self.output_list_layout.addWidget(self.output_file_list)
                self.output_list_layout.addLayout(self.output_buttons_layout)

                self.iofile_layout = QVBoxLayout()

                self.iofile_layout.addLayout(self.input_list_layout)
                self.iofile_layout.addLayout(self.output_list_layout)
                w = QWidget()
                w.setLayout(self.iofile_layout)
                self.splitter.addWidget(w)






                self.files_group = QGroupBox()
                self.files_layout = QVBoxLayout()
                self.input_layout = QHBoxLayout()
                self.output_layout = QHBoxLayout()
                self.files_group.setTitle("Files")

                self.browse_button = QPushButton()
                self.browse_button.setText("Browse")
                self.browse_button.setToolTip("Clck here to select an input file")
                self.browse_button.clicked.connect(self.browse_files)
                self.browse_button.setMaximumWidth(65)
                self.input_warning_label = QLabel()
                self.save_button = QPushButton()
                self.save_button.setText("Save as")
                self.save_button.setToolTip("Clck here to select an output file")
                self.save_button.clicked.connect(self.save_as_file)
                self.save_button.setMaximumWidth(65)
                self.output_warning_label = QLabel()

                self.input_layout.addWidget(self.browse_button)
                self.input_layout.addWidget(self.input_warning_label)
                self.output_layout.addWidget(self.save_button)
                self.output_layout.addWidget(self.output_warning_label)

                self.files_layout.addLayout(self.input_layout)
                self.files_layout.addLayout(self.output_layout)
                self.files_layout.setAlignment(Qt.AlignLeft)

                self.files_group.setLayout(self.files_layout)

                self.options_layout.addWidget(self.files_group)

                self.polygon_settings_group = QGroupBox()
                self.polygon_settings_layout = QVBoxLayout()
                self.polygon_settings_group.setTitle("Polygon Settings")

                self.density_spinbox = QDoubleSpinBox()
                self.density_spinbox.setToolTip("how many points per mm should be generated on each line")
                self.density_spinbox.setSingleStep(1)
                self.density_spinbox.setValue(1)
                self.scale_spinbox = QDoubleSpinBox()
                self.scale_spinbox.setToolTip(
                    "scale muliplier \n (0.5 will halfe the size of the polygon and 2 will double the size polygon)")
                self.scale_spinbox.setSingleStep(0.5)
                self.scale_spinbox.setValue(1)
                self.xofffset_spinbox = QDoubleSpinBox()
                self.scale_spinbox.setToolTip("x offset")
                self.xofffset_spinbox.setSingleStep(50)
                self.xofffset_spinbox.setValue(0)
                self.xofffset_spinbox.setMaximum(999999)
                self.yofffset_spinbox = QDoubleSpinBox()
                self.scale_spinbox.setToolTip("y offset")
                self.yofffset_spinbox.setSingleStep(50)
                self.yofffset_spinbox.setValue(0)
                self.yofffset_spinbox.setMaximum(999999)
                self.mirror_button = QRadioButton()
                self.mirror_button.setText("mirror polygon")
                self.scale_spinbox.setToolTip(
                    "with this enabled hte polygon will be mirrored along the y axis \n (use it if you want to print on the front of a circuit. default is back but you can change it by changing the layer)")
                self.mirror_button.setAutoExclusive(False)

                self.density_layout = QHBoxLayout()
                self.density_layout.addWidget(self.density_spinbox)
                self.density_layout.addWidget(QLabel("point density"))

                self.scale_layout = QHBoxLayout()
                self.scale_layout.addWidget(self.scale_spinbox)
                self.scale_layout.addWidget(QLabel("scale multiplier"))

                self.offfset_layout = QHBoxLayout()
                self.offfset_layout.addWidget(QLabel("x"))
                self.offfset_layout.addWidget(self.xofffset_spinbox)
                self.offfset_layout.addWidget(QLabel("y"))
                self.offfset_layout.addWidget(self.yofffset_spinbox)
                self.offfset_layout.addWidget(QLabel("polygon offset"))

                self.polygon_settings_layout.addLayout(self.density_layout)
                self.polygon_settings_layout.addLayout(self.scale_layout)
                self.polygon_settings_layout.addLayout(self.offfset_layout)
                self.polygon_settings_layout.addWidget(self.mirror_button)
                self.polygon_settings_layout.setAlignment(Qt.AlignLeft)

                self.polygon_settings_group.setLayout(self.polygon_settings_layout)

                self.options_layout.addWidget(self.polygon_settings_group)

                self.correction_group = QGroupBox()
                self.correction_layout = QHBoxLayout()
                self.correction_group.setTitle("Corrections")

                self.pop_bubbles_button = QRadioButton()
                self.pop_bubbles_button.setText("pop bubbles")
                self.pop_bubbles_button.setToolTip(
                    "pop bubbles that form inside the polygon-formations \n (only disable this if the operation takes to long and you are willing to do it manually in inkscape)")
                self.pop_bubbles_button.setAutoExclusive(False)
                self.pop_bubbles_button.setChecked(True)
                self.remove_duplicates_button = QRadioButton()
                self.remove_duplicates_button.setText("remove duplicates")
                self.remove_duplicates_button.setToolTip("removes duplicate points in the polygon")
                self.remove_duplicates_button.setAutoExclusive(False)
                self.remove_duplicates_button.setChecked(True)
                self.remove_redundancies_button = QRadioButton()
                self.remove_redundancies_button.setText("remove redundancies")
                self.remove_redundancies_button.setToolTip(
                    "remove redunatnd points from the polygon \n (for now this only means points that are on a straight line and dont change the line angle get removed as they are useless)")
                self.remove_redundancies_button.setAutoExclusive(False)
                self.remove_redundancies_button.setChecked(True)

                self.correction_layout.addWidget(self.pop_bubbles_button)
                self.correction_layout.addWidget(self.remove_duplicates_button)
                self.correction_layout.addWidget(self.remove_redundancies_button)
                self.correction_layout.setAlignment(Qt.AlignLeft)

                self.correction_group.setLayout(self.correction_layout)

                self.options_layout.addWidget(self.correction_group)

                self.eagle_settings_group = QGroupBox()
                self.eagle_settings_layout = QVBoxLayout()
                self.eagle_settings_group.setTitle("EAGLE settings")

                self.width_spinbox = QDoubleSpinBox()
                self.width_spinbox.setToolTip("line width in EAGLE™")
                self.width_spinbox.setSingleStep(0.1)
                self.width_spinbox.setValue(0.1)
                self.polygon_name_box = QLineEdit()
                self.polygon_name_box.setToolTip("name of the generated polygons")
                self.polygon_name_box.setSizePolicy(sp)
                self.polygon_name_box.setText("menga")
                self.layer_box = QLineEdit()
                self.layer_box.setToolTip(
                    "layer the polygons will be printed on \n('tplace' is the top slkscreen, while 'bplace' is the bottom silkscreen. Note that if you are printing somrthing on the back of a circuit you need to mirror it)")
                self.layer_box.setSizePolicy(sp)
                self.layer_box.setText("tplace")
                self.wirebend_selector = QComboBox()
                self.wirebend_selector.setToolTip("type of wire bend to be used")
                self.wirebend_selector.addItems(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])
                self.wirebend_selector.setCurrentIndex(2)

                self.width_layout = QHBoxLayout()
                self.width_layout.addWidget(self.width_spinbox)
                self.width_layout.addWidget(QLabel("line width"))

                self.polygon_name_layout = QHBoxLayout()
                self.polygon_name_layout.addWidget(self.polygon_name_box)
                self.polygon_name_layout.addWidget(QLabel("polygon name"))

                self.layer_layout = QHBoxLayout()
                self.layer_layout.addWidget(self.layer_box)
                self.layer_layout.addWidget(QLabel("layer name"))

                self.wirebend_layout = QHBoxLayout()
                self.wirebend_layout.addWidget(self.wirebend_selector)
                self.wirebend_layout.addWidget(QLabel("wire bend"))

                self.eagle_settings_layout.addLayout(self.width_layout)
                self.eagle_settings_layout.addLayout(self.polygon_name_layout)
                self.eagle_settings_layout.addLayout(self.layer_layout)
                self.eagle_settings_layout.addLayout(self.wirebend_layout)
                self.eagle_settings_layout.setAlignment(Qt.AlignLeft)
                self.eagle_settings_layout.setAlignment(Qt.AlignLeft)

                self.eagle_settings_group.setLayout(self.eagle_settings_layout)

                self.options_layout.addWidget(self.eagle_settings_group)

                self.preview_group = QGroupBox()
                self.preview_layout = QHBoxLayout()
                self.preview_group.setTitle("Preview")

                self.line_preview_button = QRadioButton()
                self.line_preview_button.setText("preview lines")
                self.line_preview_button.setToolTip(
                    "preview the polygon lines before generating the script. \n(slower) (needs pyqtgraph, pyqt and its dependecies installed. See the github page for help)")
                self.line_preview_button.setAutoExclusive(False)
                self.line_preview_button.toggled.connect(lambda : self.dot_preview_button.setChecked(False) if self.line_preview_button.isChecked() else None)
                self.dot_preview_button = QRadioButton()
                self.dot_preview_button.setText("preview dots")
                self.dot_preview_button.setToolTip(
                    "preview the polygon dots before generating the script. \n(faster) (needs pyqtgraph, pyqt and its dependecies installed. See the github page for help)")
                self.dot_preview_button.setAutoExclusive(False)
                self.dot_preview_button.toggled.connect(lambda : self.line_preview_button.setChecked(False) if self.dot_preview_button.isChecked() else None)
                # self.reset_button = QPushButton()
                # self.reset_button.setText("Reset")
                # self.reset_button.setToolTip("reset checkbox setting")
                # self.reset_button.clicked.connect(lambda : [self.dot_preview_button.setChecked(False), self.line_preview_button.setChecked(False)])

                self.preview_layout.addWidget(self.line_preview_button)
                self.preview_layout.addWidget(self.dot_preview_button)
                # self.preview_layout.addWidget(self.reset_button)
                self.preview_layout.setAlignment(Qt.AlignLeft)

                self.preview_group.setLayout(self.preview_layout)

                self.options_layout.addWidget(self.preview_group)

                self.json_group = QGroupBox()
                self.json_layout = QHBoxLayout()
                self.json_group.setTitle("import/export")

                self.import_button = QRadioButton()
                self.import_button.setToolTip("import polygons instead of generating it from an svg")
                self.import_button.setText("import from json")
                self.import_button.setAutoExclusive(False)
                self.import_button.toggled.connect(self.update_input_warning)
                self.export_button = QRadioButton()
                self.export_button.setToolTip("export polygons instead of generating the scipt")
                self.export_button.setText("export to json")
                self.export_button.setAutoExclusive(False)
                self.export_button.toggled.connect(self.update_output_warning)

                self.json_layout.addWidget(self.import_button)
                self.json_layout.addWidget(self.export_button)
                self.json_layout.setAlignment(Qt.AlignLeft)

                self.json_group.setLayout(self.json_layout)

                self.options_layout.addWidget(self.json_group)

                self.run_layout = QHBoxLayout()
                self.run_button = QPushButton()
                self.run_button.setText("Run")
                self.run_button.setToolTip("Run script and hope for the best ;)")
                self.run_layout.addWidget(self.run_button)
                self.run_button.clicked.connect(self.run)
                self.options_layout.addLayout(self.run_layout)

                self.options_layout.setAlignment(Qt.AlignTop)

                self.options_widget = QWidget()
                self.options_widget.setLayout(self.options_layout)
                self.splitter.addWidget(self.options_widget)

                self.main_layout = QHBoxLayout()
                self.main_layout.addWidget(self.splitter)
                self.setLayout(self.main_layout)


                self.input_file_list.clear()
                self.inputs = list(filter(lambda x: x != self.input_path,  self.inputs))
                self.inputs.append(self.input_path)
                self.input_file_list.addItems(self.inputs)

                self.output_file_list.clear()
                self.outputs = list(filter(lambda x: x != self.output_path,  self.outputs))
                self.outputs.append(self.output_path)
                self.output_file_list.addItems(self.outputs)

                self.update_input_warning()
                self.update_output_warning()

            def updateConsoleOutput(self):
                self.terminal.setText(''.join(output))

            def browse_files(self):
                filter = "Json files (*.json);;SVG files (*.svg);;All files (*)"
                caption = "select input file"
                self.input_path = \
                    QFileDialog.getOpenFileName(filter=filter, caption=caption, directory=self.input_path)[0]
                print("selected " + self.input_path + " as input file")
                self.update_input_warning()

            def save_as_file(self):
                filter = "Json files (*.json);;Script files (*.scr);;All files (*)"
                caption = "select input file"
                self.output_path = \
                    QFileDialog.getSaveFileName(self, caption=caption, directory=self.output_path, filter=filter)[0]
                print("selected " + self.output_path + " as output file")
                self.update_output_warning()

            def update_input_warning(self):
                self.settings.setValue("input_path", self.input_path)
                self.settings.sync()
                if not os.path.isfile(self.input_path):
                    self.set_message(self.input_warning_label, "ERROR: File is invalid: "+self.input_path, 3)

                elif self.input_path.split(".")[-1] == "json":
                    if self.import_button.isChecked():
                        self.set_message(self.input_warning_label, "File validated: "+self.input_path, 1)
                    else:
                        self.set_message(self.input_warning_label, "ERROR: Expected SVG file but recived JSON file: "+self.input_path, 3)

                # elif (file_type := filetype.guess(self.input_path)) is None:
                #     if self.import_button.isChecked():
                #         self.set_message(self.input_warning_label, "WARNING: Unrecognized file type", 2)
                #     else:
                #         self.set_message(self.input_warning_label, "ERROR: Expected SVG file but recived unrecognized file type", 3)
                #
                # elif file_type.mime.split("/")[0] != "image":
                #     if self.import_button.isChecked():
                #         self.set_message(self.input_warning_label, "WARNING: Possibly wrong file type", 2)
                #     else:
                #         self.set_message(self.input_warning_label, "ERROR: Expected SVG file but recived non image file", 3)
                #
                # elif file_type != "image/svg":
                #     if self.import_button.isChecked():
                #         self.set_message(self.input_warning_label, "ERROR: Expected JSON file but recived image file", 3)
                #     else:
                #         self.set_message(self.input_warning_label, "ERROR: Expected SVG file but recived unsupported image file. \nPlease check the github page for available coversion methodes", 3)

                elif self.input_path.split(".")[-1] == "svg":
                    if self.import_button.isChecked():
                        self.set_message(self.input_warning_label, "ERROR: Expected JSON file but recived SVG file: "+self.input_path, 3)
                    else:
                        self.set_message(self.input_warning_label, "File validated: "+self.input_path, 1)

                else:
                    if self.import_button.isChecked():
                        self.set_message(self.input_warning_label, "WARNING: Unrecognized file type: "+self.input_path, 2)
                    else:
                        self.set_message(self.input_warning_label,
                                         "ERROR: Expected SVG file but recived unrecognized file type: "+self.input_path, 3)

            def update_output_warning(self):
                self.settings.setValue("output_path", self.output_path)
                self.settings.sync()
                if self.output_path.split(".")[-1] == "json":
                    if self.export_button.isChecked():
                        self.set_message(self.output_warning_label, "Save location validated: "+self.output_path, 1)
                    else:
                        self.set_message(self.output_warning_label,
                                         "WARNING: saving a SCR file to JSON file. EAGLE ma not be able to open it: "+self.output_path, 2)

                elif self.output_path.split(".")[-1] == "scr":
                    if self.export_button.isChecked():
                        self.set_message(self.output_warning_label, "WARNING: saving a JSON file to SCR file: "+self.output_path, 2)
                    else:
                        self.set_message(self.output_warning_label, "Save location validated: "+self.output_path, 1)
                else:
                    if self.export_button.isChecked():
                        self.set_message(self.output_warning_label,
                                         "WARNING: saving a JSON file with uknown file extension: "+self.output_path, 2)
                    else:
                        self.set_message(self.output_warning_label,
                                         "WARNING: saving a SCR file with uknown file extension. EAGLE ma not be able to open it: "+self.output_path,
                                         2)

            def set_message(self, label, message, state=0):
                p = QPalette()
                if state == 0:
                    p.setColor(QPalette.WindowText, self.palette().windowText().color())
                if state == 1:
                    p.setColor(QPalette.WindowText, Qt.darkGreen)
                if state == 2:
                    p.setColor(QPalette.WindowText, Qt.darkYellow)
                if state == 3:
                    p.setColor(QPalette.WindowText, Qt.red)
                label.setPalette(p)
                label.setText(message)


            def input_file_list_add_to_input(self):
                if len(self.input_file_list.selectedItems()) > 0:
                    self.input_path = self.input_file_list.selectedItems()[0].text()
                    print("selected " + self.input_path + " as input file")
                    self.update_input_warning()

            def input_file_list_add_to_output(self):
                if len(self.input_file_list.selectedItems()) > 0:
                    self.output_path = self.input_file_list.selectedItems()[0].text()
                    print("selected " + self.output_path + " as input file")
                    self.update_output_warning()

            def output_file_list_add_to_input(self):
                if len(self.output_file_list.selectedItems()) > 0:
                    self.input_path = self.output_file_list.selectedItems()[0].text()
                    print("selected " + self.input_path + " as input file")
                    self.update_input_warning()

            def output_file_list_add_to_output(self):
                if len(self.output_file_list.selectedItems()) > 0:
                    self.output_path = self.output_file_list.selectedItems()[0].text()
                    print("selected " + self.output_path + " as input file")
                    self.update_output_warning()


            def run(self):

                def list_mouse_event(self: QListWidgetItem, event):
                    if event.buttons() == Qt.LeftButton:
                        self.input_path = self.text()
                        print("selected " + self.input_path + " as input file")
                        self.update_input_warning()
                    elif event.buttons() == Qt.RightButton:
                        self.output_path = self.text()
                        print("selected " + self.output_path + " as output file")
                        self.update_output_warning()

                self.input_file_list.clear()
                self.inputs = list(filter(lambda x: x != self.input_path,  self.inputs))
                self.inputs.append(self.input_path)
                self.input_file_list.addItems(self.inputs)
                self.settings.setValue("input_paths", json.dumps(self.inputs))

                self.output_file_list.clear()
                self.outputs = list(filter(lambda x: x != self.output_path,  self.outputs))
                self.outputs.append(self.output_path)
                self.output_file_list.addItems(self.outputs)
                self.settings.setValue("output_paths", json.dumps(self.outputs))

                self.settings.sync()

                args = {
                    "source": self.input_path,
                    "destination": self.output_path,
                    "density": self.density_spinbox.value(),
                    "scale": self.scale_spinbox.value(),
                    "offset": (self.xofffset_spinbox.value(), self.yofffset_spinbox.value()),
                    "dont_mirror": not self.mirror_button.isChecked(),
                    "import_polygons": self.import_button.isChecked(),
                    "export_polygons": self.export_button.isChecked(),
                    "dont_pop_bubbles": not self.pop_bubbles_button.isChecked(),
                    "dont_remove_duplicates": not self.remove_duplicates_button.isChecked(),
                    "dont_remove_redundancies": not self.remove_redundancies_button.isChecked(),
                    "width": self.width_spinbox.value(),
                    "name": self.polygon_name_box.text(),
                    "layer": self.layer_box.text(),
                    "wire_bend": self.wirebend_selector.currentText(),
                    "preview_dots": False,
                    "preview_lines": False
                }
                print(args)
                self.thread = QThread()
                if self.dot_preview_button.isChecked():
                    self.thread.finished.connect(lambda: PyQt_display(mylist, False))
                if self.line_preview_button.isChecked():
                    self.thread.finished.connect(lambda: PyQt_display(mylist, True))
                self.thread.run = lambda: svg2eagle(**args)
                self.thread.start()
                # try:
                #     self.thread.start()
                # except Exception as e:
                #     traceback.print_exc()
                # svg2eagle(**args)

        App = QApplication.instance()
        if not App:
            App = QApplication(sys.argv)
        main = MainWindow()
        main.show()
        App.exec()

if __name__ == "__main__":
    gui()
