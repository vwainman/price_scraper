from bs4 import BeautifulSoup 
from datetime import date
import requests              
import re
import locale
from typing import TypeVar, Text
from tqdm import tqdm

#TODO: github settings, separate into modules, linting, docstrings, website compatibility and unit testing

StrUInt = TypeVar('StrUInt', Text, int)
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

INTRO = "\nPlease use this scraper responsibly.\n\n"\
      + "This program scrapes and searches for the best deals for a desired product on a particular website.\n"\
      + "Since this is a work in progress, it can only scrape newegg.ca.\n\n"\
      + "Usage: Follow the input prompts and type quit to exit at any time.\n"

COMPATIBLE_WEBSITES = ["newegg"]

class Website:
    def __init__(self, name: str, 
                 search_url: str, 
                 pagination_class: str, 
                 wrapper_class: str,
                 item_container_class: str,
                 price_class: str):
        self.__name = name
        self.__search_url = search_url
        self.__pagination_class = pagination_class
        self.__wrapper_class = wrapper_class
        self.__item_container_class = item_container_class
        self.__price_class = price_class

    @property
    def name(self):
        return self.__name
    
    @property
    def search_url(self):
        return self.__search_url

    @property
    def pagination_class(self):
        return self.__pagination_class
    
    @property
    def wrapper_class(self):
        return self.__wrapper_class

    @property
    def item_container_class(self):
        return self.__item_container_class
    
    @property
    def price_class(self):
        return self.__price_class
    
class SortedListings:
    def __init__(self, listings: dict, n_listings_output: int):
        self.__n_listings_output = n_listings_output
        self.__sorted_listings: list = self.__sorted_by_price(listings)
    
    @property
    def sorted_listings(self):
        return self.__sorted_listings

    @property
    def n_listings_output(self):
        return self.__n_listings_output

    def __sorted_by_price(self, listings: dict) -> list: 
        sorted_listings = sorted(listings.items(), key=lambda x: x[1]['price'])
        if len(sorted_listings) > self.__n_listings_output: 
            return sorted_listings[:self.n_listings_output]
        else:
            return sorted_listings
                
    def __str__(self):
        string = ""
        for i, item in enumerate(self.sorted_listings):
            string += f"{i+1}.\n"
            string += f"Name: {item[0]}\n"
            string += f"Price: ${item[1]['price']:.2f}\n"
            string += f"Link: {item[1]['link']}\n\n"
        return string[:-1]
    
    def save_to_file(self, filename: str) -> None:
        with open(filename, "a") as f:
            f.write(str(self))

class WebFileHandler:
    def __init__(self, item_name: str, page_type: str, website: Website):
        self.__item_name: str = item_name
        self.__page_type: str = page_type
        self.__website: Website = website
        self.__search_url: str = f"{website.search_url}{item_name}"
        if self.__website.name.lower().strip() not in COMPATIBLE_WEBSITES:
            raise Exception(f"{self.__website.name} is not currently supported")
        
    def __get_doc(self, url) -> BeautifulSoup:
        page = requests.get(url).text
        return BeautifulSoup(page, f"{self.__page_type}.parser")
        
    def __get_n_page_listings(self, doc: BeautifulSoup) -> int:
        pagination_html = str(doc.find(class_ = self.__website.pagination_class))
        # finding and returning the last occurence of a number in the html string
        match = re.findall(r'\d+', pagination_html)[-1]
        return int(match)
    
    def get_listings(self) -> dict:
        # TODO: add compatibility with a range of websites
        listings = {}
        doc: BeautifulSoup = self.__get_doc(self.__search_url)
        n_page_listings: int = self.__get_n_page_listings(doc)
        
        if self.__website.name.lower() == "newegg":

            for i in tqdm(range(1, n_page_listings + 1)):
                doc: BeautifulSoup = self.__get_doc(self.__search_url + f"&page={i}")
                # this will narrow our search context to the products listed on each page to avoid false-positives like the search bar
                products_container = doc.find(class_ = self.__website.wrapper_class)
                matching_products = products_container.find_all(text = re.compile(self.__item_name))

                for match in matching_products:
                    attributes = self.__get_product_details(match)
                    # verify that our match was valid
                    if attributes is not None:
                        listings[match] = attributes
        return listings
    
    def __get_product_details(self, product):
        # TODO: attempt compatibility with a range of websites
        link = None
        # some matches will be devoid of links because they're html tags
        if product.parent.name == "a":
            link = product.parent['href']
            container = product.find_parent(class_ = self.__website.item_container_class)
            # TODO: refactor -- some prices do not have the strong attribute or something else is slipping through the cracks?
            try:
                price_container_html = container.find(class_ = self.__website.price_class)
                price = locale.atof(price_container_html.strong.string)
            except: 
                return None
            return {"price": price, "link": link}
        else:
            return None
        
        
class UserInterface:
    def execute():
        print(INTRO)
        while(True):
            product_name = UserInterface.filter_input("What item are you looking for? ", "str")
            n_listings = UserInterface.filter_input("How many listings do you want to see: ", "uint")
            handler = WebFileHandler(item_name=product_name, page_type="html", 
                                     website=NEWEGG)
            listings = SortedListings(handler.get_listings(), n_listings)
            print("\n", listings)
            user_input = UserInterface.filter_input("Would you like to save the results to a text file? Type 'yes' or 'no' ", "str")
            if user_input.lower() == "yes":
                fname = f"{product_name}_listings_{date.today().strftime('%d-%m-%Y')}.txt"
                listings.save_to_file(fname)
                print(f"Your results were saved to {fname}")
            else:
                print("Your results were not saved to a file")
    
    @staticmethod
    def filter_input(input_message: str, type: str) -> StrUInt:
        user_input = input(input_message)
        if user_input.lower().strip() == "quit":
            quit()
        elif type == "uint" and int(user_input) > 0:
            return int(user_input)
        elif type == "str":
            return user_input
        else:
            raise TypeError("Invalid input")
        
NEWEGG = Website(name = "newegg", 
                 search_url = "https://www.newegg.ca/p/pl?d=", 
                 pagination_class = "list-tool-pagination-text",
                 wrapper_class = "item-cells-wrap border-cells items-grid-view four-cells expulsion-one-cell",
                 item_container_class = "item-container",
                 price_class = "price-current")

test = UserInterface
test.execute()