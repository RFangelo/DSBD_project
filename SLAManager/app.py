from flask import *
from pymongo import *
import sys
import yaml
from prometheus_api_client import PrometheusConnect, MetricSnapshotDataFrame
from requests.exceptions import ConnectTimeout
from datetime import datetime
from time import time

app = Flask(__name__)

urlPrometheus = "http://15.160.61.227:29090"
myclient = MongoClient("mongodb://mongodb:27017/")
mydb = myclient["SLA"]
myColl = mydb['SLAMetrics']


metrics = []

with open('metrics.yaml') as f:
    docs = yaml.load_all(f, Loader=yaml.FullLoader)
    for doc in docs:
        for doc_metric in doc['metrics']:
            metrics.append(
                {'metricName': doc_metric['metricName'], 'labels': doc_metric['labels']})

SLA_set = list()

for row in myColl.find():
    SLA_set.append({'metricName' : row['metricName'], 'constraint' : row['constraint'] , 'value': row['value']})


@app.route('/createUpdateSla/<string:metricName>/<string:constraint>/<string:value>', methods = ['GET'])
def createUpdateSLA(metricName,constraint,value):
    db = myclient['prometheusdata']
    if(request.method == 'GET'):
        if metricName == None or constraint == None or value == None:
            return jsonify ({'error' : 'Field empty or not found'})
        if  constraint != 'Max' and constraint != 'Min':
            return jsonify ({'error' : 'Permitted values for constraint field are only Max or Min'})
        if not metricName in db.list_collection_names():
            return jsonify({'error': 'Metric not found'})
        try:
            value = float(value)
        except ValueError:
            return jsonify ({'error' : 'value is not a number'})
        
        for SLA in SLA_set:
            if SLA['metricName'] == metricName:
                SLA_set.remove(SLA)
                SLA_set.append({'metricName' : metricName, 'constraint' : constraint , 'value': value})
                myColl.replace_one({'metricName':metricName},{'metricName' : metricName, 'constraint' : constraint , 'value': value})   
                break
        else:
            if SLA_set.__len__() == 5:
                return jsonify({'error' : 'SLA set is full'})
            SLA_set.append({'metricName' : metricName, 'constraint' : constraint , 'value': value})
            myColl.insert_one({'metricName' : metricName, 'constraint' : constraint , 'value': value}) 
        

        return jsonify({'metricName' : metricName, 'constraint' : constraint , 'value': value, 'QueryResult' :'Successeful'})





@app.route('/listSla', methods = ['GET'])
def listSLA():
    return jsonify({'SLA':SLA_set})


@app.route('/removeSla/<string:metricName>', methods = ['GET'])
def removeSLO(metricName):
    for SLA in SLA_set:
        if SLA['metricName'] == metricName:
            SLA_set.remove(SLA)
            myColl.delete_one({'metricName':metricName})
            break
        else:
            return jsonify({'error':'SLA in SLA_set not found'})
    return jsonify({'SLA':SLA_set})








@app.route('/checkStateSla', methods = ['GET'])
def checkStateSLA():
    checkStates = list()
    if SLA_set.__len__() == 0:
        return jsonify({'error':'SLA set is empty'})
    for SLA in SLA_set:
        stateSLA = checkStateSLO(SLA['metricName'])
        stateSLA = dict(stateSLA)
        if stateSLA.__contains__('warning'):
            checkStates.append({'SLO': SLA, 'VIOLATED':stateSLA['VIOLATED'],'warning':stateSLA['warning']})
        else:
            checkStates.append({'SLO': SLA, 'VIOLATED':stateSLA['VIOLATED']})
    for state in checkStates:
        if state['VIOLATED'] == True:
            return jsonify({'SLA_VIOLATED': True, 'CheckList':checkStates})
    return jsonify({'SLA_VIOLATED': False, 'CheckList':checkStates})









