from spacy.lang.id.stop_words import STOP_WORDS
import spacy
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
import re
import warnings
import string
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import stopwords
import flask
import time
import networkx as nx
import community
import io
import codecs
import json
import os
from datetime import datetime
import certifi
import numpy as np
import nltk
import itertools
import pandas as pd
import matplotlib.pyplot as plt
from nltk import bigrams
from nltk.tokenize import word_tokenize
from random import seed
nltk.download('punkt')
warnings.filterwarnings("ignore")

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_STATIC = os.path.join(APP_ROOT, 'static')


class QuerySNA:
    def __init__(self):
        self.G = nx.Graph()
        self.df = pd.read_csv(APP_STATIC+'/twitter perumahan 7-8 juni.csv')
        self.alay = pd.read_csv(APP_STATIC+'/alay.csv')
        self.gdata = []
        self.lemma = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('indonesian'))
        self.nlp = spacy.blank('id')
        self.stop_word_medis = ['bu', 'ya', 'yang', 'mas', 'mbak',
                                'dok', 'dokter', 'iya', 'nya', 'ya',
                                'kalo', 'mohon', 'rt']

    def clean_text(self, text):
        text = text.lower()
        text = re.sub('[^ a-zA-Z0-9]', '', text)
        text = re.sub(r"http\S+", "", text)
        text = nltk.word_tokenize(text)
        text = [self.alay.get(a,a) for a in text]
        text = [w for w in text if not w in self.stop_words]
        text = [w for w in text if not w in STOP_WORDS]
        text = [w for w in text if not w in self.stop_word_medis]
        text = " ".join(self.nlp(word)[0].lemma_ for word in text)
        return text

    def generate_co_occurrence_matrix(self, corpus):
        vocab = set(corpus)
        vocab = list(vocab)
        vocab_index = {word: i for i, word in enumerate(vocab)}
        bi_grams = list(bigrams(corpus))
        bigram_freq = nltk.FreqDist(bi_grams).most_common(len(bi_grams))
        co_occurrence_matrix = np.zeros((len(vocab), len(vocab)))
        for bigram in bigram_freq:
            current = bigram[0][1]
            previous = bigram[0][0]
            count = bigram[1]
            pos_current = vocab_index[current]
            pos_previous = vocab_index[previous]
            co_occurrence_matrix[pos_current][pos_previous] = count
        co_occurrence_matrix = np.matrix(co_occurrence_matrix)
        return co_occurrence_matrix, vocab_index

    def graphanalytic(self):
        # graph analytic
        start_time = time.time()
        self.G = nx.from_pandas_adjacency(self.gdata)
        self.graphcentrality()  # calculate centrality
        self.graphattributes()  # set graph attributes
        elapse_time = time.time() - start_time
        print('graph analytic time: ', elapse_time)
        return self.graphtojson()

    def graphcentrality(self):
        self.degree = nx.degree_centrality(self.G)
        self.betweenness = nx.betweenness_centrality(self.G)  # most expensive
        self.closeness = nx.closeness_centrality(self.G)  # 2nd most expensive
        self.communities = community.best_partition(self.G)

    # #set graph attributes from centrality calculation
    def graphattributes(self):
        nx.set_node_attributes(self.G, self.degree, 'degree')
        nx.set_node_attributes(self.G, self.betweenness, 'betweenness')
        nx.set_node_attributes(self.G, self.closeness, 'closeness')
        nx.set_node_attributes(self.G, self.communities, 'modularity')

    def getSizeVal(self, data):
        min_r = 4
        max_r = 15
        delta_R = max_r - min_r
        data['nodes'] = sorted(data['nodes'], key=lambda x: x['degree'])
        min_s = data['nodes'][0]['degree']
        max_s = data['nodes'][-1]['degree']
        delta_S = max_s - min_s
        print(delta_S)
        for i in data['nodes']:
            size = i['degree']
            # r = (delta_R*(size-min_s)/delta_S)+min_r
            r = (size*delta_R/delta_S)+min_r
            i.update({'radius': r})
            print(r)
        return data

    def graphtojson(self):
        data = nx.readwrite.json_graph.node_link_data(
            self.G, {'link': 'links', 'source': 'source', 'target': 'target'})
        data = self.getSizeVal(data)
        jdata = flask.json.dumps(data, ensure_ascii=False, indent=4)
        nx.write_gml(self.G, "testg.gml")  # save to file
        with io.open(os.path.join(APP_STATIC, 'text_network.json'), 'w', encoding='utf-8') as f:
            # f.write(flask.json.dumps(data, ensure_ascii=False))
            f.write(jdata)

        return jdata

    def drawplot(self, index):
        if index == 0:
            nx.draw_networkx(self.G, with_labels=False)
        elif index == 1:
            nx.draw_shell(self.G)
        elif index == 2:
            nx.draw_kamada_kawai(self.G, node_size=5, linewidths=0.5)
        elif index == 3:
            nx.draw_random(self.G)

    def getgraph(self):
        return self.G

    def generate_network(self):
        df = self.df
        df['message'] = df['message'].fillna('').apply(str)
        sentences_raw = [a for a in df.message.values]
        sentences = [self.clean_text(a) for a in sentences_raw]
        df['cleaned'] = sentences
        text = df['cleaned'][:50]
        text_data = [word_tokenize(i) for i in text]
        data = list(itertools.chain.from_iterable(text_data))
        matrix, vocab_index = self.generate_co_occurrence_matrix(data)
        data_matrix = pd.DataFrame(matrix, index=vocab_index,
                                   columns=vocab_index)
        self.gdata = data_matrix
        return self.graphanalytic()


qsna = QuerySNA()
data = qsna.generate_network()
