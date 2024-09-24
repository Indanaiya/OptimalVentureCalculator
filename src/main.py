import sys
import csv
import aiohttp
from lib.universalis_handler import *

# RetainerTask.csv shows the gathering/ilvl requirement, the time and venture cost, as well as the needed retainer level and class
# RetainerTaskNormal.csv shows what items a venture gives and how many of that item
# Item.csv gives all the information about the items
# All csv files are from https://github.com/KariArisu/FFXIVDatamine/tree/master

CACHED_PRICES_ADDRESS = "res/cachedPrices.json"
RETAINER_TASK_ADDRESS = "res/RetainerTask.csv"
RETAINER_TASK_NORMAL_ADDRESS = "res/RetainerTaskNormal.csv"
ITEM_ADDRESS = "res/Item.csv"
JOB_TO_CLASS_JOB_CATEGORY = {'DoW/M': 34, 'MIN':17, 'BTN':18, 'FSH':19}

class RetainerOptimiser():
    def __init__(self, server='Chaos'):
        self.retainer_task_dicts = []
        self.retainer_task_normal_dicts = {}
        self.item_dicts = {}
        self.session = aiohttp.ClientSession()
        self.universalis_handler = UniversalisHandler(lambda response_dict : {
        'price': response_dict['listings'][0]['pricePerUnit'],
    }, CACHED_PRICES_ADDRESS, self.session, server=server, update=True)

        # Read the CSV files (Assumes they exist. I could handle their absence more gracefully but crashing works well enough for personal use)
        with open(RETAINER_TASK_ADDRESS, 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.retainer_task_dicts.append(l)
        with open(RETAINER_TASK_NORMAL_ADDRESS, 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.retainer_task_normal_dicts[l['key']] = l
        with open(ITEM_ADDRESS, 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.item_dicts[l['key']] = l

    async def close(self):
        self.universalis_handler.save()
        await self.session.close()

    async def getVentures(self, max_level=1, gathering=0, ilvl=0, quantity=4, job=None):
        """Print a list of all ventures given the restrictions, in order of most money per venture to least money per venture
        
        :param int max_level: List ventures up to and including this level
        :param int gathering: For MIN, BTN, and FSH ventures, list ventures requiring this much gathering stat or less
        :param int ilvl: For DoW/M ventures, list ventures requiring this ilvl or less
        :param int quantity: Ventures can give a range of four different quantities of the item they reward depending on the retainer's ilvl (for DoW/M) or perception (for gathering classes). 1 is the lowest category and 4 is the highest.
        """
        ventures = []
        if not job in JOB_TO_CLASS_JOB_CATEGORY.keys():
            raise KeyError

        def isValidGathererVenture(venture):
            """Check if the DoL retainer can do this venture. Returns a boolean"""
            return int(venture['ClassJobCategory']) == JOB_TO_CLASS_JOB_CATEGORY[job] and int(venture['RequiredGathering']) <= gathering and int(venture['RetainerLevel']) <= max_level and venture['VentureCost'] == '1'

        def isValidCombatVenture(venture):
            """Check if the DoW/M retainer can do this venture. Returns a boolean"""
            return int(venture['ClassJobCategory']) == JOB_TO_CLASS_JOB_CATEGORY['DoW/M'] and int(venture['RequiredItemLevel']) <= ilvl and int(venture['RetainerLevel']) <= max_level and venture['VentureCost'] == '1'

        if job == "DoW/M":
            isValidVenture = isValidCombatVenture
        elif job == "MIN" or job == "BTN" or job == "FSH":
            isValidVenture = isValidGathererVenture
        else:
            raise ValueError("Job not recognised")

        for venture in self.retainer_task_dicts[2:]: # Iterate through every single venture in the game
            if isValidVenture(venture): 
                task_id = venture['Task']
                item_id = self.retainer_task_normal_dicts[task_id]['Item']
                if item_id != '0': # If the id is zero then this venture doesn't reward anything
                    item_name = self.item_dicts[item_id]['0']
                    item_quantity = self.retainer_task_normal_dicts[task_id][f"Quantity[{quantity}]"]
                    retainer_level = venture['RetainerLevel']
                    ventures.append({'item_id': item_id, 'item_name': item_name, 'retainer_level': retainer_level, 'item_quantity': item_quantity}) 

        for v in ventures:
            try:
                v['price'] = await self.universalis_handler.get_universalis_price(v['item_id']) # Get the price of the item given by this venture
                if v['price']: # Did getUnviersalisPrice return a price?
                    v['income_per_venture'] = v['price'] * int(v['item_quantity'])
                else:
                    v['income_per_venture'] = None
            except PageNotFoundError: # Universalis returned a 404. Probably because the item id was invalid
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

        ventures = sorted(ventures, key=sortByIncomePerVenture, reverse=True) # Sort all the ventures with the highest income ventures first, and the lowest income ventures last
        
        # Display:
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

async def run_program():
    if len(sys.argv) != 4:
        print("Please use program as [Program Name] [Job] [Level] [Gathering/iLvl]")
    else:
        job = sys.argv[1]
        if not(job in JOB_TO_CLASS_JOB_CATEGORY.keys()):
            print(f"First argument must be a valid job. {[job for job in JOB_TO_CLASS_JOB_CATEGORY.keys()]}")
            return
        try:
            max_level = int(sys.argv[2])
            if max_level < 1 or max_level > 100:
                raise Exception()
        except:
            print(f"{sys.argv[2]} must be a number between 1 and 100 (inclusive)")
        try:
            gathering_ilvl = int(sys.argv[3])
        except:
            print(f"{sys.argv[3]} must be a number")
    print(f"Finding {job} ventures at level {max_level} with {'iLvl' if job=='DoW/M' else 'gathering'} {gathering_ilvl} for Final Fantasy XIV version 7.05")
    ro = RetainerOptimiser()
    await ro.getVentures(max_level=max_level, ilvl=gathering_ilvl, gathering=gathering_ilvl, job=job)
    await ro.close()
