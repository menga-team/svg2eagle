import argparse
import math
import random
from anytree import Node, AnyNode, RenderTree
from tqdm import tqdm
from xml.dom import minidom
import svg.path
import json
import collections

from youtube_dl import main


point = collections.namedtuple('point', ['x', 'y'])
line = collections.namedtuple('line', ['a', 'b'])
box = collections.namedtuple('box', ['left', 'bot', 'right', 'top'])


def prepare_svg(doc):
    paths = []
    for element in doc.getElementsByTagName("path"):
        paths.extend(list(svg.path.parse_path(element.getAttribute("d"))))

       # print(paths)
    result = []
    temp_paths = [paths[1]]
    last_move = 0
    for i in paths[1:]:
        if isinstance(i, svg.path.Move):
            # print(paths[last_move:paths.index(i)], paths.index(i))
            result.append(paths[last_move:paths.index(i)])
            last_move = paths.index(i)
    result.append(paths[last_move:len(paths)-1])
    return result


def get_point_at(path, distance, dont_mirror):
    pos = path.point(distance)
    if dont_mirror:
        return point(round(pos.real, 6), -round(pos.imag, 6))
    else:
        return point(-round(pos.real, 6), -round(pos.imag, 6))


def points_from_doc(doc, density=1, dont_mirror=True):
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
                args = paths[i][j], distance, dont_mirror
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


def PyQt_display(inp):
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
        legend = pg.LegendItem((80, 60), offset=(70, 20))
        legend.setParentItem(plot.graphicsItem())

        for path in inp:
            x = [i[0] for i in path]
            y = [i[1] for i in path]
            
            legend.addItem(plot.plot(x, y, pen=inp.index(path)), f"{inp.index(path) + 1}")
        
        App.exec()

def scale_and_offset(inp, scale, offset):
    for poly in range(len(inp)):
        for p in range(len(inp[poly])):
            inp[poly][p] = point((inp[poly][p][0] + offset[0]) * scale, (inp[poly][p][1] + offset[1]) * scale)
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


def remove_redundant_points_from_path(inp, pgbar=None):
    def is_between(a, c, b):
        return math.isclose(distance(a, c) + distance(c, b), distance(a, b))
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


def get_polygon_lines(polygon):
    if not len(polygon):
        return []
    lines = []
    for i in range(len(polygon)-1):
        lines.append(line(polygon[i], polygon[i+1]))
    lines.append(line(polygon[-1], polygon[0]))
    return lines


def line_intersect(linea, lineb):
    # thx https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    def ccw(A, B, C): return (C.y-A.y) * (B.x-A.x) > (B.y-A.y) * (C.x-A.x)
    return ccw(linea.a, lineb.a, lineb.b) != ccw(linea.b, lineb.a, lineb.b) and ccw(linea.a, linea.b, lineb.a) != ccw(linea.a, linea.b, lineb.b)


def point_in_polygon(p, polygon):
    box = get_polygon_box(polygon)
    faktor = line(point(box.top, box.right), point(box.bot, box.top))
    c = distance(faktor.a, faktor.b)
    ccw = lambda A, B, C: (C.y-A.y) * (B.x-A.x) > (B.y-A.y) * (C.x-A.x)
        
    for pp in polygon:
        intersections = 0
        
        l2 = line(p, pp)
        alpha = math.degrees(math.atan2(l2.a.y-l2.b.y, l2.a.x-l2.b.x))
        a = c * math.sin(alpha)
        b = math.sqrt(c*c - a*a)
        new_point = point(round(pp.x-b, 6), round(pp.y-a, 6))
        l2 = line(p, new_point)
        
        
        for l1 in get_polygon_lines(polygon):
            if ccw(l1.a, l2.a, l2.b) != ccw(l1.b, l2.a, l2.b) and ccw(l1.a, l1.b, l2.a) != ccw(l1.a, l1.b, l2.b):
                intersections += 1

            # if line_intersect(line(p, new_point), l1):
            #     # print(intersections)
            #     intersections += 1
            
            
            # l2 = line(p, pp)
            # dy1 = l1.b.y - l1.a.y
            # dx1 = l1.b.x - l1.a.x
            # dy2 = l2.b.y - l2.a.y
            # dx2 = l2.b.x - l2.a.x
            # # check whether the two line parallel
            # if not dy1 * dx2 == dy2 * dx1:
            #     x =  ((l2.a.y - l1.a.y) * dx1 * dx2 + dy1 * dx2 * l1.a.x - dy2 * dx1 * l2.a.x) / (dy1 * dx2 - dy2 * dx1)
            #     y =  l1.a.y + (dy1 / dx1) * (x - l1.a.x)
                # if point_in_box(point(x, y), get_polygon_box(l1)):
                #     intersections += 1
            # Vertices for the first line
            # p1_start    = np.asarray([-5,   0])
            # p1_end      = np.asarray([-3,   0])

            # # Vertices for the second line
            # p2_start    = np.asarray([0,    4])
            # p2_end      = np.asarray([0,    2])

            # p       = p1_start
            # r       = (l1.a-l1.b)

            # # q       = l.a
            # s       = (l2.a-l2.b)

            # t       = np.cross(q - p,s)/(np.cross(r,s))

            # This is the intersection point
            # i       = p + t*r
            # l = line(p, poly_point)
            # x = (poly_line.y - l.y) / (poly_line.x-l.x)
            # y = l.x * x + poly_line.y
            # lenght = distance(poly_line.a, poly_line.b) + 0.001
            # x = ((poly_point.x / lenght) + (dist / lenght)) * lenght
            # y = ((poly_point.y / lenght) + (dist / lenght)) * lenght
            # new = point(x, y)
        if intersections % 2 == 1:
            return False
    return True


