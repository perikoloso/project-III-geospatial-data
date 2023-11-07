import re
import numpy as np
import pandas as pd
import os
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd

# Get FSQ token from .env file
from dotenv import load_dotenv
load_dotenv() # load_env
token = os.getenv("token")

from getpass import getpass

import requests
#-------------------------------------------------
#-------------------------------------------------

# ------------------------------------------------

def requests_for_foursquare (query, lat, lon, radius=2500,limit=50,category_id=''):

    url = f"https://api.foursquare.com/v3/places/search?query={query}&ll={lat}%2C{lon}&radius={radius}&limit={limit}"

    headers = {
        "accept": "application/json",
        "Authorization": token
    }
    try:
        venues_list = []
        outcome =  requests.get(url, headers=headers).json()["results"]
        
        venues_list.append([
        (   

            v['name'],
            v['geocodes']['main']['latitude'], 
            v['geocodes']['main']['longitude'],
            v['distance'], 
            v['categories'][0]['name']
        ) for v in outcome
    ])


        nearby_places = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
        nearby_places = nearby_places.rename(columns={ 0: 'Name',1: 'Lat',2: 'Long',3:'Distance',4:'Category'})

        return nearby_places

    except:
        print('Error: review code')



#-------------------------------------------------

def get_geodata_company(df_source,name):

    
        filtered_df = df_source[df_source["name"] == name]
        df1 = pd.DataFrame(filtered_df["offices"].explode())
        df_normalized = pd.json_normalize(df1["offices"])
        selected_columns = ["address1","zip_code","city","state_code","country_code", "latitude", "longitude"]
        df_out = df_normalized[selected_columns]
        return df_out
   
def get_coordinates_company(df_source,name):

    try:
        filtered_df = df_source[df_source["name"] == name]
        df1 = pd.DataFrame(filtered_df["offices"].explode())
        df_normalized = pd.json_normalize(df1["offices"])
        selected_columns = ["latitude", "longitude"]
        df_work = df_normalized[selected_columns]
        df_out = df_work[df_work["latitude"].notna()]
        v_latitude = df_out["latitude"][0]
        v_longitude = df_out["longitude"][0]

        return v_latitude,v_longitude
    except:
        return 0,0


def get_one_venue (one_venue):

    name = one_venue["name"]
    address = one_venue["location"]["address"]
    distance = one_venue["distance"]
    zip_code = one_venue["location"]["postcode"]
    lat = one_venue["geocodes"]["main"]["latitude"]
    lon = one_venue["geocodes"]["main"]["longitude"]

    
    venue_data = {
    "name": name,
    "address": address,
    "zip_code": zip_code,
    "distance": distance,
    "lat": lat,
    "lon": lon
}
    return venue_data

def create_geojson(dataframe, filename):
    # Create a GeoDataFrame from the DataFrame
    geometry = [Point(xy) for xy in zip(dataframe['Long'], dataframe['Lat'])]
    gdf = gpd.GeoDataFrame(dataframe, geometry=geometry)
    # Save the GeoDataFrame to a GeoJSON file
    gdf.to_file(filename, driver='GeoJSON')




def filtering_companies (df,filters):
    query = list(df.find(filters, projection= {"name":1,"category_code":1, "offices.city":1,'_id':0, "number_of_employees":1,'founded_year':1,
                                                           "total_money_raised":1, "tag_list":1,"offices.latitude":1, "offices.longitude":1,"offices.country_code":1}))
    df=pd.DataFrame(query)
    df['city1'] = df['offices'].apply(lambda x: x[0]['city'] if x and len(x) > 0 else None)
    df['city2'] = df['offices'].apply(lambda x: x[1]['city'] if x and len(x) > 1 else None)
    df['country'] = df['offices'].apply(lambda x: x[1]['country_code'] if x and len(x) > 1 else None)
    df['lat'] = [x[0]['latitude'] if x and 'latitude' in x[0] else 'N/A' for x in df['offices']]
    df['lon'] = [x[0]['longitude'] if x and 'longitude' in x[0] else 'N/A' for x in df['offices']]
    
    df.drop('offices', axis=1, inplace=True)
    df =df.sort_values('founded_year',ascending =False)
    
    return df

def get_topics(df,topics):
    result = pd.DataFrame()
    list_topics = topics
    for i in list_topics:
        for index, row in df.iterrows():
            df_out = requests_for_foursquare(i,row["lat"],row["lon"])
            df_out ["Company"]=row["name"]
            df_out ["City"]=row["city1"]
            result = pd.concat([result, df_out], ignore_index=True)
    return result

def convert_to_amount(string):
    
    # Check if the string contains "B" for billion and adjust the multiplier
    multiplier = 1
    if 'B' in string:
        string = re.sub(r'[\$\s]', '', string)
        multiplier = 1e9  # 1 billion
        string = string.replace('B', '').strip()

    # Check if the string contains "M" for million and adjust the multiplier
    if 'M' in string:
        multiplier = 1e6  # 1 million
        string = re.sub(r'[\$\s]', '', string)
        string = string.replace('M', '').strip()

    if 'k' in string:
        multiplier = 1000  # 1 thousand
        string = re.sub(r'[\$\s]', '', string)
        string = string.replace('k', '').strip()
        
    # Convert the modified string to a float and apply the multiplier
    numeric_value = float(string) * multiplier

    return numeric_value
   
