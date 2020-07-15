import json
import requests
import csv
import pprint

universalis_url = "https://universalis.app/api/"
stored_item_values_address = "values.json"
datacenter = "Chaos"

def openCSV():
    dictionary = []
    with open('res/RetainerTaskNormal.csv', 'r') as f:
        reader = csv.DictReader(f)
        for l in reader:
            dictionary.append(l)
    pprint.pprint(dictionary)

def getItemsFromUniversalis(item_values=None):
    with open(stored_item_values_address) as f:
        stored_item_values = json.load(f)
        if not item_values:
            item_values = stored_item_values
    item_prices = {}
    for i in item_values:
        with requests.request("GET", universalis_url + datacenter + "/" + item_values[i]['id'] + "?entries=1") as response:
            response_json = response.json()
            price = response_json['listings'][0]['pricePerUnit']
            price_per_tomestone = float(price) / float(item_values[i]['tomestone_price'])
            item_prices[i] = {'price': price, 'price_per_tomestone': price_per_tomestone}
    sorted_prices = sorted(item_prices.items(), key=lambda x: x[1]['price_per_tomestone'], reverse=True)

    header_price_per_tomestone = "Price per Tomestone"
    header_name = "Item(Unit Price)"
    price_per_colwidth = max([len(str(item[1]['price_per_tomestone'])) for item in item_prices.items()] + [len(header_price_per_tomestone)])
    header_title = f"{header_price_per_tomestone} | {header_name}"
    

    #print(*["=" for i in range(len(header_string))], sep="")
    data_to_print = []
    for k, v in sorted_prices:
        data_to_print.append(f"{str(v['price_per_tomestone']):>{price_per_colwidth}} | {str(k)}({str(v['price'])})")

    print(header_title)
    print(*["=" for i in range(max([len(string) for string in data_to_print] + [len(header_title)]))], sep="") #Prints enough = to cover the width of the widest point of the table
    print(*data_to_print, sep="\n")

if __name__ == "__main__":
    openCSV()
