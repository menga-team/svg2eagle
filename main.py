from xml.dom import minidom

from svgpath2mpl import parse_path

def paths_from_doc(doc):
    for element in doc.getElementsByTagName("path"):
        yield (element.getAttribute("d"), element.getAttribute("id"))

doc = minidom.parseString(open("vectordesign.svg").read())
# points = points_from_doc(doc)
# doc.unlink()

comand = ""
for path, id in paths_from_doc(doc):
    mpl_path = parse_path(path)

    d = mpl_path.to_polygons()[0]
    coordinates = list()
    for i in d:
        coordinates.append(list(i))
    # print(coordinates)
    # poly = Polygon(coordinates[0])
    # p = gpd.GeoSeries(poly)
    # p.plot()

    res = "polygon GND 0.1mm "
    # coordinates[0].append(coordinates[0][0])
    
    temp = []
    for coord in coordinates[1:-1]:
        if coord not in temp and coord != coordinates[0]:
            temp.append(coord)
    coordinates = [coordinates[0]]
    coordinates.extend(temp)
    coordinates.append(coordinates[0])
    
    for i in coordinates:
        res += f" ({i[0]}mm {-i[1] - 20}mm)"

    comand += res + f";#{id};\n"

f = open("comand.scr", "w")
f.write(comand)

# p = gpd.GeoSeries(poly)
# p.plot()
# plt.show()