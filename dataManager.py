import numpy as np
import pandas as pd
import requests
import itertools
import time
import sys

#api key and base constants
API_BASE = "https://na1.api.riotgames.com/lol/"
API_BASE_CHAMPIONGG = "http://api.champion.gg/v2/champions/"
API_KEY = "api_key=RGAPI-8fedf7f8-7c95-43ca-a638-1090b1d32126"
API_KEY_LIST = ["api_key=RGAPI-cdf44912-8580-4a03-ae38-b63daac8a1c8",
                "api_key=RGAPI-7fda51d1-d6a4-4ffc-8c01-83a2a2b7b6be",
                "api_key=RGAPI-98ecaf7a-4306-433c-8a3d-002c1a9bd3b2",
                "api_key=RGAPI-01de53eb-47e5-4af8-a6a4-de5ab0a0cbaf"]
API_KEY_CHAMPIONGG = "api_key=977d33e558311e9fcd259e4314d4115d"

SELF_ID = 37871085 #my account id for idioticfuse, this will be the seed
unix_time_limit = 0.5 #this is the maximum number of days that can pass for the match to be valid as a sample point, so we only get recent matches.

#request url constants
MATCHES_REQUEST_ACCOUNT = API_BASE + "match/v3/matchlists/by-account/"
MATCHES_REQUEST_MATCHID = API_BASE + "match/v3/matches/"
CHAMPIONS_REQUEST = API_BASE + "static-data/v3/champions?locale=en_US&dataById=false"
MASTERY_REQUEST = API_BASE + "champion-mastery/v3/champion-masteries/by-summoner/"
SUMMONER_REQUEST = API_BASE + "summoner/v3/summoners/by-account/"
SUMMONER_REQUEST_NAME = API_BASE + "summoner/v3/summoners/by-name/"
LEAGUE_REQUEST = API_BASE + "league/v3/positions/by-summoner/"
CHAMPION_REQUEST_GG = "?champData=averageGames,overallPerformanceScore,matchups&limit=200"

#data file save paths
MATCH_ID_FILE_PATH = "data/match_id.csv"
USER_ID_FILE_PATH = "data/user_id.csv"
CONTINUE_FILE_PATH = "data/get_id_continue.csv"
CHAMPION_FILE_PATH = "data/champions.csv"
FEATURIZED_MATCHES_FILE_PATH = "data/featurized_matches.csv"
DATA_FILE_PATH = "data/data.csv"

MAX_MATCH_IDS = 10000
RANKED_QUEUE = 420 #lol its lit

ROLE_ORDER = {"TOP":0, "JUNGLE":1, "MIDDLE":2, "DUO_CARRY":3, "DUO_SUPPORT":4}
ROLE_LIST = ["TOP", "JUNGLE", "MIDDLE", "DUO_CARRY", "DUO_SUPPORT"]
TIER_ORDER = {"BRONZE":0, "SILVER":1, "GOLD":2, "PLATINUM":3, "DIAMOND":4, "MASTER":5}
TIER_LIST = ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER"]
RANK_ORDER = {"V":0, "IV":1, "III":2, "II":3, "I":4}
WIN_LOSS_ORDER = {"Win":1, "Fail":0}
WIN_LOSS_LIST = ["Loss", "Win"]

INDIVIDUAL_FEATURES = ["champion_winrate", "champion_playrate", "champion_percentRolePlayed",
                       "champion_overallPerformanceScore", "champion_matchupWinrate", "wins_last2",
                       "wins_last15", "gamesPlayed", "gamesPlayedRanked", "lanePlayed",
                       "lanePlayedRanked", "championPoints", "summonerLevel", "rank"]
TEAM_FEATURES = ["win"]
FULL_FEATURES = [i+"_"+j for i,j in itertools.product(ROLE_LIST,INDIVIDUAL_FEATURES)]
FULL_FEATURES.extend(TEAM_FEATURES)

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
        print("Request error: ", req.status_code, cur_api-1)
        return -1
    return req.json()

