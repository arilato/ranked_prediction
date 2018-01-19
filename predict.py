import numpy as np
import pandas as pd
import requests
import dataManager
from sklearn.externals import joblib

#api key and base constants
API_BASE = dataManager.API_BASE
API_BASE_CHAMPIONGG = dataManager.API_BASE_CHAMPIONGG
API_KEY_LIST = dataManager.API_KEY_LIST
API_KEY_CHAMPIONGG = dataManager.API_BASE_CHAMPIONGG

#request url constants
MATCHES_REQUEST_ACCOUNT = dataManager.MATCHES_REQUEST_ACCOUNT
MATCHES_REQUEST_MATCHID = dataManager.MATCHES_REQUEST_MATCHID
CHAMPIONS_REQUEST = dataManager.CHAMPIONS_REQUEST
MASTERY_REQUEST = dataManager.MASTERY_REQUEST
SUMMONER_REQUEST = dataManager.SUMMONER_REQUEST
SUMMONER_REQUEST_NAME = dataManager.SUMMONER_REQUEST_NAME
LEAGUE_REQUEST = dataManager.LEAGUE_REQUEST
CHAMPION_REQUEST_GG = dataManager.CHAMPION_REQUEST_GG

#data file save paths
DATA_FILE_PATH = dataManager.DATA_FILE_PATH

RANKED_QUEUE = dataManager.RANKED_QUEUE

ROLE_ORDER = dataManager.ROLE_ORDER
ROLE_LIST = dataManager.ROLE_LIST
TIER_ORDER = dataManager.TIER_ORDER
TIER_LIST = dataManager.TIER_LIST
RANK_ORDER = dataManager.RANK_ORDER
WIN_LOSS_ORDER = dataManager.WIN_LOSS_ORDER
WIN_LOSS_LIST = dataManager.WIN_LOSS_LIST
INDIVIDUAL_FEATURES = dataManager.INDIVIDUAL_FEATURES

#global helper variable for api switching
cur_api = 0

'''
    FUNCTIONS
'''
#helper function to get a request from the api database. We will be using multiple api keys for speedup.
#Takes in the url without the api key, returns -1 if request error, otherwise returns a json() data structure
def get_request(url):
    global cur_api
    req = requests.get(url+API_KEY_LIST[cur_api])
    cur_api += 1
    if cur_api == len(API_KEY_LIST):
        time.sleep(1.2)
        cur_api = 0
    if req.status_code != 200:
        print("Request error: ", req.status_code)
        return -1
    return req.json()

#Takes a summoner name and returns its id
def get_summoner_id(summoner_name):
    req = get_reqeust(SUMMONER_REQUEST_NAME+summoner_name+"?")
    if req == -1: return -1
    return {'accountId':req['accountId'], 'summonerId':req['id']}

'''
Main predict function. Takes the summoner names of top, jg, mid, adc, sup in order, and takes
the champion names of top, jg, mid, adc, sup of both teams in order. Generates sample featureset
for use with interactive mode.
'''

def predict(model, summoners, allyteam, enemyteam):
    #First, convert all summoners to summoner ids
    player_id = [get_summoner_id(i) for i in range(5)]
    #Then, convert all champion names to champion ids
    champData = requests.get("https://na1.api.riotgames.com/lol/static-data/v3/champions?locale=en_US&dataById=false&"+API_KEY_LIST[0])['data']
    ally_id, enemy_id = [0 for i in range(5)], [0 for i in range(5)]
    feature = [[]]
    for j in range(5):
        for i in champData:
            if i['name'].upper() == allyteam[j].upper(): ally_id[j] = i['id']
            if i['name'].upper() == enemyteam[j].upper(): enemy_id[j] = i['id']
        dict = dataManager.generate_player_features(player_id[j], ally_id[j], -1)
        dict2 = dataManager.generate_champion_data(ally_id[j], enemy_id[j], dict['tier'], ROLE_LIST[j])
        dict.update(dict2)
        for i in INDIVIDUAL_FEATURES:
            feature[0].append(dict[i])
    return model.predict(feature), model.predict_proba(feature)


mlpc = joblib.load('models/mlpc.pkl')
gbc = joblib.load('models/gbc.pkl')
print("Ready for user input")
while(1):
    summoners = [input("Enter Summoner with role " + ROLE_LIST[i] + ": ") for i in range(5)]
    allychampions = [input("Enter Ally Champion with role " + ROLE_LIST[i] + ": ") for i in range(5)]
    enemychampions = [input("Enter Enemy Champion with role " + ROLE_LIST[I] + ": ") for i in range(5)]
    pred, prob = predict(gbc, summoners, allychampions, enemychampions)
    print("Predicting ", WIN_LOSS_LIST[pred], "with ", prob[pred], "% chance")







