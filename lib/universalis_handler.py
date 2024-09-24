import asyncio
import os
import logging
from datetime import datetime, timedelta
import json
from typing import Union
from aiohttp import ClientSession
from pathlib import Path

class Throttle:
    def __init__(self, requests_per_second):
        self.requests_per_second = requests_per_second
        self.requests_in_second = 0
        self.last_updated = datetime.now()

    async def throttle(self):
        if self.requests_in_second < self.requests_per_second:
            self.requests_in_second += 1
            return
        elif datetime.now() > self.last_updated + timedelta(milliseconds=100):
            self.requests_in_second = 0
            self.last_updated = datetime.now()
            return await self.throttle()
        else:
            await asyncio.sleep(0.5)  # Suboptimal but works well enough
            return await self.throttle()
        
class UniversalisHandler():
    def __init__(self, response_format, cached_prices_address, session, server="Chaos", update=True):
        self._format_response = response_format
        self.cached_prices_address = cached_prices_address
        self.prices = self._get_cached_prices()
        self.cache_ttl = 0.5  # The time to live of cached data (in days)
        self.server = server
        self.universalis_url = f"https://universalis.app/api/{server}/"
        self.update = update  # Prevents fetching more data from Unviversalis if False and the data needed is present in cache just outdated
        self.fetch_count = 0
        self.throttle = Throttle(1)

    def _get_cached_prices(self):
        """Load all item prices from cache"""
        if os.path.isfile(self.cached_prices_address):
            with open(self.cached_prices_address) as f:
                return json.load(f)
        else:
            return {}

    async def _fetch_single(self, item_id):
        await self.throttle.throttle()
        logging.info(f"Fetching {item_id} from Universalis")
        print(f"Fetching {item_id} from Universalis")
        async with self.session.get(self.universalis_url + item_id) as response:
            if response.status == 404:
                raise PageNotFoundError()

            try:
                response_dict = await response.json(content_type=None)
            except json.JSONDecodeError as err:
                print(await response.text())
                raise err

            return response_dict

    async def _fetch_multiple(self, item_ids):
        query = ",".join(item_ids)
        async with self.session.get(self.universalis_url + query) as response:
            if response.status == 404:
                raise PageNotFoundError()

            try:
                response_dict = (await response.json(content_type=None))['items']
            except json.JSONDecodeError as err:
                print(await response.text())
                raise err

            return response_dict

    async def _update_item(self, item_id):            
        logging.info(f"Updating price for {item_id}")
        self.prices[self.server][item_id] = self._format_response(await self._fetch_single(item_id))
        self.fetch_count += 1
        if self.fetch_count >= 20:
            self.save()
            self.fetch_count = 0
    
    async def _update_items(self, item_ids):
        logging.info(f"Updating price for {item_ids}")
        for resp in await self._fetch_multiple(item_ids):
            self.prices[self.server][str(resp['itemID'])] = self._format_response(resp)
            self.fetch_count += 1
            if self.fetch_count >= 20:
                self.save()
                self.fetch_count = 0

    async def get_universalis_price(self, item_id: Union[str, int], hq: bool = False):
        """Get the price for the given item, on the server which this class is set to get data from"""
        item_id = str(item_id)
        if not self.server in self.prices:
            self.prices[self.server] = {}
        item_id_in_prices = item_id in self.prices[self.server]

        # Data fetched from universalis if there is no data for this item, or if the data we have is outdated and self.update is True
        if not item_id_in_prices or ((datetime.strptime(self.prices[self.server][item_id]['fetch_time'], "%Y-%m-%dT%H:%M:%S")) < (datetime.now() - timedelta(days=self.cache_ttl)) and self.update):          
            print(
                f"Fetching {item_id} from Universalis. item_id_in_prices: {item_id_in_prices}")
            await self.throttle.throttle()
            async with self.session.get(self.universalis_url + item_id) as response:
                if response.status == 404:
                    raise PageNotFoundError()
                
                response_dict = await response.json(content_type=None)
                if not response_dict['listings']:
                    return None
                self.prices[self.server][item_id] = self._format_response(response_dict)
                self.prices[self.server][item_id]['fetch_time'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                
                self.fetch_count += 1
                if self.fetch_count >= 20:
                    self.save()
                    self.fetch_count = 0
        
        return

    def save(self):
        """Save stored item prices to cache"""
        logging.info("Saving prices")
        if self.prices != {}:
            with open(self.cached_prices_address, 'w') as f:
                json.dump(self.prices, f)


class PageNotFoundError(Exception):
    """Website returned a 404 error"""
    pass


class NoHQItemError(Exception):
    """The price for a high quality item was requested but no hq items are listed"""
    pass