#riot's system has a hard time determining adc from support, and sometimes lists both roles as 'DUO'.
#To combat this, the following function takes two champion ids, and returns which has a higher playrate as
#an adc

def get_adc(champ1, champ2):
    req1 = requests.get(API_BASE_CHAMPIONGG+str(champ1)+CHAMPION_REQUEST_GG+"&"+API_KEY_CHAMPIONGG)
    req2 = requests.get(API_BASE_CHAMPIONGG+str(champ2)+CHAMPION_REQUEST_GG+"&"+API_KEY_CHAMPIONGG)
    #error
    time.sleep(0.2)
    if req1.status_code != 200 or req2.status_code != 200:
        raise NameError()
    data1 = req1.json()
    data2 = req2.json()

    playrate1, playrate2 = 0, 0
    for i in data1:
        if i['_id']['role'] == 'DUO_CARRY':
            playrate1 = i['playRate']
            break
    for i in data2:
        if i['_id']['role'] == 'DUO_CARRY':
            playrate2 = i['playRate']
            break

    if playrate1 < playrate2: return champ2
    else: return champ1


'''
    This function takes in a sample, and transforms it into another sample using its existing features.
    For reference, existing features are, TOP, JG, MID, ADC, SUP, with each having
    (0)champion_winrate, (1)champion_playrate, (2)champion_percentRolePlayed, (3)champion_overallPerformanceScore,
    (4)champion_matchupWinrate, (5)wins_last2, (6)wins_last15, (7)gamesPlayed, (8)gamesPlayedRanked, (9)lanePlayed,
    (10)lanePlayedRanked, (11)championPoints, (12)summonerLevel, (13)rank
    14 total original features per role
'''
def transform_features(sample, trans=True, player_winrate_only=False, champion_winrate_only=False, rank_only=False,
                       gamesPlayedRanked=False, gamesPlayed=False, lanePlayed=False):
    newsample = []
    if champion_winrate_only == True:
        newsample.extend([sample[i*14] for i in range(5)])
    if player_winrate_only == True:
        newsample.extend([sample[6+i*14] for i in range(5)])
    if gamesPlayed == True:
        newsample.extend([sample[7+i*14] for i in range(5)])
    if gamesPlayedRanked == True:
        newsample.extend([sample[8+i*14] for i in range(5)])
    if lanePlayed == True:
        newsample.extend([sample[9+i*14] for i in range(5)])
    if rank_only == True:
        newsample.extend([sample[13+i*14] for i in range(5)])
    
    if trans == True:
        n_features = 14
        new_features = [[] for i in range(5)]
        for i in range(5):
            #New feature: player_transformed_winrate = wins_last15/min(gamesPlayedRanked, 15)
            new_features[i].append(sample[6+i*14]/max(min(15,sample[8+i*14]),1))
            #New feature: player_compared_winrate = champion_winrate - player_transformed_winrate
            new_features[i].append(sample[i*14]-new_features[i][0])
        #Testing removal of certain features
        #Remove summonerLevel
        sample = np.delete(sample, [12+i*14 for i in range(5)]).tolist()
        
        #add new features to sample
        sample.extend(np.array(new_features).flatten())
        newsample = sample
    return newsample

