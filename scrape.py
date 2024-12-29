import csv
import requests
import os
import json
from tqdm import tqdm
import argparse
import time
from requests_toolbelt.utils import dump


data_types = [
    { "name": "distribution",
      "path": "PlantProfile/getDownloadDistributionDocumentation",
      "data": '{{"Field":"Symbol","SortBy":"sortSciName","Offset":null,"MasterId":"{}"}}',
      "accept": "text/csv"
     },
    {
        "name":"images",
        "path":"PlantImages?plantId={}",
        "data": None,
        "accept":'application/json'
    },
    {
        "name": "wetland",
        "path": "PlantWetland/{}",
        "data": None,
        "accept":'application/json'
    },
    {
        "name": "related-links",
        "path": "PlantRelatedLinks/{}",
        "data": None,
        "accept": 'application/json'
    },
    {
        "name": "documentation",
        "path": "PlantDocumentation/{}?orderBy=DataSourceString&offset=-1",
        "data": None,
        "accept": 'application/json'
    },
    {
        "name": "characteristics",
        "path": "PlantCharacteristics/{}",
        "data": None,
        "accept": "application/json"
    }
]

image_path='https://plants.sc.egov.usda.gov/'

def get_unique_symbols(csv_file):
    symbols = set()
    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row.get('Symbol')  # Ensure you are getting the correct column name
            if symbol:
                symbols.add(symbol.strip())
    return sorted(symbols)


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


def get_json_data(id, property, debug=False):
    print(property)
    action = property["path"]
    base = f'https://plantsservices.sc.egov.usda.gov/api/{action}' 
    url =  base.format(id)
    headers = {'Accept': f'{property["accept"]}'}
    if debug:
        print(base)
        print(headers)
    if property["data"]:
        headers["Origin"] = "https://plants.usda.gov"
        headers["Referer"] = "https://plants.usda.gov/"
        headers['Sec-Fetch-Dest'] = 'empty' 
        headers['Sec-Fetch-Mode'] =  'cors' 
        headers['Sec-Fetch-Site'] = 'same-site'
        headers['DNT'] = "1"
        headers['Accept-Language'] = 'en-US,en;q=0.9'

        post = property["data"].format(id)
        post_data = json.loads(post)
        if debug:
            print(post)
            print(headers)
        headers['Content-Type'] = 'application/json'
        response = requests.post(url, json=post_data, headers=headers)
        if debug:
            data = dump.dump_all(response)
            print(data.decode('utf-8'))
    else:
        response = requests.get(url, headers=headers)        
    if response.status_code == 200:
        if property["accept"] == 'application/json':
            return response.json()
        else:
            return response.text
    else:
        name = property["name"]
        print(response.text)
        print(f"Failed to get {name} for ID {id}. Status code: {response.status_code}")
        return None

def download_single_image(save_dir, img_url):
    image_url = f'{image_path}/{img_url}'
    img_response = requests.get(image_url)
    if img_response.status_code == 200:
        img_name = os.path.join(save_dir, os.path.basename(img_url))
        with open(img_name, 'wb') as f:
            f.write(img_response.content)
    else:
        print(f"Failed to download image from {img_url}. Status code: {img_response.status_code}")
    
    
def download_images(symbol, images_json, save_dir):
    for img_data in tqdm(images_json, desc=f"Downloading images for {symbol}", unit="image"):
        for (image) in ["StandardSizeImageLibraryPath",
                         "ThumbnailSizeImageLibraryPath",
                         "LargeSizeImageLibraryPath",
                         "OriginalSizeImageLibraryPath"]:
            img_url = img_data.get(image)
            if img_url:
                download_single_image(save_dir, img_url)

def process_symbol(output_dir, symbol, debug=False):
    id = get_id_for_symbol(symbol)
    if not id:
        print(f'No id for sumbol {symbol}')
        return False
    symbol_dir = f'{output_dir}/{symbol}'
    if not os.path.exists(symbol_dir):
        os.makedirs(symbol_dir)

    # Save the initial JSON
    plant_profile = {
        "name":"plant_profile",
        "path":"PlantProfile?symbol={}",
        "data": None,
        "accept":'application/json'
    }   
    profile_json = get_json_data(symbol, plant_profile)
    if profile_json:
        with open(f'{symbol_dir}/{symbol}.json', 'w') as f:
            json.dump(profile_json, f, indent=4)

    for data_type in data_types:
        data = get_json_data(id, data_type, debug)
        if data:
            document = data_type["name"]
            with open(f'{symbol_dir}/{document}.json', 'w') as f:
                json.dump(data, f, indent=4)

    # Assuming images JSON is obtained from one of the API calls
    images_dir = f'{symbol_dir}/images'
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    images_file = f'{symbol_dir}/images.json'
    print(images_file)
    with open(images_file, 'r') as f:
        images_json = json.load(f)
        print(images_json)
        download_images(symbol, images_json, images_dir)
    return True
                

def process_list(output_dir, csv_file):
    symbols = get_unique_symbols(csv_file)
    total = len(symbols)
    errors = 0
    print(f'We have {total} symbols')
    
    for symbol in tqdm(symbols, desc="Processing symbols", unit="symbol"):
        #print(symbol)
        try:
            process_symbol(output_dir, symbol)
        except:
            print(f'Problem processing {symbol}')
            errors = errors + 1
        time.sleep(1) # Throttle
        
    print(f'{errors}/{total} errors')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download plant data from USDA.')
    
    # Adding arguments
    parser.add_argument('-s', '--symbol', help='Symbol to process')
    parser.add_argument('-o', '--output-dir', default='output', help='Output directory (default: .)')
    parser.add_argument('-i', '--csv-file', default='plants.csv', help='List of plant symbols')    
    
    args = parser.parse_args()
    
    if args.symbol:
        print(f"Processing symbol: {args.symbol}")        
        process_symbol(args.output_dir, args.symbol, True)
    else:
        print(f"Processing list from CSV: {args.csv_file}")        
        process_list(args.output_dir, args.csv_file)

