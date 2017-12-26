import numpy as np
import pandas as pd
import requests
import time

#constants
API_BASE = "https://na1.api.riotgames.com/lol/"
API_KEY = "?api_key=RGAPI-22154b03-a201-4c09-b8f2-7cf6b80d8796"
SELF_ID = 37871085 #my account id for idioticfuse
MATCHES_REQUEST_ACCOUNT = API_BASE + "match/v3/matchlists/by-account/"
MATCHES_REQUEST_MATCHID = API_BASE + "match/v3/matches/"
MATCH_ID_FILE_PATH = "data/match_id.csv"
USER_ID_FILE_PATH = "data/user_id.csv"
MAX_MATCH_IDS = 10**5

'''
This function collects summoner and match ids by branching out from the original id.
We find all unique summoner ids in the 20 previous matches with the original id, then we find
the unique summoner ids in the new summoner id's matches, and so on...
We search until we hit thresh_size amount of unique match ids, then we store it to
our preset file name as a CSV. It is important that we pause 1.25s after every request so
we don't violate the request limits
'''
def get_ids(origin_id, thresh_size):
    id_set = set([origin_id]) #set of unique summoner ids
    match_set = set() #set of unique match ids
    next_id = [origin_id] #'queue' of summoner ids to visit
    passes = 0 #for debugging purposes
    while len(match_set) < thresh_size:
        passes += 1
        print("pass ", passes, ": matches: ", len(match_set), ", ids: ", len(id_set))
        tmp_id = next_id.pop()
        req = requests.get(MATCHES_REQUEST_ACCOUNT+str(tmp_id)+"/recent"+API_KEY)
        time.sleep(1.25)
        if req.status_code != 200: continue
        matchlist = req.json()['matches']
        for i in matchlist:
            if i['gameId'] not in match_set:
                match_set.add(i['gameId'])
                req = requests.get(MATCHES_REQUEST_MATCHID+str(i['gameId'])+API_KEY)
                time.sleep(1.25)
                if req.status_code != 200: continue
                match = req.json()["participantIdentities"]
                for j in match:
                    if j['player']['accountId'] not in id_set:
                        id_set.add(j['player']['accountId'])
                        next_id.append(j['player']['accountId'])
    #we now have our summoner and match id sets, let's store them as a csv
    sets, matches = [i for i in id_set], [i for i in match_set]
    df_id, df_matches = pd.DataFrame([i for i in id_set]), pd.DataFrame([i for i in match_set])
    df_id.to_csv(USER_ID_FILE_PATH)
    df_matches.to_csv(MATCH_ID_FILE_PATH)

get_ids(SELF_ID, MAX_MATCH_IDS)