'''
given two champion ids and rank as a string, returns two dictionaries:
champion_winrate
champion_playrate
champion_percentRolePlayed
matchup_winrate
overallPerformanceScore
Total API requests: 2(GG)
'''
def generate_champion_data(champion1, champion2, rank, role):
    champ_dict1, champ_dict2 = {}, {}
    #get data for champ1
    if rank == "DIAMOND" or rank == "MASTER" or rank == "CHALLENGER":
        req = requests.get(API_BASE_CHAMPIONGG+str(champion1)+CHAMPION_REQUEST_GG+"&"+API_KEY_CHAMPIONGG)
    else:
        req = requests.get(API_BASE_CHAMPIONGG+str(champion1)+CHAMPION_REQUEST_GG+"&elo="+rank+"&"+API_KEY_CHAMPIONGG)
    time.sleep(0.2)
    if req.status_code != 200: return -1
    data = req.json()
    for i in data:
        if i['_id']['role'] == role: #we found which one we want
            champ_dict1['champion_winrate'] = i['winRate']
            champ_dict1['champion_playrate'] = i['playRate']
            champ_dict1['champion_percentRolePlayed'] = i['percentRolePlayed']
            champ_dict1['champion_overallPerformanceScore'] = i['overallPerformanceScore']
            for j in i['matchups'][role]:
                if j['champ2_id'] == champion2:
                    champ_dict1['champion_matchupWinrate'] = j['champ1']['winrate']
                    champ_dict2['champion_matchupWinrate'] = 1-j['champ1']['winrate']
                    break
                if j['champ1_id'] == champion2:
                    champ_dict2['champion_matchupWinrate'] = j['champ1']['winrate']
                    champ_dict1['champion_matchupWinrate'] = 1-j['champ1']['winrate']
            break
    #get data for champ2
    if rank == "DIAMOND" or rank == "MASTER" or rank == "CHALLENGER":
        req = requests.get(API_BASE_CHAMPIONGG+str(champion2)+CHAMPION_REQUEST_GG+"&"+API_KEY_CHAMPIONGG)
    else:
        req = requests.get(API_BASE_CHAMPIONGG+str(champion2)+CHAMPION_REQUEST_GG+"&elo="+rank+"&"+API_KEY_CHAMPIONGG)
    time.sleep(0.2)
    if req.status_code != 200: return -1
    data = req.json()
    for i in data:
        if i['_id']['role'] == role: #we found which one we want
            champ_dict2['champion_winrate'] = i['winRate']
            champ_dict2['champion_playrate'] = i['playRate']
            champ_dict2['champion_percentRolePlayed'] = i['percentRolePlayed']
            champ_dict2['champion_overallPerformanceScore'] = i['overallPerformanceScore']
            break
    return champ_dict1, champ_dict2

