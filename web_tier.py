from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# Load the prediction data from the CSV file
prediction_df = pd.read_csv('results_data.csv')

@app.route('/', methods=['POST'])
def classify_image():
    # Get the image file from the request
    image_file = request.files['inputFile']
    
    # Process the image 
    filename = image_file.filename

    # Perform lookup in the prediction data based on the image filename
    image_name = filename.split('.')[0]
    correct_result = prediction_df.loc[prediction_df['Image'] == image_name, 'Results'].iloc[0]
    webTier_response = image_name + ':' + correct_result

    return webTier_response