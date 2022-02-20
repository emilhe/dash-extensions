marks = [0, 10, 20, 50, 100, 200, 500, 1000]
color_scale = ["#FFEDA0", "#FED976", "#FEB24C", "#FD8D3C", "#FC4E2A", "#E31A1C", "#BD0026", "#800026"]


def style(feature):
    color = None
    for i, item in enumerate(marks):
        if feature["properties"]["density"] > item:
            color = color_scale[i]
    return dict(fillColor=color, weight=2, opacity=1, color="white", dashArray="3", fillOpacity=0.7)


def hover_style(feature):
    return dict(weight=5, color="#666", dashArray="")