'''
given a player id and champion id, compiles the last 500 games by the player, and returns the following dictionary:
wins_last2(ranked) - feature for tilt
wins_last15(ranked)*
gamesplayed(ranked)*
championPoints*
summonerLevel
rank
* = champion specific
Total API Requests: 18(Riot)
'''
def generate_player_features(player, championId, matchId):
    player_dict = {} #setup dictionary that we will return
    req = get_request(SUMMONER_REQUEST+str(player)+"?") #gets summoner id and level
    player_dict['summonerId'] = req['id']
    player_dict['summonerLevel'] = req['summonerLevel']
    
    #gets champion points
    req = get_request(MASTERY_REQUEST+str(player_dict['summonerId'])+"/by-champion/"+str(championId)+"?")
    player_dict['championPoints'] = req['championPoints']
    
    req = get_request(LEAGUE_REQUEST+str(player_dict['summonerId'])+"?") #gets rank of player
    for i in req:
        if i['queueType'] == "RANKED_SOLO_5x5":
            player_dict['rank'] = TIER_ORDER[i['tier']]*500+(4-RANK_ORDER[i['rank']])*100+i['leaguePoints']
            player_dict['tier'] = i['tier']
            break
    
    #now, we go through the last 200 ranked games played, and generate the rest of the features
    player_dict['gamesPlayed'] = 0
    player_dict['gamesPlayedRanked'] = 0
    player_dict['lanePlayed'] = 0
    player_dict['lanePlayedRanked'] = 0
    player_dict['wins_last2'] = 0
    player_dict['wins_last15'] = 0
    games_recorded = 0
    tilt_recorded = 0
    flag = False
    lane = "none"
    if matchId == -1: flag = True
    for i in [0, 100, 200]:
        req = get_request(MATCHES_REQUEST_ACCOUNT+str(player)+"?beginIndex="+str(i)+"&")
        for j in req['matches']:
            if j['gameId'] == matchId:
                flag = True
                lane = j['lane']
                continue
            if flag == False:
                continue
            if j['champion'] == championId: player_dict['gamesPlayed'] += 1
            if j['lane'] == lane: player_dict['lanePlayed'] += 1
            if tilt_recorded < 2:
                tilt_recorded += 1
                req2 = get_request(MATCHES_REQUEST_MATCHID+str(j['gameId'])+'?')
                for k in req2['participantIdentities']:
                    if k['player']['accountId'] == player: #found a match
                        if k['participantId'] < 6:
                            player_dict['wins_last2'] += WIN_LOSS_ORDER[req2['teams'][0]['win']]
                        else:
                            player_dict['wins_last2'] += WIN_LOSS_ORDER[req2['teams'][1]['win']]
                        break
    flag = False
    for i in [0, 100, 200]:
        req = get_request(MATCHES_REQUEST_ACCOUNT+str(player)+"?queue=420&beginIndex="+str(i)+"&")
        for j in req['matches']:
            if j['gameId'] == matchId:
                flag = True
                continue
            if flag == False: continue
            if j['lane'] == lane: player_dict['lanePlayedRanked'] += 1
            if j['champion'] != championId: continue #we don't care about games not involving our champion
            if games_recorded < 15: #if part of most recent 10 games, we have to find wins
                games_recorded += 1
                req2 = get_request(MATCHES_REQUEST_MATCHID+str(j['gameId'])+'?')
                for k in req2['participantIdentities']:
                    if k['player']['accountId'] == player: #found a match
                        if k['participantId'] < 6:
                            player_dict['wins_last15'] += WIN_LOSS_ORDER[req2['teams'][0]['win']]
                        else:
                            player_dict['wins_last15'] += WIN_LOSS_ORDER[req2['teams'][1]['win']]
                        break
            player_dict['gamesPlayedRanked'] += 1
    return player_dict

