from sklearn.model_selection import KFold
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.externals import joblib
from sklearn import tree
from dataManager import transform_features
from sklearn.naive_bayes import MultinomialNB
import math
import models
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pylab

def grid_search(model, params, trainx, trainy):
    gsearch = GridSearchCV(estimator = model, param_grid = params)
    gsearch.fit(trainx, trainy)
    return gsearch.grid_scores_, gsearch.best_params_, gsearch.best_score_

def plot_grid_search(grid_scores, best_params, best_score):
    print(1)
    keylist = [key for key in best_params]
    print(2)
    for key in keylist:
        X = [] #values of the key
        Y = [] #mean when run on values of the key
        for i in grid_scores:
            flag = False
            for k in i[0]:
                if k != key and i[0][k] != best_params[k]:
                    flag = True
                    break
            if flag == False:
                X.append(i[0][key])
                Y.append(i[1])
        print(3)
        pylab.figure(1)
        x = range(len(X))
        print(4)
        pylab.xticks(x, X)
        print(5)
        pylab.plot(x, Y)
        print(6)
        pylab.xlabel('Values of ' + str(key))
        print(7)
        pylab.ylabel('Mean Accuracy')
        pylab.show()
        print(8)

#Given NaN values, we can take two approaches - remove all cases of NaN, or use averages instead
def polish_data(X, Y, replace=False, average=False):
    nan_count, nan_ind = 0, []
    for i, sample in enumerate(X):
        for j in sample:
            if math.isnan(j):
                nan_count += 1
                nan_ind.append(i)
                break
    if replace==True:
        X = np.delete(X, nan_ind, 0)
        Y = np.delete(Y, nan_ind, 0)
    else:
        nan_index_set = set(nan_ind)
        av = np.array([0. for i in range(len(X[0]))])
        for i, sample in enumerate(X):
            if i not in nan_index_set:
                av += sample
            av /= (len(X)-len(nan_index_set))
            for i in nan_ind:
                for j, feature in enumerate(X[i]):
                    if math.isnan(feature):
                        X[i][j] = av[j]
    return X,Y

#Tells what percentage of our data is from each tier
def get_data_rank_percentages():
    X_train, Y_train, X_test, Y_test = generate_data(scale=False, average=True)
    X = np.vstack([X_train, X_test])
    ranks = [500*i for i in range(7)]
    rank_names = ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER", "CHALLENGER"]
    rank_percentages = [0 for i in range(7)]
    for i in X:
        av = sum([i[k*14+13] for k in range(5)])/5
        for ind, j in enumerate(ranks):
            if av < j:
                rank_percentages[ind-1] += 1
                break
            elif ind == len(ranks)-1:
                print(i[13])
    rank_percentages = [i/len(X) for i in rank_percentages]
    for rank, perc in zip(rank_names, rank_percentages):
        print("Percentage of Data that is " + rank + ": ", perc)
    patches, _ = plt.pie(rank_percentages)
    plt.axis('equal')
    for i, rank in enumerate(rank_names):
        rank_names[i] = rank + " (" + str(int(rank_percentages[i]*10000)/100) + "%)"
    plt.legend(patches, rank_names, loc='lower left')
    plt.savefig('models/data_rank_pie_graph.png')
    plt.show()

def generate_data(scale=True, replace=False, average=False, percent_train=0.7, lim=-1, touse=[]):
    df = pd.read_csv('data/data.csv')
    data = df.values[:,1:]
    np.random.shuffle(data)
    if lim == -1:
        if len(touse) > 0:
            X = data[:,touse]
        else:
            X = data[:,0:data.shape[1]-1]
        Y = data[:,data.shape[1]-1]
    else:
        if len(touse) > 0:
            X = data[:lim,touse]
        else:
            X = data[:lim,0:data.shape[1]-1]
        Y = data[:lim,data.shape[1]-1]
    X,Y = polish_data(X, Y, replace=replace, average=average)
    split_index = int(percent_train * len(X))
        
    X_train = X[0:split_index]
    Y_train = Y[0:split_index]
    X_test = X[split_index:]
    Y_test = Y[split_index:]

    #Transform features
    if scale==True:
        xScaler = StandardScaler()
        xScaler.fit(X_train)
        X_train = xScaler.transform(X_train)
        X_test = xScaler.transform(X_test)
    
    return X_train, Y_train, X_test, Y_test


