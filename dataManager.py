import numpy as np
import pandas as pd
import requests
import time

#constants
api_base = "https://na1.api.riotgames.com/lol/"
api_key = "?api_key=RGAPI-22154b03-a201-4c09-b8f2-7cf6b80d8796"
self_id = 37871085 #my account id for idioticfuse
matches_request_account = api_base + "match/v3/matchlists/by-account/"
matches_request_matchId = api_base + "match/v3/matches/"

#to meet request limits, we will pause 1.25 seconds per request
def get_sum_ids(origin_id, thresh_size): #collects summoner ids based on the original id
    id_set = set(origin_id)
    match_set = set()
    next_id = [origin_id]
    while len(id_set) < thresh_size:
        tmp_id = next_id.pop()
        matchlist = requests.get(matches_request_account+str(tmp_id)+"/recent"+api_key).json()['matches']
        time.sleep(1.25)
        for i in matchlist:
            if i['gameId'] not in match_set:
                match_set.add(i['gameId'])




matchlist = requests.get(matches_request_account+str(self_id)+"/recent"+api_key)
print(matchlist.json()['matches'])