'''
Given a match id, generates two feature sets for that match - one for each team. The features we are interested in are:
wins_last2(ranked). - feature for tilt
wins_last15(ranked)*.
gamesplayed(ranked)*.
championPoints*.
summonerLevel.
rank.
champion_winrate*<
champion_playrate*<
champion_percentRolePlayed*<
champion_overallPerformanceScore*<
matchup_winrate*<

* = champion specific
. = player specific
< = rank specific
Total API Requests: 181(Riot), 20(GG) - 3 minutes without multiple API Keys
Generates 2 samples
'''
def generate_featureset(match):
    match_data = get_request(MATCHES_REQUEST_MATCHID+str(match)+"?")
    if match_data == -1: return -1
    #generate the two teams' player dictionaries, in order of [top jg mid adc sup]
    team = {0:{}, 1:{}}
    #generates win t/f for each team
    team[0]['win'] = WIN_LOSS_ORDER[match_data['teams'][0]['win']]
    team[1]['win'] = WIN_LOSS_ORDER[match_data['teams'][1]['win']]
    
    participantId_index_dict = {}
    duo_pairs = [[], []]
    adc_index = [-1, -1]
    for i in match_data['participants']:
        if i['timeline']['role'] == 'DUO':
            if i['participantId'] < 6: duo_pairs[0].append(i['championId'])
            else: duo_pairs[1].append(i['championId'])
    if len(duo_pairs[0]) == 1 or len(duo_pairs[1]) == 1:
        print("Unequal unmarked duo lane assignment, sample discarded.")
        raise NameError()
    
    for i in range(2):
        if len(duo_pairs[i]) == 2:
            adc = get_adc(duo_pairs[i][0], duo_pairs[i][1])
            for j in match_data['participants']:
                if j['timeline']['role'] == 'DUO' and j['participantId'] > 5*i and j['participantId'] < 6+5*i:
                    if j['championId'] == adc: j['timeline']['role'] = 'DUO_CARRY'
                    else: j['timeline']['role'] = 'DUO_SUPPORT'

    
    for i in match_data['participants']: #generates player specific dictionary values
        if i['participantId'] < 6: teamId = 0
        else: teamId = 1
        if i['timeline']['lane'] == "BOTTOM": index = ROLE_ORDER[i['timeline']['role']] #generate index based on role
        else: index = ROLE_ORDER[i['timeline']['lane']]
        participantId_index_dict[i['participantId']] = index
        
        team[teamId][ROLE_LIST[index]] = {'role':index}
        team[teamId][ROLE_LIST[index]]['spell1Id'] = i['spell1Id']
        team[teamId][ROLE_LIST[index]]['spell2Id'] = i['spell2Id']
        team[teamId][ROLE_LIST[index]]['highestAchievedSeasonTier'] = i['highestAchievedSeasonTier']
        team[teamId][ROLE_LIST[index]]['championId'] = i['championId']
    
    #sanity check - Riot's API is notorious for inaccurately predicting role assignments. If that is the case
    #with the current data, we will simply discard it
    for i in range(2):
        for j in ROLE_LIST:
            if j not in team[i]:
                print("Match Skipped due to inaccurate role assignments")
                raise NameError()
    
    for i in match_data['participantIdentities']: #generates account ids for each player
        if i['participantId'] < 6: teamId = 0
        else: teamId = 1
        team[teamId][ROLE_LIST[participantId_index_dict[i['participantId']]]]['accountId'] = i['player']['accountId']

    #generates more player and champion specific dictionary values with use of helper function
    for i in range(2): #which team?
        for j in ROLE_LIST: #which role?
            print(i)
            team[i][j].update(generate_player_features(team[i][j]['accountId'], team[i][j]['championId'], match))
            if i == 0:
                dict1, dict2 = generate_champion_data(team[i][j]['championId'], team[1-i][j]['championId'],
                                                     team[i][j]['tier'], j)
                team[0][j].update(dict1)
                team[1][j].update(dict2)
    #now we have our full dictionary, let's transform it into features!
    data = [[], []]
    for i in range(2):
        for j in ROLE_LIST:
            for k in INDIVIDUAL_FEATURES:
                if k in team[i][j]:
                    data[i].append(team[i][j][k])
                else:
                    data[i].append(float('nan'))
                    print(j, k, "is NaN")
        data[i].append(team[i]['win'])
    return data

'''
This is our main function that will call each match and generates 2 samples for it using our helper functions.
Since it will take an insanely long time to get every single match down, we will be running this function in
batches, specified by lim
With 4 Riot API keys: 1.18s per match
'''
def generate_data(lim, cont=False):
    featurizedMatches = set()
    data = []
    if cont == True:
        df_featurizedMatches, df_data = pd.read_csv(FEATURIZED_MATCHES_FILE_PATH), pd.read_csv(DATA_FILE_PATH)
        featurizedMatches = set([i for i in df_featurizedMatches.values[:,1]])
        data = df_data.values[:,1:].tolist()
    matches = pd.read_csv(MATCH_ID_FILE_PATH).values[:,1]
    count = 1
    for i, match in enumerate(matches):
        if count > lim: break
        if match not in featurizedMatches:
            featurizedMatches.add(match)
            try:
                tmp = generate_featureset(match)
            except:
                tmp = -1
                print("Unexpected error:", sys.exc_info()[0])
            if tmp != -1: data.extend(tmp)
            print("Pass ", count)
            count += 1
    print("Saving")
    df_featurizedMatches, df_data = pd.DataFrame([i for i in featurizedMatches]), pd.DataFrame(data)
    df_featurizedMatches.to_csv(FEATURIZED_MATCHES_FILE_PATH)
    df_data.to_csv(DATA_FILE_PATH)
    return

