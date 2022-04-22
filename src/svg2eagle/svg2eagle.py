import argparse
import math
from tqdm import tqdm
from xml.dom import minidom

import json
import collections

from svg.path import parse_path

point = collections.namedtuple('point', ['x', 'y'])

def get_point_at(path, distance, scale, offset, dont_mirror):
    pos = path.point(distance)
    pos += offset
    pos *= scale
    if dont_mirror:
        return point(pos.real, -pos.imag)
    else:
        return point(-pos.real, -pos.imag)

def points_from_doc(doc, density=1, scale=0.15, offset=(0, 0), dont_mirror=True):
    offset = offset[0] + offset[1] * 1j
    paths = []
    points = []
    
    for element in doc.getElementsByTagName("path"):
        paths.append(list(parse_path(element.getAttribute("d"))))
    
    
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
                try: distance = k/(step)
                except ZeroDivisionError: distance = 0
                args = paths[i][j], distance, scale, offset, dont_mirror
                points[i].append(get_point_at(*args))
                # processes.append(Process(target=get_point_at, args=args))
            index += step+1
            
    
    # for i in processes:
    #     i.start()
    # for i in processes:
    #     i.join()
    pgbar.close()
    # for i in range(len(points)):
    #     points[i] = list(points[i].values())
    return points

def getDoc(path):
    print("opening ", path)
    return minidom.parseString(open(path).read())

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
        screen = pg.ScatterPlotItem()
        plot.addItem(screen)
        for path in inp:
            screen.addPoints(pos=path, pen=inp.index(path))
        App.exec()

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
    pgbar = tqdm(desc="removing duplicate points", total=max_points, unit="points")
    result = []
    for i in inp:
        result.append(remove_duplicate_points_from_path(i, pgbar))
    pgbar.close()
    return result

def pointAreClose(a, b):
    return all((math.isclose(a.x, b.x), math.isclose(a.y, b.y)))

def distance(a,b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def remove_redundant_points_from_path(inp, pgbar=None):
    def is_between(a,c,b):
        return math.isclose(distance(a,c) + distance(c,b), distance(a,b))
    result = []
    for i in range(1, len(inp) - 1):
        if not is_between(inp[i-1], inp[i], inp[i+1]):
            result.append(inp[i])
        if pgbar is not None:
            pgbar.update()
    return [inp[0]] + result + [inp[0]]

def remove_redundant_points(inp):
    max_points = sum([len(i) for i in inp])
    pgbar = tqdm(desc="removing redundant points", total=max_points, unit="points")
    result = []
    for i in inp:
        result.append(remove_redundant_points_from_path(i, pgbar))
    pgbar.close()
    return result

# def get_closest_points(path1, path2):
#     pointa = path1[0]
#     pointb = path2[0]
#     last_distance = distance(pointa, pointb)
#     for a in path1: 
#         for b in path2: 
#             if (dist := distance(a, b)) < last_distance:
#                 pointa = a
#                 pointb = b
#                 last_distance = dist
#     return point(pointa, pointb)

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
    offset=(90, 90), 
    dont_mirror=True,
    
    import_polygons=False,
    
    export_polygons=False,
    
    dont_remove_duplicates=False, 
    dont_remove_redundancies=False, 
    
    width=0.1, 
    name="menga", 
    layer="bplace", 
    
    preview=True, 
    ):
    
    global mylist
    if import_polygons:
        mylist = importPoints(source)
    else:
        mylist = points_from_doc(getDoc(source), density=density, scale=scale, offset=offset, dont_mirror=dont_mirror)
    if not dont_remove_duplicates:
        mylist = remove_duplicate_points(mylist)
    if not dont_remove_redundancies:
        mylist = remove_redundant_points(mylist)
    if preview:
        PyQt_display(mylist)
    if export_polygons:
        exportPoints(mylist, destination)
    else:
        generateScript(mylist, destination, width=width, name=name, layer=layer)

def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--density", default=1, type=float, required=False, help="how many points per mm should be generated on each line")
    ap.add_argument("-s", "--scale", default=1, type=float, required=False, help="scale multiplier")
    ap.add_argument("-o", "--offset", default=(90, 90), type=float, required=False, help="offset the points by:", nargs=2)
    ap.add_argument("-m", "--dont-mirror", action="store_true", required=False, help="don't mirror the polygon." +
                    "(use it if you want to print of the front of a circuit. default is back but you can change it by changing the layer)")
    
    ap.add_argument("-i", "--import-polygons", action="store_true", required=False, help="import polygons instead of generating it from an svg")
    
    ap.add_argument("-e", "--export-polygons", action="store_true", required=False, help="export polygons instead of generating the scipt")
    
    ap.add_argument("-x", "--dont-remove-duplicates", action="store_true", required=False, help="don't remove duplicate points from the polygon")
    ap.add_argument("-X", "--dont-remove-redundancies", action="store_true", required=False, help="dont't remove redunatnd points from the polygon"+
                    "(for now points that are on a straight line and dont change the line angle get removed as they are useless)")
    
    ap.add_argument("-w", "--width", default=0.1, type=float, required=False, help="line width in EAGLE™")
    ap.add_argument("-n", "--name", default="menga", type=str, required=False, help="name of the generated polygons")
    ap.add_argument("-l", "--layer", default="bplace", type=str, required=False, help="layer the polygons will be printed on "+
                    "('tplace' is the top slkscreen, while 'bplace' is the bottom silkscreen. Note that if you are printing"+
                    "somrthing on the back of a circuit you need to mirror it)")
    
    ap.add_argument("-p", "--preview", action="store_true", required=False, help="preview the polygons before generating the script."+
                    "(needs pyqtgraph, pyqt and its dependecies installed. See the github page for help")
    
    ap.add_argument("source", default="this.svg", type=str, help="path to source svg or to import json")
    ap.add_argument("destination", default="this.svg", type=str, help="destination path for export or script")
    
    
    print(json.dumps(vars(ap.parse_args()), indent=2))
    svg2eagle(**vars(ap.parse_args()))

if __name__ == "__main__":
    cli()