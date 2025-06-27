import os
import io
import csv
import cv2
import easyocr
import pandas as pd
import numpy as np
import tempfile
import streamlit as st
from pdf2image import convert_from_bytes

current_dir = os.getcwd()

reader = easyocr.Reader(['en', 'ja'])

st.set_page_config(page_title="Invoice Processing", layout="wide")

st.markdown(
    "<h1 style='color: #2E86C1; font-family: Arial; font-style: italic;'>OCR Invoice Processing</h1>",
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader("Upload Invoice PDF", type=["pdf", "jpg", "jpeg", "png"])

if uploaded_file:

    # get file name and type 
    file_name = uploaded_file.name
    file_ext = file_name.split('.')[-1].lower()

    # get upload file path from temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix="."+uploaded_file.name.split(".")[-1]) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        temp_file_path = tmp_file.name

    if file_ext == 'pdf':
        images = convert_from_bytes(uploaded_file.read(), dpi=300)
        image = images[0]
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    elif file_ext == 'jpg' or file_ext == 'jpg' or file_ext == 'png':
        image = cv2.imread(temp_file_path)

    with st.spinner("Detecting & Extracting Text..."):

        results = reader.readtext(image)

        structured_results = []

        for bbox, text, conf in results:
            x_min = min(point[0] for point in bbox)
            y_min = min(point[1] for point in bbox)
            x_max = max(point[0] for point in bbox)
            y_max = max(point[1] for point in bbox)
            
            structured_results.append({
                'text': text,
                'x_min': x_min,
                'y_min': y_min,
                'x_max': x_max,
                'y_max': y_max,
                'center_y': (y_min + y_max) / 2
            })

            # visualize bounding boxes on detected texts
            cv2.rectangle(image, [x_min, y_min], [x_max, y_max], (0, 255, 0), 2)

        det_image_name = os.path.join(current_dir,'outputs/detect',file_name.split('.')[0]+'.jpg')

        # save detected image to './outputs/detect/' folder
        cv2.imwrite(det_image_name,image)

    
    df = pd.DataFrame(structured_results)

    df = df.sort_values(by=['center_y', 'x_min']).reset_index(drop=True)

    # set threshold for vertical pixels distance 
    row_threshold = 20  
    rows = []
    current_row = []
    last_y = None

    for _, row in df.iterrows():
        if last_y is None or abs(row['center_y'] - last_y) <= row_threshold:
            current_row.append(row)
        else:
            rows.append(current_row)
            current_row = [row]
        last_y = row['center_y']

    if current_row:
        rows.append(current_row)


    table = []

    for row_cells in rows:
        sorted_cells = sorted(row_cells, key=lambda r: r['x_min'])
        row_text = [cell['text'] for cell in sorted_cells]
        table.append(row_text)

    # set columns for visualization 
    col_1, col_2 = st.columns([1,1])

    with col_1:
        # display detected texts
        st.image(image, width= 700, channels="BGR")

    with col_2:
        st.markdown(
            "<h3 style='color: teal; font-style: italic;'> Extracted CSV Table </h3>",
            unsafe_allow_html=True
        )
        st.dataframe(table)
    
        # download csv file
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerows(table)

        csv_name = os.path.join(file_name.split('.')[0]+'.csv')

        st.download_button("📥 Download CSV", data = csv_buffer.getvalue(), file_name=csv_name, mime="text/csv")






