def plot_nsample_variation(model_name):
    df = pd.read_csv('data/data.csv')
    data = df.values[:,1:]
    model = [joblib.load('models/'+i+'.pkl') for i in model_name]

    graphX, graphY = [i for i in np.linspace(100, len(data), 25)], [[] for i in model_name]
    
    for ind, mod in enumerate(model):
        print("Starting generation of plot for ", model_name[ind], "based on nsamples")
        for i in np.linspace(100, len(data), 25):
            tmp = 0.
            for j in range(20):
                lim = int(i)
                X_train, Y_train, X_test, Y_test = generate_data(replace=True, lim=lim)
                mod.fit(X_train, Y_train)
                tmp += mod.score(X_test, Y_test)
            graphY[ind].append(tmp/20.)
    print("Plotting")
    for i, j in zip(model_name, graphY):
        plt.plot(graphX, j, label=i)
    plt.xlabel('Number of Samples')
    plt.ylabel('Validation Error')
    plt.title('Model accuracy over number of samples')
    plt.legend(loc='lower right')
    plt.savefig('models/model_sample_graph_delete_nan.png')
#plt.show()

def model_score(models):
    train_accuracy, val_accuracy, sensitivity, specificity = [0. for i in models], [0. for i in models], [0. for i in models], [0. for i in models]
    trials = 20
    for i in range(trials):
        X_train, Y_train, X_test, Y_test = generate_data(average=True)
        sensitivity_index, specificity_index = [], []
        for j, sample in enumerate(Y_test):
            if sample == 1: sensitivity_index.append(j)
            else: specificity_index.append(j)
        for ind, mod in enumerate(models):
            cur_mod = joblib.load('models/'+mod+'.pkl')
            cur_mod.fit(X_train,Y_train)
            train_accuracy[ind] += cur_mod.score(X_train, Y_train)/trials
            val_accuracy[ind] += cur_mod.score(X_test, Y_test)/trials
            sensitivity[ind] += cur_mod.score(X_test[sensitivity_index], Y_test[sensitivity_index])/trials
            specificity[ind] += cur_mod.score(X_test[specificity_index], Y_test[specificity_index])/trials
    for ind, mod in enumerate(models):
        print(mod, "Training Accuracy:", train_accuracy[ind])
        print(mod, "Validation Accuracy:", val_accuracy[ind])
        print(mod, "Sensitivity:", sensitivity[ind])
        print(mod, "Specificity:", specificity[ind])

