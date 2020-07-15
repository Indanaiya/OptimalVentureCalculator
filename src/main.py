import json
import requests
import csv
from pprint import pprint 

#RetainerTask.csv shows the gathering/ilvl requirement, the time and venture cost, as well as the needed retainer level and class
#RetainerTaskNormal.csv shows what items a venture gives and how many of that item
#Item.csv gives all the information about the items

universalis_url = "https://universalis.app/api/"
stored_item_values_address = "values.json"
datacenter = "Chaos"
job_to_ClassJobCategory = {'DoW/M': 34, 'MIN':17, 'BTN':18, 'FSH':19}#For retainer task
#ClassJobCategory_to_job = {v:k for k,v in job_to_ClassJobCategory.items()}

class RetainerOptimiser():
    def __init__(self):
        self.retainer_task_dicts = []
        self.retainer_task_normal_dicts = {}
        self.item_dicts = {}

        with open('res/RetainerTask.csv', 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.retainer_task_dicts.append(l)
        with open('res/RetainerTaskNormal.csv', 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.retainer_task_normal_dicts[l['key']] = l
        with open('res/Item.csv', 'r', encoding="UTF-8-sig") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.item_dicts[l['key']] = l

        # for dic in self.retainer_task_normal_dicts[2:]:
        #     if dic['Item'] != '0':
        #         print(self.item_dicts[dic['Item']])

    def getMining(self, level=1, gathering=0):
        for element in self.retainer_task_dicts[2:]:
            if int(element['ClassJobCategory']) == job_to_ClassJobCategory['MIN'] and int(element['RequiredGathering']) <= gathering and int(element['RetainerLevel']) <= level and element['VentureCost'] == '1':
                item_id = self.retainer_task_normal_dicts[element['key']]['Item']
                #print(f"Element: {element['key']}, {self.retainer_task_normal_dicts[element['key']]}")
                print(f"Item id: {item_id}, Item Name: {self.item_dicts[item_id]['0']}")

if __name__ == "__main__":
    ro = RetainerOptimiser()
    ro.getMining(level=10)
