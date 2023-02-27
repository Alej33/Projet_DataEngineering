from flask import Flask, render_template
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import pandas as pd
import os


#Importation des données traitées
df = pd.read_csv("tweets_ratp.csv", encoding='utf-8')
df['raison_keyword'] = df['raison_keyword'].fillna('')

app = Flask(__name__)

def connect_elasticsearch():
    LOCAL = False

    es = Elasticsearch(hosts=["localhost" if LOCAL else "http://localhost:9200"])
    if es.ping():
        print('Connecter à Elasticsearch')
    else:
        print('Connexion à Elasticsearch échoué')
    return es


index_name = "ratp_tweets"
mapping = {
    "mappings": {
        "properties": {
            "account": {"type": "keyword"},
            "tweet": {"type": "text"},
            "reasons": {"type": "keyword"},
            "reasons_keyword": {"type": "keyword"},
            "timestamp": {"type": "date"}
        }
    }
}

#Indexations des données dans Elasticsearch
def index_data(es, index_name, data):
    if es.indices.exists(index_name):
        es.indices.delete(index=index_name)
        
    es.indices.create(index=index_name, body=mapping)
    documents = []
    for index, row in data.iterrows():
        document = {
            "_index": index_name,
            "_source": {
                "account": row["Lignes"],
                "tweet": row["tweets"],
                "reasons": row["raison"],
                "reasons_keyword": row["raison_keyword"],
                "timestamp": pd.to_datetime(row["date"] + " " + row["heure"], format="%d-%m-%Y %H:%M:%S")
            }
        }
        documents.append(document)

    bulk(es, documents)

#Importation des Kibana Objects (Index pattern et Dashboard)
def import_index_dashboard():
    os.system('cmd /c "curl -X POST "localhost:5601/api/saved_objects/_import" -H "kbn-xsrf: true" --form file=@export_index_pattern.ndjson"')
    os.system('cmd /c "curl -X POST "localhost:5601/api/saved_objects/_import" -H "kbn-xsrf: true" --form file=@export_dashboard.ndjson"')

@app.route('/templates')
def dashboard():
    es = connect_elasticsearch()
    index_data(es, index_name, df)
    import_index_dashboard()

    return render_template('dashboard.html')
