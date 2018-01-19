from sklearn.ensemble import GradientBoostingClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
import numpy as np

def GBC_model():
    params = {'n_estimators':range(10, 300, 50), 'learning_rate':np.linspace(0.001, 0.1, 5),
        'max_depth':range(1, 30, 4), 'min_samples_leaf':range(1, 30, 4)}
    model = GradientBoostingClassifier(min_samples_split=15,max_features='sqrt',
                                       subsample=0.8,random_state=189)
    return model, params

def MLPC_model():
    model = MLPClassifier(random_state=189, max_iter=1000)
    params = {'hidden_layer_sizes':[(100), (100, 100), (50, 100), (100, 50), (100, 100, 100),
                                    (50, 100, 50), (100, 50, 100), (100, 100, 50), (50, 50, 100),
                                    (100, 100, 100, 100), (100, 50, 100, 50), (50, 100, 50, 100),
                                    (100, 100, 100, 100, 100), (100, 50, 100, 50, 100),
                                    (50, 100, 50, 100, 50), (100, 100, 50, 100, 100),
                                    (100, 100, 100, 100, 100, 100), (100, 100, 100, 100, 100, 100, 100),
                                    (80, 70, 60, 50, 40, 30, 20, 10), (200, 150, 100, 50, 20),
                                    (120, 90, 75, 63, 55, 50)],
              'activation':['relu', 'tanh'], 'alpha':np.linspace(0.000001, 0.001, 10)}
    return model, params

def RFC_model():
    params = {'criterion':['gini', 'entropy'], 'n_estimators':range(10,311,100),
              'max_features':['sqrt','log2',0.2,0.4,0.6,0.8], 'max_depth':range(3,25,10),
              'min_samples_split':range(5,30,10), 'min_samples_leaf':range(5,30,10)}
    model = RandomForestClassifier(random_state=189)
    return model, params

def SVC_model():
    params = {'C':np.linspace(0.01,5,25), 'kernel':['linear','poly','rbf','sigmoid']}
    model = SVC(max_iter=5000,random_state=189)
    return model, params

def LR_model():
    params = {'C':np.linspace(0.01,5,10),
            'solver':['newton-cg','lbfgs','liblinear','sag','saga']}
    model = LogisticRegression(max_iter=1000, random_state=189)
    return model, params

