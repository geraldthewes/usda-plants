import csv
import requests
import os
import json
from tqdm import tqdm

def get_unique_symbols(csv_file):
    symbols = set()
    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row.get('symbol')  # Ensure you are getting the correct column name
            if symbol:
                symbols.add(symbol.strip())
    return symbols


def get_id_for_symbol(symbol):
    url = f'https://plantsservices.sc.egov.usda.gov/api/PlantProfile?symbol={symbol}'
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('Id')
    else:
        print(f"Failed to get ID for symbol {symbol}. Status code: {response.status_code}")
        return None


def get_json_data(id, property):
    url = f'https://plantsservices.sc.egov.usda.gov/api/{property.path}' % (id)
    headers = {'Accept': f'{property.accept}'}
    if property.data:
        post_data = json.load(property.data % (id))
        headers['Content-Type'] = 'application/json'
        response = requests.put(url, data=post_data, headers=headers)
    else:
        response = requests.get(url, headers=headers)        
    if response.status_code == 200:
        if property.accept == 'application/json':
            return response.json()
        else:
            return response.text
    else:
        print(f"Failed to get {data_type} for ID {id}. Status code: {response.status_code}")
        return None

def download_images(symbol, images_json, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    for img_data in tqdm(images_json, desc=f"Downloading images for {symbol}", unit="image"):
        img_url = img_data.get('url')
        if img_url:
            img_response = requests.get(img_url)
            if img_response.status_code == 200:
                img_name = os.path.join(save_dir, img_data.get('filename', f'image_{hash(img_url)}.jpg'))
                with open(img_name, 'wb') as f:
                    f.write(img_response.content)
            else:
                print(f"Failed to download image from {img_url}. Status code: {img_response.status_code}")
    


def main(csv_file):
    symbols = get_unique_symbols(csv_file)
    
    for symbol in tqdm(symbols, desc="Processing symbols", unit="symbol"):
        id = get_id_for_symbol(symbol)
        if id:
            # Assuming we have multiple data types to fetch
            data_types = [
                { "name": "distribution",
                  "path": "getDownloadDistributionDocumentation"
                  "data": '{"Field":"Symbol","SortBy":"sortSciName","Offset":null,"MasterId":"%"}',
                  "accept", "text/csv"
                 },
                {
                    "name":"images",
                    "path":"PlantImages?plantId=%",
                    "data": None,
                    "accept":'application/json'
                },
                {
                    "name": "wetland",
                    "path": "PlantWetland/%"
                    "data": None,
                    "accept":'application/json'
                },
                {
                    "name": "related-links",
                    "path": "PlantRelatedLinks/%",
                    "data": None,
                    "accept": 'application/json'
                },
                {
                    "name": "documentation",
                    "path": "PlantDocumentation/%?orderBy=DataSourceString&offset=-1",
                    "data": None,
                    "accept": 'application/json'
                },
                {
                    "name": "characteristics",
                    "path": "PlantCharacteristics/%",
                    "data": None,
                    "accept": 'application/json"
                }
            ]

            symbol_dir = f'{symbol}'
            if not os.path.exists(symbol_dir):
                os.makedirs(symbol_dir)
            
            # Save the initial JSON
            profile_json = get_json_data(id, 'PlantProfile')
            if profile_json:
                with open(f'{symbol_dir}/{symbol}.json', 'w') as f:
                    json.dump(profile_json, f, indent=4)
            
            for data_type in data_types:
                data = get_json_data(id, data_type)
                if data:
                    with open(f'{symbol_dir}/data_{data_type}.json', 'w') as f:
                        json.dump(data, f, indent=4)
            
            # Assuming images JSON is obtained from one of the API calls
            images_json = get_json_data(id, 'Images')
            if images_json:
                images_dir = f'{symbol_dir}/images'
                with open(f'{images_dir}/images.json', 'w') as f:
                    json.dump(images_json, f, indent=4)
                download_images(symbol, images_json, images_dir)


if __name__ == '__main__':
    main('path_to_csv.csv')