def feature_scoring():
    gbc, rfc = joblib.load('models/gbc.pkl'), joblib.load('models/rfc.pkl')
    #Testing importance of roles
    roles = ["TOP", "JUNGLE", "MIDDLE", "ADC", "SUPPORT"]
    xGraph = np.array([[i for j in range(10)] for i in range(7)]).flatten()
    y_rfc, y_gbc = [], []
    for i, role in enumerate(roles):
        print("Generating feature score for ", role)
        touse = [i*14+j for j in range(14)]
        for j in range(10):
            X_train, Y_train, X_test, Y_test = generate_data(average=True, touse=touse)
            gbc.fit(X_train, Y_train)
            rfc.fit(X_train, Y_train)
            y_rfc.append(rfc.score(X_test, Y_test))
            y_gbc.append(gbc.score(X_test, Y_test))

    #Testing importance of player features
    print("Generating feature score for player only")
    player_features = [5, 6, 7, 8, 9, 10, 11, 12, 13]
    touse = np.array([[i*14+j for j in player_features] for i in range(5)]).flatten()
    for j in range(10):
        X_train, Y_train, X_test, Y_test = generate_data(average=True, touse=touse)
        gbc.fit(X_train, Y_train)
        rfc.fit(X_train, Y_train)
        y_rfc.append(rfc.score(X_test, Y_test))
        y_gbc.append(gbc.score(X_test, Y_test))

    print("Generating feature score for champion only")
    champion_features = [0, 1, 2, 3, 4]
    touse = np.array([[i*14+j for j in champion_features] for i in range(5)]).flatten()
    gbc_score, rfc_score = 0, 0
    for j in range(10):
        X_train, Y_train, X_test, Y_test = generate_data(average=True, touse=touse)
        gbc.fit(X_train, Y_train)
        rfc.fit(X_train, Y_train)
        y_rfc.append(rfc.score(X_test, Y_test))
        y_gbc.append(gbc.score(X_test, Y_test))

    plt.scatter(xGraph, y_rfc, label='rfc', color='r')
    plt.scatter(xGraph, y_gbc, label='gbc', color='g')
    plt.legend(loc='lower right')
    plt.xticks([i for i in range(7)], ["TOP", "JUNGLE", "MIDDLE", "ADC", "SUPPORT", "PLAYER", "CHAMPION"])
    plt.ylabel("Validation Accuracy")
    plt.xlabel("Feature Subset")
    plt.title("Model Accuracy Trained on Specific Subsets of Features")
    plt.savefig('models/feature_score.png')
    plt.show()

def grid_search_init(model_name):
    print("Starting grid search for", model_name)
    X_train, Y_train, X_test, Y_test = generate_data(average=True)

    if model_name == "GBC":
        model, params = models.GBC_model()
    if model_name == "MLPC":
        model, params = models.MLPC_model()
    if model_name == "RFC":
        model, params = models.RFC_model()
    if model_name == "SVC":
        model, params = models.SVC_model()
    if model_name == "LRC":
        model, params = models.LR_model()

        
    print("Training data: ", len(X_train))

    #Feature Scoring
    '''rfc = joblib.load('models/rfc.pkl')
    player_features = [5, 6, 7, 8, 9, 10, 11, 12, 13]
    champion_features = [0, 1, 2, 3, 4]

    X_train = [transform_features(i) for i in X_train]
    X_test = [transform_features(i) for i in X_test]
    xScaler = StandardScaler()
    xScaler.fit(X_train)
    X_train = xScaler.transform(X_train)
    X_test = xScaler.transform(X_test)
    rfc.fit(X_train, Y_train)
    print(rfc.score(X_test, Y_test))
    quit()
    '''

    #PCA Visualization
    '''
    u,s,v = np.linalg.svd(X_train)
    '''

    scores, best_params, best_score = grid_search(model ,params, X_train, Y_train)
    #print("Plotting")
    #plot_grid_search(scores, best_params, best_score)
    print(best_params)
    print(best_score)
    model.set_params(**best_params)
    model.fit(X_train,Y_train)

    y_pred = [i for i in model.predict(X_test)]
    val_accuracy = sum([1 if i == j else 0 for i, j in zip(y_pred, Y_test)])/len(y_pred)
    print("Validation Accuracy:", val_accuracy)
    return model

models_ = ['rfc', 'gbc', 'mlpc', 'lrc', 'svc']
'''
gbc = grid_search_init("GBC")
joblib.dump(gbc, 'models/gbc.pkl')
mlpc = grid_search_init("MLPC")
joblib.dump(mlpc, 'models/mlpc.pkl')
svc = grid_search_init("SVC")
joblib.dump(svc, 'models/svc.pkl')

rfc = grid_search_init("RFC")
joblib.dump(rfc, 'models/rfc.pkl')
lrc = grid_search_init("LRC")
joblib.dump(lrc, 'models/lrc.pkl')
'''
#model_score(models_)
#plot_nsample_variation(models_)
#feature_scoring()
get_data_rank_percentages()
