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

class RetainerOptimiser():
    def __init__(self):
        self.retainer_task_dicts = []
        self.retainer_task_normal_dicts = []
        self.item_dicts = {}

        with open('res/RetainerTask.csv', 'r', encoding="UTF-8") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.retainer_task_dicts.append(l)
        with open('res/RetainerTaskNormal.csv', 'r', encoding="UTF-8") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.retainer_task_normal_dicts.append(l)
        with open('res/Item.csv', 'r', encoding="UTF-8") as f:
            reader = csv.DictReader(f)
            for l in reader:
                self.item_dicts[l['key']] = l

        for dic in self.retainer_task_normal_dicts[2:]:
            if dic['Item'] != '0':
                print(self.item_dicts[dic['Item']])


if __name__ == "__main__":
    RetainerOptimiser()