def checkStateSLO(metricName):
    initTime = time()
    for element in SLA_set:
        if element['metricName'] == metricName:
            SLA = element
    connectionFail = False

    try:
        prom = PrometheusConnect(
            url=urlPrometheus, disable_ssl=True)
        
        for metric in metrics:
            if metric['metricName'] == metricName:
                label_config = metric['labels']
                break
        else:
            return {'error': 'Metric not found'}
        metric_data = MetricSnapshotDataFrame(prom.get_current_metric_value(
            metric_name=metricName,
            label_config=label_config,))
    except ConnectTimeout:
        date_time = datetime.fromtimestamp(initTime)
        str_date_time = date_time.strftime("%d-%m-%Y, %H:%M:%S")
        connectionFail = True
        
    if SLA['constraint'] == 'Max':
        if not connectionFail:
            if metric_data["value"][0] < SLA['value']:
                return {'VIOLATED':False}
            else:
                return {'VIOLATED':True}
        else:
            db = myclient['prometheusdata']
            coll = db[metricName]
            pointer = coll.find_one({'typeDocument': 'pointer'})
            if pointer == None:
                return {'error': 'Metric not found'}
            lastDocument = coll.find_one({'_id': pointer['lastDocument']})
            if lastDocument == None:
                return {'error': 'Update document not found'}
            if lastDocument['parameters_1h']['parameters']['max'] < SLA['value']:
                return {'VIOLATED':False,'warning':'This evaluation was carried out considering the max compared to the hour preceding the time'+ str_date_time +'  because the connection to prometheus failed'}
            else:
                return {'VIOLATED':True,'warning':'This evaluation was carried out considering the max compared to the hour preceding the time'+ str_date_time +'  because the connection to prometheus failed'}
    else:
        if not connectionFail:
            if metric_data["value"][0] > SLA['value']:
                return {'VIOLATED':False}
            else:
                return {'VIOLATED':True}
        else:
            db = myclient['prometheusdata']
            coll = db[metricName]
            pointer = coll.find_one({'typeDocument': 'pointer'})
            if pointer == None:
                return {'error': 'Metric not found'}
            lastDocument = coll.find_one({'_id': pointer['lastDocument']})
            if lastDocument == None:
                return {'error': 'Update document not found'}
            if lastDocument['parameters_1h']['parameters']['min'] > SLA['value']:
                return {'VIOLATED':False,'warning':'This evaluation was carried out considering the max compared to the hour preceding the time'+ str_date_time +'  because the cannection to prometheus failed'}
            else:
                return {'VIOLATED':True,'warning':'This evaluation was carried out considering the max compared to the hour preceding the time'+ str_date_time +'  because the cannection to prometheus failed'}
    


@app.route('/checkStateSlaHistory/<int:hours>', methods = ['GET'])
def checkStateSLAhistory(hours):
    checkStates = list()
    db = myclient['prometheusdata']
    if SLA_set.__len__() == 0:
        return jsonify({'error':'SLA set is empty'})
    if hours!= 1 and hours != 3 and hours != 12:
        return jsonify ({'error' : 'Permitted values for hours field are only 1,3,12'})
    for SLA in SLA_set:
        coll = db[SLA['metricName']]
        pointer = coll.find_one({'typeDocument': 'pointer'})
        if pointer == None:
            return jsonify ({'error': 'Metric'+ SLA['metricName'] +' not found'})
        lastDocument = coll.find_one({'_id': pointer['lastDocument']})
        if lastDocument == None:
            return jsonify ({'error': 'Update document in '+SLA['metricName']+' not found'} )
        samples = lastDocument['sampleValues_12h']
        samples = samples[720-60*hours:]
        num_violation = 0
        if SLA['constraint'] == 'Max':
            for sample in samples:
                if sample > SLA['value']:
                    num_violation += 1
        else:
            for sample in samples:
                if sample < SLA['value']:
                    num_violation += 1
        checkStates.append({'metricName':SLA['metricName'], 'numViolation':num_violation})
    return jsonify({'history':checkStates,"time_frame_hours":hours})
        



@app.route('/checkFutureSla', methods = ['GET'])
def checkFutureSLA():
    checkStates = list()
    db = myclient['prometheusdata']
    if SLA_set.__len__() == 0:
        return jsonify({'error':'SLA set is empty'})
    for SLA in SLA_set:
        coll = db[SLA['metricName']]
        pointer = coll.find_one({'typeDocument': 'pointer'})
        if pointer == None:
            return jsonify ({'error': 'Metric'+ SLA['metricName'] +' not found'} )
        lastDocument = coll.find_one({'_id': pointer['lastDocument']})
        if lastDocument == None:
            return jsonify ({'error': 'Update document in '+SLA['metricName']+' not found'} )
        
        if SLA['constraint'] == 'Max':
            if lastDocument['prediction']['max'] >SLA['value']:
                checkStates.append({'metricName': SLA['metricName'], 'POSSIBLE_VIOLATION_OF_PREDICTION':True})
            else:
                checkStates.append({'metricName': SLA['metricName'], 'POSSIBLE_VIOLATION_OF_PREDICTION':False})
        else:
            if lastDocument['prediction']['min'] < SLA['value']:
                checkStates.append({'metricName': SLA['metricName'], 'POSSIBLE_VIOLATION_OF_PREDICTION':True})
            else:
                checkStates.append({'metricName': SLA['metricName'], 'POSSIBLE_VIOLATION_OF_PREDICTION':False})
    return jsonify(checkStates)
        






if __name__ == '__main__':
  
    app.run(port=5002,host='0.0.0.0')
