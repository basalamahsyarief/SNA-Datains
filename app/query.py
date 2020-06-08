import flask
import time
import networkx as nx
import community
import io
import codecs
import json
import os
from datetime import datetime
from elasticsearch import Elasticsearch
import certifi

# es = Elasticsearch(['http://10.17.5.104:9200'], timeout=100)


class configElasticseach(object):
    USER = 'semantic'
    PWD = 'Semantic123'
#     HOST = 'https://ali-es.semantic.id' #facebook
    HOST = 'https://es.semantic.id'  # twitter
    PORT = 80


es = Elasticsearch([configElasticseach.HOST], port=configElasticseach.PORT, http_auth=(configElasticseach.USER, configElasticseach.PWD), use_ssl=True, ca_certs=certifi.where(),timeout=100)
# es = Elasticsearch(['https://es.semantic.id/'], timeout=100)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_STATIC = os.path.join(APP_ROOT, 'static')


class QuerySNA:
    def __init__(self):
        self.G = nx.Graph()
        self.gdata = {'nodes': [], 'links': []}
        self.hashtags = []
        self.accounts = []
        self.gte = "now-30d/d"
        self.lte = "now/d"
        self.keyword = "(masyarakat AND berpenghasilan AND rendah) OR (perumahan AND subsidi) OR (perumahan AND rakyat)"
        self.fsize = 20
        self.landlordsize = 100
        self.laymansize = 50
        self.tweet_counts = 0

    def qparam(self, gte, lte, keyword, lands, lays, fsize):
        self.G = nx.Graph()
        # self.gdata = {'nodes': [], 'links': []}
        self.gte = gte
        self.lte = lte
        self.keyword = keyword
        self.landlordsize = lands
        self.laymansize = lays
        self.freesize = fsize

    def qretweet(self):
        query = {
            "size": 0,
            "_source": {
                "excludes": []
            },
            "aggs": {
                "2": {
                    "terms": {
                        "field": "retweeted_status.message.keyword",
                        "size": self.landlordsize,
                        "order": {
                            "_count": "desc"
                        }
                    },
                    "aggs": {
                        "3": {
                            "terms": {
                                "field": "retweeted_status.screen_name.keyword",
                                "size": 1,
                                "order": {
                                    "_count": "desc"
                                }
                            },
                            "aggs": {
                                "6": {
                                    "terms": {
                                        "field": "retweeted_status.profile_img.keyword",
                                        "size": 1,
                                        "order": {
                                            "_count": "desc"
                                        }
                                    },
                                    "aggs": {
                                        "5": {
                                            "terms": {
                                                "field": "user.screen_name.keyword",
                                                "size": self.laymansize,
                                                "order": {
                                                    "_count": "desc"
                                                }
                                            },
                                            "aggs": {
                                                "7": {
                                                    "terms": {
                                                        "field": "retweeted_status.tweet_id.keyword",
                                                        "size": 1,
                                                        "order": {
                                                            "_count": "desc"
                                                        }
                                                    },
                                                    "aggs": {
                                                        "8": {
                                                            "terms": {
                                                                "field": "created",
                                                                "size": 1,
                                                                "order": {
                                                                    "_term": "desc"
                                                                }
                                                            },
                                                            "aggs": {
                                                                "hashtag": {
                                                                    "terms": {
                                                                        "field": "hastags.keyword"
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "hashtag": {
                    "terms": {
                        "field": "hastags.keyword"
                    }
                }
            },
            "stored_fields": [
                "*"
            ],
            "script_fields": {},
            "docvalue_fields": [
                "created",
                "created_at_utc",
                "lastaccess"
            ],
            "query": {
                "bool": {
                    "must": [
                        {
                            "match_all": {}
                        },
                        {
                            "range": {
                                "created": {
                                    "gte": self.gte,
                                    "lte": self.lte
                                }
                            }
                        },
                        {
                            "query_string": {
                                "query": self.keyword,
                                "analyze_wildcard": True,
                                "default_field": "retweeted_status.message"
                            }
                        }
                    ],
                    "filter": [],
                    "should": [],
                    "must_not": []
                }
            }
        }

        res = es.search(index="twitter", doc_type="tweet", body=query)
        # print("elasticsearch time, got %d Hits in %d ms" % (res['hits']['total'], res['took']))
        # print(json.dumps(res))
        start_time = time.time()
        self.tweet_counts = res['aggregations']['2']['sum_other_doc_count']
        # print(json.dumps(res['aggregations']['2']))
        for hit in res['aggregations']['2']['buckets']:
            id = hit['3']['buckets'][0]['key']  # screen_name
            # filter if a node have exist
            isnode = list(filter(lambda person: person['id'] == id, self.gdata['nodes']))
            if isnode:  # mode exist, re-use the key
                id = isnode[0]['id']
            else:
                message = hit['key']
                value = hit['3']['buckets'][0]['doc_count']
                type = 'retweet'
                role = 'landlord'  # retweeted node
                img = hit['3']['buckets'][0]['6']['buckets'][0]['key']
                # tweet id
                tid = hit['3']['buckets'][0]['6']['buckets'][0]['5']['buckets'][0]['7']['buckets'][0]['key']
                link = "https://twitter.com/i/web/status/" + tid
                created = hit['3']['buckets'][0]['6']['buckets'][0]['5']['buckets'][0]['7']['buckets'][0]['8']['buckets'][0]['key_as_string']
                hashtag = hit['3']['buckets'][0]['6']['buckets'][0]['5']['buckets'][0]['7']['buckets'][0]['8']['buckets'][0]['hashtag']['buckets']
                created_key = hit['3']['buckets'][0]['6']['buckets'][0]['5']['buckets'][0]['7']['buckets'][0]['8']['buckets'][0]['key']
                if(len(hashtag) > 0):
                    nodex = {'id': id, 'label': id, 'hop': 1, 'message': message,
                             'hashtag': hashtag[0]['key'], 'size': value, 'type': type, 'role': role, 'img': img, 'link': link, 'created': created, 'ckey': created_key}
                else:
                    nodex = {'id': id, 'label': id, 'hop': 1, 'message': message, 'size': value, 'type': type,
                             'role': role, 'img': img, 'link': link, 'created': created, 'ckey': created_key}
                self.gdata['nodes'].append(nodex)
                self.accounts.append(nodex)

            for agg in hit['3']['buckets'][0]['6']['buckets'][0]['5']['buckets']:
                # if len(filter(lambda person: person['id'] == agg['key'], self.gdata['nodes'])) == 0:  # filter if a node have exist
                l = filter(lambda person: person['id'] == agg['key'], self.gdata['nodes'])
                if len(list(l)) == 0:
                    node = {'id': agg['key'], 'hop': 1, 'size': agg['doc_count'],
                            'type': 'retweet', 'role': 'layman'}
                    self.gdata['nodes'].append(node)
                eid = len(self.gdata['links'])
                edge = {'source': agg['key'], 'target': id, 'size': agg['doc_count'], 'id': eid}
                self.gdata['links'].append(edge)

            elapse_time = time.time() - start_time
            print("query aggregate time: ", elapse_time)
        self.accounts = sorted(self.accounts, key=lambda x: datetime.strptime(
            x['created'], "%Y/%m/%d %H:%M:%S"))
        self.getSizeVal()
        return self.getHashtags(res)

    def getHashtags(self, res):
        for hit in res['aggregations']['hashtag']['buckets']:
            hash = {'hashtag': hit['key'], 'count': hit['doc_count']}
            self.hashtags.append(hash)
        return json.dumps(self.hashtags)

    def getSizeVal(self):
        min_r = 4
        max_r = 15
        delta_R = max_r - min_r
        self.gdata['nodes'] = sorted(self.gdata['nodes'], key=lambda x: x['size'])
        min_s = self.gdata['nodes'][0]['size']
        max_s = self.gdata['nodes'][-1]['size']
        delta_S = max_s - min_s
        print(delta_S)
        for i in self.gdata['nodes']:
            size = i['size']
            # r = (delta_R*(size-min_s)/delta_S)+min_r
            r = (size*delta_R/delta_S)+min_r
            i.update({'radius': r})
            print(r)
        return r

    # def addRadius(self,Size):
    # 	if (item):
    # 		item.group = 4;
    # 	return var item = array.find(x => x.applicantID == 3)

    def simqretweet(self):
        # self.gdata = {'nodes': [], 'links': []}
        size = self.fsize
        query = {
            # "terminate_after": 2000,
            "from": 0, "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "match_all": {}
                        },
                        {
                            "query_string": {
                                "default_field": "retweeted_status.message",
                                "query": self.keyword
                            }
                        },
                        {
                            "range": {
                                "created": {
                                    "gte": self.gte,
                                    "lte": self.lte
                                }
                            }
                        }
                    ]
                }
            }
        }

        res = es.search(index="twitter", doc_type="tweet", body=query)
        # bro = flask.json.dumps(res)
        # print("elasticsearch time, got %d Hits in %d ms" % (res['hits']['total'], res['took']))
        # print (len(res['hits']['hits']))

        start_time = time.time()
        for hit in res['hits']['hits']:
            id_source = hit['_source']['user']['screen_name']
            isnode = list(filter(lambda person: person['id'] == id_source,
                                 self.gdata['nodes']))
            # if len(filter(lambda person: person['id'] == id_source, self.gdata['nodes'])) == 0:  # new node
            lislayman = filter(lambda person: person['id'] == id_source,
                               self.gdata['nodes'])
            if len(list(l)) == 0:
                node = {'id': id_source, 'size': 1, 'type': 'retweet', 'role': 'layman'}
                self.gdata['nodes'].append(node)
            else:  # node exist
                isnode[0]['size'] += 1

            id_target = hit['_source']['retweeted_status']['screen_name']
            isnode = list(filter(lambda person: person['id'] == id_target, self.gdata['nodes']))
            # if len(filter(lambda person: person['id'] == id_target,
            #              self.gdata['nodes'])) == 0:  # new node
            m = filter(lambda person: person['id'] == id_target,
                       self.gdata['nodes'])  # new node
            if len(list(m)) == 0:
                node = {'id': id_target, 'size': 1, 'type': 'retweet', 'role': 'landlord'}
                self.gdata['nodes'].append(node)
            else:
                isnode[0]['size'] += 1

                # links
            eid = len(self.gdata['links'])
            edge = {'source': id_source, 'target': id_target, 'size': 1, 'id': eid}
            self.gdata['links'].append(edge)
        elapse_time = time.time() - start_time
        print("guery drone time: ", elapse_time)
    #

    def graphanalytic(self):
        # graph analytic
        start_time = time.time()
        self.G = nx.readwrite.json_graph.node_link_graph(self.gdata)
        self.graphcentrality()  # calculate centrality
        self.graphattributes()  # set graph attributes
        elapse_time = time.time() - start_time
        print('graph analytic time: ', elapse_time)
        return self.graphtojson()

    def graphcentrality(self):
        # self.betweenness = nx.betweenness_centrality(self.G) #most expensive
        # self.closeness = nx.closeness_centrality(self.G) #2nd most expensive
        self.communities = community.best_partition(self.G)

    # #set graph attributes from centrality calculation
    def graphattributes(self):
        # nx.set_node_attributes(self.G, self.betweenness, 'betweenness')
        # nx.set_node_attributes(self.G, self.closeness, 'closeness')
        nx.set_node_attributes(self.G, self.communities, 'modularity')
    #
    # # save to json format

    def graphtojson(self):
        # jdata = nx.readwrite.json_graph.node_link_data(self.G, {'link': 'edges', 'source': 'sources', 'target': 'target', 'id': 'id'})
        # jdata = nx.readwrite.json_graph.node_link_data(self.G)
        # jdata['edges'][0]['id']=1
        awal = datetime.strptime(self.accounts[0]['created'],
                                 "%Y/%m/%d %H:%M:%S")
        akhir = datetime.strptime(self.accounts[len(self.accounts)-1]['created'],
                                  "%Y/%m/%d %H:%M:%S")
        waktu = abs((akhir-awal).days)
        data = nx.readwrite.json_graph.node_link_data(
            self.G, {'link': 'links', 'source': 'source', 'target': 'target'})
        data.update({'general_info': {'keyword': self.keyword, 'waktu': waktu,
                                      'tweet_counts': self.tweet_counts},
                     'hashtags': self.hashtags, 'accounts': self.accounts})
        jdata = flask.json.dumps(data, ensure_ascii=False, indent=4)
        nx.write_gml(self.G, "testg.gml")  # save to file
        with io.open(os.path.join(APP_STATIC, 'data.json'), 'w', encoding='utf-8') as f:
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


qsna = QuerySNA()
# print(qsna.hashtags(qsna.qretweet()))
# # start_time = time.time()
qsna.qretweet()
# qsna.simqretweet()
# # elapse_time = time.time() - start_time
# # print ('total time: ', elapse_time)
# # print(qsna.gdata['nodes'])
gjson = qsna.graphanalytic()
# with open(qsna.keyword+'.json', 'w') as f:
#     json.dump(json.loads(gjson),f)
