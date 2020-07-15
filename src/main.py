import json
import requests
import csv
from pprint import pprint 
import os
from datetime import datetime, timedelta

#RetainerTask.csv shows the gathering/ilvl requirement, the time and venture cost, as well as the needed retainer level and class
#RetainerTaskNormal.csv shows what items a venture gives and how many of that item
#Item.csv gives all the information about the items

#TODO check that the server is valid
#TODO check that the csvs don't need updating. Maybe try automatically updating them

cached_prices_address = "../res/cachedPrices.json"
job_to_ClassJobCategory = {'DoW/M': 34, 'MIN':17, 'BTN':18, 'FSH':19}#For retainer task

class RetainerOptimiser():
    def __init__(self, server='Chaos'):
        self.retainer_task_dicts = []
        self.retainer_task_normal_dicts = {}
        self.item_dicts = {}
        self.universalis_handler = UniversalisHandler(server, update=True)

        #Read the CSV files (Assumes they exist. The program can't work without them anyway so it's not a big deal)
        with open('../res/RetainerTask.csv', 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.retainer_task_dicts.append(l)
        with open('../res/RetainerTaskNormal.csv', 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.retainer_task_normal_dicts[l['key']] = l
        with open('../res/Item.csv', 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.item_dicts[l['key']] = l

    def savePrices(self):
        """Tell the universalis handler to save all stored information to the cache json file"""
        self.universalis_handler.save()

    def getVentures(self, level=1, gathering=0, ilvl=0, quantity=2, job=None):
        """Print a list of all ventures given the restrictions, in order of most money per venture to least money per venture"""
        ventures = []
        if not job in job_to_ClassJobCategory.keys():
            raise KeyError

        def isValidGathererVenture(venture):
            """Check if the DoL retainer can do this venture. Returns a boolean"""
            return int(venture['ClassJobCategory']) == job_to_ClassJobCategory[job] and int(venture['RequiredGathering']) <= gathering and int(venture['RetainerLevel']) <= level and venture['VentureCost'] == '1'

        def isValidCombatVenture(venture):
            """Check if the DoW/M retainer can do this venture. Returns a boolean"""
            return int(venture['ClassJobCategory']) == job_to_ClassJobCategory['DoW/M'] and int(venture['RequiredItemLevel']) <= ilvl and int(venture['RetainerLevel']) <= level and venture['VentureCost'] == '1'

        if job == "DoW/M":
            isValidVenture = isValidCombatVenture
        elif job == "MIN" or job == "BTN" or job == "FSH":
            isValidVenture = isValidGathererVenture
        else:
            raise ValueError("Job not recognised")

        for venture in self.retainer_task_dicts[2:]:#Iterate through every single venture in the game
            if isValidVenture(venture): #Can this venture be done by the retainer?
                task_id = venture['Task']
                item_id = self.retainer_task_normal_dicts[task_id]['Item']
                if item_id != '0': #If the id is zero then this venture doesn't reward anything
                    item_name = self.item_dicts[item_id]['0']
                    item_quantity = self.retainer_task_normal_dicts[task_id][f"Quantity[{quantity}]"]
                    retainer_level = venture['RetainerLevel']
                    ventures.append({'item_id': item_id, 'item_name': item_name, 'retainer_level': retainer_level, 'item_quantity': item_quantity}) 

        for v in ventures:
            try:
                v['price'] = self.universalis_handler.getUniversalisPrice(v['item_id']) #Get the price of the item given by this venture
                if v['price']: #Did getUnviersalisPrice return a price?
                    v['income_per_venture'] = v['price'] * int(v['item_quantity'])
                else:
                    v['income_per_venture'] = None
            except PageNotFoundError: #Universalis returned a 404. Probably because the item id was invalid
                print(f"404: {v}")
                v['price'] = None
                v['income_per_venture'] = None

        def sortByIncomePerVenture(venture):
            """Return the income_per_venture if this venture has it, or 0 if it does not."""
            try:
                if venture['income_per_venture']:
                    return venture['income_per_venture']
                else:
                    return 0
            except Exception as e:
                print(venture)
                raise e

        ventures = sorted(ventures, key=sortByIncomePerVenture, reverse=True) #Sort all the ventures with the highest income ventures first, and the lowest income ventures last
        #Display:
        #TODO Can I collate all these for v in ventures?
        header_retainer_level = "Retainer Level"
        retainer_level_colwidth = max([len(v['retainer_level']) for v in ventures] + [len(header_retainer_level)])
        header_item_name = "Item (Quantity)"
        item_name_colwidth = max([len(v['item_name']) for v in ventures] + [len(header_item_name)])
        header_price = "Income per Venture"
        price_colwidth = max([len(str(v['price'])) for v in ventures] + [len(header_price)])
        header_title = f"{header_retainer_level:>{retainer_level_colwidth}} | {header_item_name:^{item_name_colwidth}} | {header_price:<{price_colwidth}}"
        data_to_print = [f"{v['retainer_level']:>{retainer_level_colwidth}} | {(v['item_name']):^{item_name_colwidth}} | {str(v['income_per_venture']):<{price_colwidth}}" for v in ventures]
        print(header_title)
        print(*["=" for i in range(max([len(string) for string in data_to_print] + [len(header_title)]))], sep="") #Prints enough = to cover the width of the widest point of the table
        print(*data_to_print, sep="\n")

class UniversalisHandler():
    def __init__(self, server, update=True):
        self.prices = self.getCachedPrices()
        self.cache_ttl = 3 #The time to live of cached data (in days)
        self.server = server
        self.universalis_url = f"https://universalis.app/api/{server}/"
        self.update = update #Prevents fetching more data from Unviversalis if False and the data needed is present in cache just outdated

    def getCachedPrices(self):
        """Load all item prices from cache"""
        if os.path.isfile(cached_prices_address):
            with open(cached_prices_address) as f:
                return json.load(f)
        else:
            return {}

    def getUniversalisPrice(self, item_id):
        """Get the price for the given item, on the server which this class is set to get data from"""
        if not self.server in self.prices:   
            self.prices[self.server] = {}

        item_id_in_prices = item_id in self.prices[self.server]
        #Data fetched from universalis if there is no data for this item, or if the data we have is outdated and self.update is True
        if not item_id_in_prices or ((datetime.strptime(self.prices[self.server][item_id]['time'], "%Y-%m-%dT%H:%M:%S")) < (datetime.now() - timedelta(days=self.cache_ttl)) and self.update):
            print(f"Fetching {item_id} from Universalis")
            with requests.request("GET", self.universalis_url + item_id + "?entries=1") as response:
                if response.status_code == 404:
                    raise PageNotFoundError()
                response_dict = response.json()
                if not response_dict['listings']:
                    return None
                self.prices[self.server][item_id] = {}
                self.prices[self.server][item_id]['price'] = response_dict['listings'][0]['pricePerUnit']
                self.prices[self.server][item_id]['time'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        return self.prices[self.server][item_id]['price']

    def save(self):
        """Save stored item prices to cache"""
        if self.prices != {}:
            with open(cached_prices_address, 'w') as f:
                json.dump(self.prices, f)

class PageNotFoundError(Exception):
    """Website returned a 404 error"""
    pass

if __name__ == "__main__":
    ro = RetainerOptimiser()
    ro.getVentures(level=80, gathering=5000, job="MIN")
    ro.getVentures(level=80, ilvl=500, job="DoW/M")
    ro.getVentures(level=80, gathering=5000, job="FSH")
    ro.savePrices() #Necessary if you want to save Universalis data to cache
