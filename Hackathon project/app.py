from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import requests
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
azure_openai_endpoint = os.getenv("ENDPOINT_URL", "https://example.openai.azure.com/")
api_key = os.getenv("AZURE_OPENAI_API_KEY", "your_api_key_here")
deployment_name = 'gpt-4o'  # Replace with your valid model name

headers = {
    "Content-Type": "application/json",
    "api-key": api_key,
}

def get_product_info(product_name, date, file_content=None, receipt=None):
    if receipt:
        prompt = (
            "Analyze the following receipt with multiple groceries and organize them in descending order of expiration date:\n"
            f"{receipt}\n"
            "Provide the expiration date in the format 'Best by: MM/DD/YYYY' for each item.\n"
            "Format the response as follows:\n"
            "Item 1: Best by: MM/DD/YYYY\n"
            "Item 2: Best by: MM/DD/YYYY\n"
            "Item 3: Best by: MM/DD/YYYY\n"
        )
    else:
        prompt = (
            f"Estimate the 'Best by' date for {product_name}, assuming it is refrigerated and bought on {date}. "
            "Provide the date in the format 'Best by: MM/DD/YYYY'. Then, create a list of the top 3 recipes using this product. "
            "Separate the 'Best by' date and the list of recipes clearly. Format the response as follows:\n"
            "'Best by: MM/DD/YYYY'\n"
            "Top 3 Recipes:\n"
            "1. Recipe 1\n"
            "2. Recipe 2\n"
            "3. Recipe 3\n"
        )
        if file_content:
            encoded_image = base64.b64encode(file_content).decode('ascii')
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {"type": "text", "text": prompt}
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Provide the following data: "},
                            {"type": "text", "text": "Image data"}
                        ],
                        "media": [
                            {"type": "image", "content": encoded_image}
                        ]
                    }
                ],
                "temperature": 0.4,
                "top_p": 0.95,
                "max_tokens": 200
            }
        else:
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                "temperature": 0.4,
                "top_p": 0.95,
                "max_tokens": 200
            }

    endpoint = f"{azure_openai_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2024-02-15-preview"

    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
        return response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No content')
    except requests.RequestException as e:
        return f"Error fetching product info: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_input', methods=['POST'])
def process_input():
    # Extract the product_name, date, file, and receipt from form data
    product_name = request.form.get('product_name')
    date_str = request.form.get('date')
    file = request.files.get('file')
    receipt = request.form.get('receipt')

    # Validate the date
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        if (datetime.now() - date).days > 365 * 5:  # Check if the date is more than 5 years ago
            return jsonify({"error": "The date provided is too old. Please attach an image of the receipt instead."}), 400
    except ValueError:
        return jsonify({"error": "Invalid date format. Please provide a valid date."}), 400

    if not product_name and not receipt:
        return jsonify({"error": "Product name or receipt not provided"}), 400

    file_content = None
    if file:
        file_content = file.read()

    # Get product information from Azure OpenAI
    product_info = get_product_info(product_name, date_str, file_content, receipt)

    # Return the result as JSON
    return jsonify({"message": product_info})

if __name__ == '__main__':
    app.run(debug=True)
