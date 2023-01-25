from flask import *
from pymongo import *
import sys

app = Flask(__name__)

myclient = MongoClient("mongodb://mongodb:27017/")
mydb = myclient["prometheusdata"]



@app.route('/', methods = ['GET','POST'])
def home():
    if(request.method == 'GET'):
        return jsonify({'Status': 'Up'})


@app.route('/metricsList/', methods = ['GET'])
def metricList():
    if(request.method == 'GET'):
        return jsonify({'MetricList': mydb.list_collection_names()})

@app.route('/<string:metricName>/<string:dataType>', methods = ['GET'])
def getMetric(metricName,dataType):
    if(request.method == 'GET'):
        pointer = mydb[metricName].find_one({'typeDocument': 'pointer'})
        if pointer == None:
            return jsonify ({'error': 'Metric not found'} )
        lastDocument = mydb[metricName].find_one({'_id': pointer['lastDocument']})
        if lastDocument == None:
            return jsonify ({'error': 'Update document not found'} )
        return jsonify({'MetricName':metricName,'TimeStamp':lastDocument['time_stamp'], 'dataType' : dataType, 'data' : lastDocument[dataType]})


if __name__ == '__main__':
  
    app.run(port=5001,host='0.0.0.0')