'''
    This function collects summoner and match ids by branching out from the original id.
    We find all unique summoner ids in the 20 previous matches with the original id, then we find
    the unique summoner ids in the new summoner id's matches, and so on...
    We search until we hit thresh_size amount of unique match ids, then we store it to
    our preset file name as a CSV. It is important that we pause 1.25s after every request so
    we don't violate the request limits.
    While crawling matches, we note the start time of the match. If it is recent (defined in constants),
    we featurize the match and add it as a sample to our data.
    '''
def get_ids(origin_id, thresh_size, lim, cont=False): #note: this only collects RANKED data
    if cont == True: #if we are continuing from last time
        #for match/summoner crawling:
        df_id, df_matches = pd.read_csv(USER_ID_FILE_PATH), pd.read_csv(MATCH_ID_FILE_PATH),
        df_continue = pd.read_csv(CONTINUE_FILE_PATH)
        id_set = set(df_id.values[:,1])
        match_set = set(df_matches.values[:,1])
        next_id = df_continue.values[:,1].tolist()
        #for dataset collection:
        df_data = pd.read_csv(DATA_FILE_PATH)
        data = df_data.values[:,1:].tolist()
    else: #we start from scratch
        id_set = set([origin_id]) #set of unique summoner ids
        match_set = set() #set of unique match ids
        next_id = [origin_id] #random 'queue' of summoner ids to visit
        data = []

    passes = 0 #for debugging purposes
    count = 0 #how many matches have we turned to samples?
    
    while len(match_set) < thresh_size and len(data) < lim:
        if (len(next_id) == 0):
            print("Ran out of summoner ids")
            break
        passes += 1
        print("pass ", passes, ": matches: ", len(match_set), ", ids: ", len(id_set), ", samples: ", len(data))
        randindex = np.random.randint(0, len(next_id)) #we sample randomly from our 'queue'
        tmp_id = next_id.pop(randindex)
        req = get_request(MATCHES_REQUEST_ACCOUNT+str(tmp_id)+"?queue=420&")
        if req == -1:
            print("error requesting matches by account data")
            continue
        matchlist = req['matches']
        for i in matchlist[0:5]: #only take the 5 most recent games so we don't end up going too far back in time
            if i['queue'] == RANKED_QUEUE and i['season'] == 9 and i['gameId'] not in match_set:
                req = get_request(MATCHES_REQUEST_MATCHID+str(i['gameId'])+"?")
                if req == -1: continue
                match_set.add(i['gameId'])
                match = req['participantIdentities']
                for j in match:
                    if j['player']['accountId'] not in id_set:
                        id_set.add(j['player']['accountId'])
                        next_id.append(j['player']['accountId'])
            if i['timestamp'] / 1000 > time.time() - 24 * 60 * 60 * unix_time_limit:
                count += 1
                try:
                    tmp = generate_featureset(i['gameId'])
                except:
                    tmp = -1
                    print("Unexpected error:", sys.exc_info()[0])
                if tmp != -1: data.extend(tmp)
                print("Data Pass ", count)
    #save the dataset
    print("Saving")
    df_data = pd.DataFrame(data)
    df_data.to_csv(DATA_FILE_PATH)
    #save crawl data
    df_id, df_matches = pd.DataFrame([i for i in id_set]), pd.DataFrame([i for i in match_set])
    df_continue = pd.DataFrame(next_id)
    df_continue.to_csv(CONTINUE_FILE_PATH)
    df_id.to_csv(USER_ID_FILE_PATH)
    df_matches.to_csv(MATCH_ID_FILE_PATH)

if __name__ == "__main__":
    #generate_data(lim=750,cont=True)
    get_ids(SELF_ID, thresh_size=100000, lim=3600, cont=True)
    #print(generate_featureset(2680651793))



