from confluent_kafka import Consumer
import sys
from pymongo import *
import json

myclient = MongoClient("mongodb://mongodb:27017/")
mydb = myclient["prometheusdata"]
mycol = mydb["metricsdata"]

c = Consumer({
    'bootstrap.servers': sys.argv[1],
    'group.id': 'mygroup',
    'auto.offset.reset': 'earliest'
})

c.subscribe([sys.argv[2]])

while True:
    msg = c.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        sys.stderr.write("error: {}".format(msg.error()))
        continue

    dict_p = json.loads(msg.value().decode('utf-8','strict'))
    if not dict_p['query'] in mydb.list_collection_names():
        collection_parameters = { "capped" : True, "max" : 20, "size" : 900000 }
        mydb.create_collection(dict_p['query'],**collection_parameters)
    mycol = mydb[dict_p['query']]
    id = mycol.insert_one(dict_p)
    lastpointer = mycol.find_one({'typeDocument':'pointer'})
    if lastpointer == None:
        mycol.insert_one({'typeDocument':'pointer','lastDocument':id.inserted_id,'time_stamp':dict_p['time_stamp']})
    else:
        mycol.replace_one({'typeDocument':'pointer'},{'typeDocument':'pointer','lastDocument':id.inserted_id,'time_stamp':dict_p['time_stamp']})


c.close()

