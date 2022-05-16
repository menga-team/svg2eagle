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
    result.append(paths[last_move:len(paths)-1])
    return result


def get_point_at(path, distance):
    pos = path.point(distance)
    return point(round(pos.real, 6), round(pos.imag, 6))


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
            for k in range(0, step+1):
                try:
                    distance = k/(step)
                except ZeroDivisionError:
                    distance = 0
                args = paths[i][j], distance
                points[i].append(get_point_at(*args))
                # processes.append(Process(target=get_point_at, args=args))
            index += step+1

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

        App.exec()


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
    for i in range(1, len(inp)-1):
        if not pointAreClose(inp[i], inp[i+1]) and not pointAreClose(inp[i], inp[0]):
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
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def is_between(a,c,b):
    if (math.isclose(a[0], b[0]) and math.isclose(b[0], c[0])) or (math.isclose(a[1], b[1]) and math.isclose(b[1], c[1])):
        return True
    else:
        crossproduct = (c.y - a.y) * (b.x - a.x) - (c.x - a.x) * (b.y - a.y)

        # compare versus epsilon for floating point values, or != 0 if using integers
        if abs(crossproduct) > 0.001:
            return False

        dotproduct = (c.x - a.x) * (b.x - a.x) + (c.y - a.y)*(b.y - a.y)
        if dotproduct < 0:
            return False

        squaredlengthba = (b.x - a.x)*(b.x - a.x) + (b.y - a.y)*(b.y - a.y)
        if dotproduct > squaredlengthba:
            return False

        return True

def remove_redundant_points_from_path(inp, pgbar):
    if inp == []:
        return []
    result = []
    for i in range(1, len(inp) - 1):
        if not is_between(inp[i-1], inp[i], inp[i+1]):
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
    return polygon[:p+1] + hole[h:] + hole[:h+1] + polygon[p:]


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


def generateScript(inp, script_path, width=0.1, name="menga", layer="bplace"):
    total = 0
    for path in inp:
        for point in path:
            total += 1
    pgbar = tqdm(desc="generating script", total=total, unit="points")
    script = f"CHANGE layer {layer}; CHANGE rank 3; CHANGE pour solid; SET WIRE_BEND 2;\n"
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
    scale=0.2,
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

    preview_dots=True,
    preview_lines=True,
):
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
                       name=name, layer=layer)

def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--density", default=1, type=float, required=False,
                    help="how many points per mm should be generated on each line")
    ap.add_argument("-s", "--scale", default=1, type=float,
                    required=False, help="scale multiplier")
    ap.add_argument("-o", "--offset", default=(0, 0), type=float,
                    required=False, help="offset the points by:", nargs=2)
    ap.add_argument("-m", "--dont-mirror", action="store_true", required=False, help="don't mirror the polygon." +
                    "(use it if you want to print of the front of a circuit. default is back but you can change it by changing the layer)")

    ap.add_argument("-i", "--import-polygons", action="store_true", required=False,
                    help="import polygons instead of generating it from an svg")

    ap.add_argument("-e", "--export-polygons", action="store_true",
                    required=False, help="export polygons instead of generating the scipt")

    ap.add_argument("-b", "--dont-pop-bubbles", action="store_true",
                    required=False, help="don't remove pop bubbles that form inside the polygon-formations")
    ap.add_argument("-x", "--dont-remove-duplicates", action="store_true",
                    required=False, help="don't remove duplicate points from the polygon")
    ap.add_argument("-X", "--dont-remove-redundancies", action="store_true", required=False, help="dont't remove redunatnd points from the polygon" +
                    "(for now points that are on a straight line and dont change the line angle get removed as they are useless)")

    ap.add_argument("-w", "--width", default=0.1, type=float,
                    required=False, help="line width in EAGLE™")
    ap.add_argument("-n", "--name", default="menga", type=str,
                    required=False, help="name of the generated polygons")
    ap.add_argument("-l", "--layer", default="bplace", type=str, required=False, help="layer the polygons will be printed on " +
                    "('tplace' is the top slkscreen, while 'bplace' is the bottom silkscreen. Note that if you are printing" +
                    "somrthing on the back of a circuit you need to mirror it)")

    ap.add_argument("-p", "--preview-dots", action="store_true", required=False, help="preview the polygon dots before generating the script. (faster)" +
                    "(needs pyqtgraph, pyqt and its dependecies installed. See the github page for help")
    ap.add_argument("-P", "--preview-lines", action="store_true", required=False, help="preview the polygons lines before generating the script. (slower)" +
                    "(needs pyqtgraph, pyqt and its dependecies installed. See the github page for help")

    ap.add_argument("source", type=str,
                    help="path to source svg or to import json")
    ap.add_argument("destination", default="", type=str,
                    help="destination path for export or script")

    print(json.dumps(vars(ap.parse_args()), indent=2))
    svg2eagle(**vars(ap.parse_args()))


if __name__ == "__main__":
    cli()