def get_polygon_box(polygon):
    x = []
    y = []
    for i in polygon:
        x.append(i.x)
        y.append(i.y)
    return box(min(x), max(y), max(x), min(y))


def point_in_box(point, box):
    return box.left < point.x < box.left and box.bot < point.y < box.top


def box_in_box(boxa, boxb):
    left = boxa.left < boxb.left
    top = boxa.top < boxb.top
    right = boxa.right > boxb.right
    bot = boxa.bot > boxb.bot
    return left and top and right and bot


# des sich die methode de nui zu implementieren isch
def polygon_in_polygon(polygona, polygonb):
    # for point in polygona:
    #     if not point_in_polygon(point, polygonb):
    #         return False
    # return True
    if box_in_box(get_polygon_box(polygona), get_polygon_box(polygonb)):
        # wenn i lei check ob a polygon-boundry box in die boundry box von an ondren polygon drin isch, norr geat sel supper
        # sobold i ober probier mit point_in_polygon zu spezifisch zu schecken ob des in dem polygon drin isch braucht des johre
        if polygon_intersects_polygon(polygona, polygonb):
            return False
        for point in polygona:
            if not point_in_polygon(point, polygonb):
                return False
        return True
    return False


def polygon_intersects_polygon(polygona, polygonb):
    for linea in get_polygon_lines(polygona):
        for lineb in get_polygon_lines(polygonb):
            if line_intersect(linea, lineb):
                return True
    return False


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
    pgbar = tqdm(desc="popping bubbles", total=(len(inp) * 2) + 2, unit="polygons")

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
                inp[node.name] = stich_hole_into_polygon(inp[i.name], inp[node.name])
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
        script += f"polygon {name} {width}mm "
        for point in path:
            pgbar.update()
            script += f" ({point.x}mm {point.y}mm) "
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
    destination,

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

    preview=True,
):
    if import_polygons:
        mylist = importPoints(source)
    else:
        mylist = points_from_doc(getDoc(source), density=density, dont_mirror=dont_mirror)
    mylist = scale_and_offset(mylist, scale, offset)
    if not dont_pop_bubbles:
        mylist = pop_bubbles(mylist)
    if not dont_remove_duplicates:
        mylist = remove_duplicate_points(mylist)
    if not dont_remove_redundancies:
        mylist = remove_redundant_points(mylist)
    if preview:
        PyQt_display(mylist)
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

    ap.add_argument("-p", "--preview", action="store_true", required=False, help="preview the polygons before generating the script." +
                    "(needs pyqtgraph, pyqt and its dependecies installed. See the github page for help")

    ap.add_argument("source", default="this.svg", type=str,
                    help="path to source svg or to import json")
    ap.add_argument("destination", default="this.svg", type=str,
                    help="destination path for export or script")

    print(json.dumps(vars(ap.parse_args()), indent=2))
    svg2eagle(**vars(ap.parse_args()))


if __name__ == "__main__":
    cli()
    # # svg2eagle("mediumtest.svg", preview=True)
    # mylist = points_from_doc(getDoc("mediumtest.svg"), density=0.1)
    # exportPoints(mylist, "test.json")
    # # PyQt_display(mylist)
    # mylist = importPoints("test.json")
    # # exportPoints(mylist, "test.json")
    # mylist = pop_bubbles(mylist)
    # mylist = remove_duplicate_points(mylist)
    # # PyQt_display(mylist)
    # generateScript(mylist, "test.scr")

    # # print(line_intersect(line(point(0, 1), point(1, 0)), line(point(1, 1), point(0, 0))))
    
    # A = line(point(1, -1), point(1, 0))
    # B = line(point(1, 1), point(1, 0))
    
    # C = line(point(0, 0), point(2, 0))
    
    # print(line_intersect(A, C))
    # print(line_intersect(B, C))
    # print(line_intersect(A, B))
