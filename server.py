from flask import Flask, render_template, request
import os
import colorgram
import webcolors
import numpy as np
import cv2
import statistics
import pandas as pd
import easyocr
from werkzeug.utils import secure_filename

app = Flask(__name__)

reader = easyocr.Reader(['en'])  # Initialize once


def is_nan(x):
    return (x is np.nan or x != x)


@app.route('/')
def index():
    return render_template('template.html')


def color(file):
    colors = colorgram.extract(file, 2)
    first_color = colors[1]
    rgb = first_color.rgb
    return rgb


def closest_colour(requested_colour):
    min_colours = {}
    for name, hex_code in webcolors.CSS3_NAMES_TO_HEX.items():
        r_c, g_c, b_c = webcolors.hex_to_rgb(hex_code)
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        min_colours[(rd + gd + bd)] = name
    return min_colours[min(min_colours.keys())]



def get_colour_name(requested_colour):
    try:
        closest_name = actual_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        closest_name = closest_colour(requested_colour)
        actual_name = None
    return actual_name, closest_name


def detect_imprint_locally(image_path):
    result = reader.readtext(image_path)
    text = ''.join([item[1] for item in result])
    return ''.join(text.split())


@app.route('/my-link/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        f = request.files['file']
        f.save(secure_filename(f.filename))
        file = str(f.filename)

    # Detect imprint text locally
    text2 = detect_imprint_locally(file)

    # Getting color
    requested_colour = color(file)
    actual_name, closest_name = get_colour_name(requested_colour)
    if "grey" in closest_name:
        closest_name = "WHITE"
    if "rose" in closest_name:
        closest_name = "PINK"
    if "red" in closest_name:
        closest_name = "RED"
    if "yellow" in closest_name:
        closest_name = "YELLOW"
    if "blue" in closest_name:
        closest_name = "BLUE"

    # Getting shape
    shape = ""
    img = cv2.imread(file)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.Canny(np.asarray(gray), 50, 250)

    contours, _ = cv2.findContours(gray, 1, 2)
    avgArray = []
    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)
        avgArray.append(len(approx))

    edges = statistics.median(avgArray) if avgArray else 0
    if edges < 15:
        shape = "OVAL"
    elif edges > 15:
        shape = "CIRCLE"

    data = {"uploadName": file, "text": text2, "color": closest_name, "shape": shape}
    print(data)

    dataframe = pd.read_csv("out.csv")

    for index, row in dataframe.iterrows():
        name = str(row["Imprint"]).replace(";", "")
        if not is_nan(row["Name"]):
            if name == text2 and row["Color"] == closest_name and row["Shape"] == shape:
                return render_pill_table(row)

    for index, row in dataframe.iterrows():
        name = str(row["Imprint"]).replace(";", "")
        if not is_nan(row["Name"]):
            if name == text2 and row["Color"] == closest_name:
                return render_pill_table(row)

    for index, row in dataframe.iterrows():
        name = str(row["Imprint"]).replace(";", "")
        if not is_nan(row["Name"]):
            if name == text2:
                return render_pill_table(row)

    return "No matching pill found."


def render_pill_table(row):
    return f'''<style>
        table, th, td {{
            border: 1px solid black;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 5px;
            text-align: left;
        }}
        b{{
            margin-left: 43%;
            font-size: 20px;
        }}
        </style><b>Pill Details</b><br><table style="width:100%; height: 80%; padding: 1px; margin: 1px"><br />
          <tr><th>Author</th><td>{row['Author']}</td></tr>
          <tr><th>Name</th><td>{row['Name']}</td></tr>
          <tr><th>Color</th><td>{row['Color']}</td></tr>
          <tr><th>Imprint</th><td>{row['Imprint']}</td></tr>
          <tr><th>Size</th><td>{row['Size']}</td></tr>
          <tr><th>Shape</th><td>{row['Shape']}</td></tr>
          <tr><th>Ingredients</th><td>{row['Ingredients']}</td></tr>
        </table>'''


if __name__ == "__main__":
    app.run(debug=True)
