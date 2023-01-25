from statsmodels.tsa.stattools import adfuller
from numpy import std
from statsmodels.tsa.stattools import acf
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.ar_model import AutoReg
import warnings
from sklearn.metrics import mean_squared_error
from enum import Enum
import numpy as np

class TimeFrame(Enum):
    H1 = 1
    H3 = 3
    H12 = 12

def get_stationarity(df):
    result = adfuller(df.get('value'),autolag='AIC')
    if result[1] <= 0.05:
        return True #stazionarietà, non c'è stagionalità
    else:
        return False #non stazionario, potrebbe esserci stagionalità


def get_seasonality(df):  
    periodo = df.shape[0]/2
    cinquePercPeriodo = periodo/20 
    for i in range (0,19): #provo i periodi 20 volte levando il 10% ogni iterazione e seleziono il periodo con la media dell'autocorrelazione sull' errore più basso (comportamento dimile rumore bianco)
        print(periodo)
        result = seasonal_decompose(df.get('value'), model='add', period= int(periodo))
        acf_errore = acf(result.resid.dropna())
        if i == 0:
            periodo_minimo = periodo
            media_acf_err_minimo = abs(acf_errore[1:].mean())
        elif abs(acf_errore[1:].mean())<media_acf_err_minimo:
            periodo_minimo = periodo
            media_acf_err_minimo = abs(acf_errore[1:].mean())
        periodo = periodo - cinquePercPeriodo
    result = seasonal_decompose(df.get('value'), model='add', period= int(periodo_minimo))#una volta trovato il periodo corretto decompongo la serie
    
    acf_season = acf(result.seasonal,nlags=df.shape[0])#analizzo l'autocorrelazione sulla componente stagionale, 
                                                        #in questo modo sono visibili i campioni correlati ogni periodo della componente stagionale
    if acf_season[1:].max()>0.4:                        # con una verifica utilizzando soglie minime di 0.4 per il primo impulso e 0.25 per il secondo
        idxmax = np.argmax(acf_season[1:])
        if acf_season[idxmax+1:].max() >0.25:
            idxmax2 = np.argmax(acf_season[idxmax+2:])
            if abs(idxmax2 - idxmax)<idxmax*0.05:
                return {'Seasonality' : True , 'Period' : int(periodo_minimo)}
    return {'Seasonality' : False , 'Period' : int(periodo_minimo)}

def get_acf(df):
    return acf(df.get('value')).tolist()

def get_max(df,timeFrame):
    rowNum = df.shape[0]
    if rowNum < timeFrame*60:
        return None
    newDf = df[int(rowNum-60*timeFrame):]
    return newDf.max().get('value')

def get_min(df,timeFrame):
    rowNum = df.shape[0]
    if rowNum < timeFrame*60:
        return None
    newDf = df[int(rowNum-60*timeFrame):]
    return newDf.min().get('value')

def get_avg(df,timeFrame):
    rowNum = df.shape[0]
    if rowNum < timeFrame*60:
        return None
    newDf = df[int(rowNum-60*timeFrame):]
    return newDf.get('value').mean()

def get_dev_std(df,timeFrame):
    rowNum = df.shape[0]
    if rowNum < timeFrame*60:
        return None
    newDf = df[int(rowNum-60*timeFrame):]
    return std(newDf.get('value'))
    
def computeParameterForTimeFrame(df,timeFrame):
    return {'timeFrame':timeFrame.value,'parameters':{
        'max' : get_max(df,timeFrame.value),
        'min' : get_min(df,timeFrame.value),
        'avg' : get_avg(df,timeFrame.value),
        'dev_std' : get_dev_std(df,timeFrame.value)
    }}

def predict(df,period):
    d = df.xs('value', axis=1)
    result = seasonal_decompose(d, model='add', period=period)
    data = result.trend.dropna()
    diecipercento = int(data.shape[0]/10)
    train_data = data.iloc[:-diecipercento]
    test_data = data.iloc[-diecipercento:]
    warnings.filterwarnings("ignore")

    predictions = list()

    for i in range (1,10):#calcolo dieci prediction su valori che ho già variando i lags
        model = AutoReg(train_data, lags = i)
        AR1fit = model.fit()
        start = len(train_data)
        end = start + len(test_data)-1
        predictions.append(AR1fit.predict(start=start, end=end))

    errors = list()
    for i in range(0,9):#calcolo gli errori relativi alla prediction e ai valori effettivi
        errors.append(mean_squared_error(test_data, predictions[i]))
        
    min = errors[0]
    minindex = 0
    for i in range(0,8):#trovo l'errore minimo, selezionando il lags associato
        if errors[i+1] < min:
            min = errors[i+1]
            minindex = i
        
    model = AutoReg(data, lags = minindex+1)
    ARfit = model.fit()

    fcast = ARfit.predict(start=len(data), end=len(data)+10, dynamic=False).rename('Forecast')#effettuo la prediction sui successivi dieci minuti

    return {'avg': fcast.mean(),'min': fcast.min(),'max': fcast.max()}