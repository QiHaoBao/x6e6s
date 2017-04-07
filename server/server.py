from flask import Flask, request, jsonify
import flask
import json
import random
import time
import sys
import re
import requests
#xes module
import xes
import os
#xmljson
from xmljson import badgerfish as bf
from xml.etree.ElementTree import fromstring
import itertools
import networkx as nx

from networkx.readwrite import json_graph

JPL_HOST_GET_WORKFLOW_BY_ID = "http://localhost:9005/serviceExecutionLog/getServiceExecutionLogByWorkflowId/"
PROM_DIR = "/home/soc/Downloads/prom/prom-6.6-all-platforms/"
#JPL_HOST_GET_WORKFLOW_BY_ID = "http://hawking.sv.cmu.edu:9005/serviceExecutionLog/getServiceExecutionLogByWorkflowId/"
#PROM_DIR = "/home/new/m66m/"


app = Flask(__name__)

@app.route("/test", methods=["GET"])
def test():
    wid = request.args.get("wid")
    print "Getting Traces..."
    result = requests.get(JPL_HOST_GET_WORKFLOW_BY_ID + wid).content
    print "Got Traces..."
    result = json.loads(result)
    print type(result)
    
    traces = {}
    log = xes.Log()
    workflowId = result[0]['workflowId']
    for x in result:
        print "WRID " + x['workflowRunId']
        print "Name " + x['climateService']['serviceEntry']['name']
        if ("WRID" + str(x['workflowRunId']) not in traces):
            traces["WRID" + str(x['workflowRunId'])] = [x['climateService']['serviceEntry']['name']]
        else:
            traces["WRID" + str(x['workflowRunId'])].append(x['climateService']['serviceEntry']['name'])
        print "Name " + x['climateService']['serviceEntry']['name']
        
    for y in traces:
        t = xes.Trace()
        for z in range(len(traces[y])):
            e = xes.Event()
            e.attributes = [
                xes.Attribute(type="string", key="org:resource", value=traces[y][z]),
                xes.Attribute(type="string", key="concept:name", value=traces[y][z])
            ]
            t.add_event(e)
        log.add_trace(t)
        
    log.classifiers = [
        xes.Classifier(name="org:resource",keys="org:resource"),
        xes.Classifier(name="concept:name",keys="concept:name")
    ]
    open(PROM_DIR + "server.xes", "w").write(str(log))
    print "=================================="   
    
    with open(PROM_DIR + "script_inductive_miner.txt", "rt") as fin:
        with open(PROM_DIR + "script_inductive_miner_workflow_" + workflowId + ".txt", "wt") as fout:
            for line in fin:
                fout.write(line.replace('mined_net_server.pnml', 'mined_net_workflow_' + workflowId + '.pnml'))
    
    os.chdir(PROM_DIR)   
    print os.system("pwd;sh " + PROM_DIR + "ProM66_CLI.sh -f " + PROM_DIR + "script_inductive_miner_workflow_" + workflowId + ".txt")

    with open(PROM_DIR + 'mined_net_workflow_' + workflowId + '.pnml', "rt") as fin:
        for i,line in enumerate(fin):
            if i == 1:
                jsoned = bf.data(fromstring(line))
    
    with open(PROM_DIR + "jsoned_workflow_" + workflowId + ".txt", "wt") as fout:
        fout.write(json.dumps(jsoned))
        
    G=nx.DiGraph()

    page = jsoned['pnml']['net']['page']

    for p in page['place']:
        #print p['@id']
        G.add_node(p['@id'], name = p['name']['text']['$'], sort = 'place')

    for t in page['transition']:
        #print t['@id']
        G.add_node(t['@id'], name = t['name']['text']['$'], sort = 'transition')

    for a in page['arc']:
        #print a['@id']
        G.add_edge(a['@source'], a['@target'], name = a['name']['text']['$'], sort = 'arc')
        
    test_res = set(n for u,v,d in G.edges_iter(data=True)
               if d['sort']=='arc'
               for n in (u, v)
               if G.node[n]['sort']=='place')

    #print str(test_res)
    comb = list(itertools.combinations(test_res,2))
    uow = []
    #print comb
    for i in comb:
        for j in G.successors(i[0]):
            if nx.has_path(G, j, i[1]):
                #print (i[0], i[1])
                uow.append((i[0], i[1]))
                break
    print uow
        
    jsonRes = {"all_uows" : []}
    for pair in uow:
        sub = nx.DiGraph()
        for path in nx.all_simple_paths(G, source=pair[0], target=pair[1]):         
            for node in path:
                sub.add_node(node)
        subG = nx.subgraph(G, sub)
        print subG.nodes()
        #nx.draw_networkx(subG)
        #plt.show()    
        jsonTmp = json_graph.node_link_data(subG)
        jsonRes['all_uows'].append(jsonTmp)
    
    return json.dumps(jsonRes)

@app.route("/ttt", methods=["GET"])
def ttt():
    if request.method == "GET":
        return "Right, use GET."
    else:
        return "Please use GET."

if __name__ == "__main__":
    app.run(port=5000, host= '0.0.0.0', debug=True)
    #app.run(port=5000, host= '127.0.0.1', debug=True)

