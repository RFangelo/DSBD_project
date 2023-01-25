import json
import sys
from lib import *
from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from confluent_kafka import Producer
from prometheus_api_client.utils import parse_datetime
from datetime import timedelta
from time import time, sleep
from datetime import datetime
from requests.exceptions import ConnectTimeout
import yaml

def delivery_callback(err, msg):
    if err:
        
        sys.stderr.write('%% Message failed delivery: %s\n' % err)
    else:
        sys.stderr.write('%% Message delivered to %s [%d] @ %d\n' %
                         (msg.topic(), msg.partition(), msg.offset()))


urlPrometheus = "http://15.160.61.227:29090"

if len(sys.argv) != 3:
    sys.stderr.write(
        'Invalid arguments, required <bootstrap-brokers> <topic>\n')
    sys.exit(1)

broker = sys.argv[1]
topic = sys.argv[2]

conf = {'bootstrap.servers': broker}
p = Producer(**conf)

time_stamp = time()
date_time = datetime.fromtimestamp(time_stamp)
str_date_time = date_time.strftime("%d-%m-%Y, %H:%M:%S")

sys.stderr.write('ETL container started at ' + str_date_time + '\n')
     

metrics = []

with open('metrics.yaml') as f:
    docs = yaml.load_all(f, Loader=yaml.FullLoader)
    for doc in docs:
        for doc_metric in doc['metrics']:
            metrics.append(
                {'metricName': doc_metric['metricName'], 'labels': doc_metric['labels']})
                
prom = PrometheusConnect(
                url=urlPrometheus, disable_ssl=True)

while True:

    time_stamp = time()

    for metric in metrics:

        initTime = time()
        query_time_stamp = initTime
        try:
            
            start_time = parse_datetime("2d")
            end_time = parse_datetime("now")
            chunk_size = timedelta(minutes=1)
            label_config = metric['labels']
            metric_data = prom.get_metric_range_data(
                metric_name=metric['metricName'],
                label_config=label_config,
                start_time=start_time,
                end_time=end_time,
                chunk_size=chunk_size,)
        except ConnectTimeout:

            date_time = datetime.fromtimestamp(initTime)
            str_date_time = date_time.strftime("%d-%m-%Y, %H:%M:%S")
            sys.stderr.write('ConnectTimeout at : ' + str_date_time +
                      '  retry to connect with prometheus server at : '+urlPrometheus)
            continue

        queryTime = time() - initTime
        df = MetricRangeDataFrame(metric_data)
        initTime = time()
        stationarity = get_stationarity(df)
        acf_ = get_acf(df)
        season = get_seasonality(df)
        metaTime = time() - initTime

        initTime = time()
        parameters1h = computeParameterForTimeFrame(df, TimeFrame.H1)
        computeTime1h = time() - initTime

        initTime = time()
        parameters3h = computeParameterForTimeFrame(df, TimeFrame.H3)
        computeTime3h = time() - initTime

        initTime = time()
        parameters12h = computeParameterForTimeFrame(df, TimeFrame.H12)
        computeTime12h = time() - initTime

        initTime = time()
        prediction_ = predict(df,season['Period'])
        predictionTime = time() - initTime
        date_time = datetime.fromtimestamp(query_time_stamp)
        str_date_time = date_time.strftime("%d-%m-%Y, %H:%M:%S")

        logData = {'time_stamp': str_date_time, 'query': metric['metricName'], 'stats': {'queryTime': queryTime, 'metaTime': metaTime, 'computationTime1h': computeTime1h,
                        'computationTime3h': computeTime3h, 'computationTime12h': computeTime12h, 'predictionTime': predictionTime}}
        sys.stderr.write(str(logData)+'\n')
        
        df_12 = df.iloc[-720:].get('value')
        samples_list = list()
        for sample in df_12:
            samples_list.append(sample)

        p.produce(topic, json.dumps({'time_stamp': str_date_time, 'query': metric['metricName'], 'metadata': {'stationarity': stationarity, 'Seasonality': season['Seasonality'],
                  'acf': acf_}, 'parameters_1h': parameters1h, 'parameters_3h': parameters3h, 'parameters_12h': parameters12h,'prediction':prediction_, 'sampleValues_12h': samples_list }), callback=delivery_callback)
        p.poll(0)
        
    p.flush()#prima di mandare in sleep aspetto in modo bloccante che tutte i messaggi di ricezione sono stati ricevuti e a quel putno chiamo le callbacks
    
    sleepTime = timedelta(hours=1).seconds - (time() - time_stamp)
    if sleepTime > 0:
        sleep(sleepTime)


