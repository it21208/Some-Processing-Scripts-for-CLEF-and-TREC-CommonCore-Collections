# author: alexandros ioannidis
import sys
from sentence_transformers import SentenceTransformer, util, models
import scipy.spatial
import pickle
from collections import OrderedDict
import operator

# pathToCorpus = '/home/pfb16181/common_core_data1855658.tsv'
pathToCorpus = '/home/pfb16181/common_core_data_with_FullText.tsv'
pathToQueries = '/home/pfb16181/NetBeansProjects/lucene4ir-master/data/TREC-CommonCore/topicsfile'
pathToTrecResults = '/home/pfb16181/NetBeansProjects/hedwig/scripts/run.core17.bm25+rm3.topics.core17.txt'
# pathToTrecResults = '/home/pfb16181/NetBeansProjects/hedwig/scripts/run.core17.bm25.topics.core17.txt'

def readInitialRanking(pathToTrecResults):
    # read trec results file
    f = open(pathToTrecResults, "r")
    topic_len_trec_dict = {}
    listOfDocsForTopic = []
    previous_topic = ''
    for idx, line in enumerate(f):
        topic = line.split()[0]
        doc = line.split()[2]
        if idx != 1:
            if topic == previous_topic:
                # add doc id to list
                listOfDocsForTopic.append(doc)
            else:
                if previous_topic not in topic_len_trec_dict.keys():
                    topic_len_trec_dict[previous_topic] = listOfDocsForTopic
                # reset doc id list for next topic
                listOfDocsForTopic = []
                # add the first doc id of the next topic to the reset list
                listOfDocsForTopic.append(doc)
        # the following block of code is executed only for the first iteration
        else: 
            # add first doc id to the list only for the first topic 
            listOfDocsForTopic.append(doc)
        previous_topic = topic
    # for the last topic 
    topic_len_trec_dict[topic] = listOfDocsForTopic
    return(topic_len_trec_dict)


queriesDict = {}
queries = []
with open(pathToQueries) as file_in:
    for idx, line in enumerate(file_in):
        newLine = line.split(" ", 1)
        queries.append(newLine[0]+' '+newLine[1].rstrip())
        queriesDict[newLine[0]+' '+newLine[1].rstrip()] = newLine[0]
print('created queries dictionary')

dictWithPMIDS = {}
tempList = []
with open(pathToCorpus) as file_in:
    corpus = []
    for line in file_in:
        newLine = line.split(" ", 1)
        if len(line) < 1 or newLine[0] in tempList:
            continue 
        try: 
            tempList.append(newLine[0])
            corpus.append(newLine[1].rstrip())
            dictWithPMIDS[newLine[0]] = newLine[1].rstrip()
        except Exception as e:
            pass
print('corpus size: {}'.format(len(corpus)))


for idx, j in enumerate(corpus):
    corpus[idx] = j.split('.')
print('split documents into sentences in corpus data structure')

for idx, (k, v) in enumerate(dictWithPMIDS.items()):
    dictWithPMIDS[k] = v.split('.')
print('split documents into sentences in dictWithPMIDS data structure')


# Swap Keys and Values in Dictionary dictWithPMIDS
# new_dictWithPMIDS = dict([(value, key) for key, value in dictWithPMIDS.items()])
New_dictWithPMIDS = {}
for idx, (k, v) in enumerate(dictWithPMIDS.items()):
    for i in v:
        New_dictWithPMIDS[i] = k
print('created dictionary New_dictWithPMIDS to relate sentences with pmids')


corpus50 = {}
resultslst = []
dict_of_len_ids_for_topic = readInitialRanking(pathToTrecResults)

for query in queries:
    dictForIndexing = {}
    word_embedding_model = models.Transformer('bert-base-uncased')
    pooling_model = models.Pooling(word_embedding_model.get_word_embedding_dimension())
    embedder = SentenceTransformer(modules=[word_embedding_model, pooling_model])
    
    print('size of corpus for topic {}: {}'.format( query.split(" ", 1)[0], len(dict_of_len_ids_for_topic[query.split(" ", 1)[0]]) ) )
    list_of_pmids_for_topic = dict_of_len_ids_for_topic[query.split(" ", 1)[0]]
    
    corpus50[query.split(" ", 1)[0]] = []
    
    for pmid in list_of_pmids_for_topic:
        try:
            corpus50[query.split(" ", 1)[0]].append(dictWithPMIDS[pmid])
            dictForIndexing[dictWithPMIDS[pmid]] = pmid
        except Exception as e:
            pass
            
    # cur_corpus = corpus50[query.split(" ", 1)[0]]
    cur_corpus = [item for sublist in corpus50[query.split(" ", 1)[0]] for item in sublist]
    cur_corpus = list(dict.fromkeys(cur_corpus))
    
    def removeDuplicateValuesFromDict(dictForIndexing):
        seen = set()
        for key in dictForIndexing.keys():
            value = tuple(dictForIndexing[key])
            if value in seen:
                del dictForIndexing[key]
            else:
                seen.add(value)
        return(dictForIndexing)
    
    dictForIndexing = removeDuplicateValuesFromDict(dictForIndexing)
    print('corpus with size {} created'.format(len(cur_corpus)))
    corpus_embeddings = embedder.encode(cur_corpus)
    query_embeddings = embedder.encode(query)
    
    closest_n = len(list_of_pmids_for_topic)-1
    ranking = 1
    savedPMIDSwithTheirAggregatedSentenceScores = OrderedDict()  # declare ordered dictionary
    for query_embedding in query_embeddings:
        distances = scipy.spatial.distance.cdist([query_embedding], corpus_embeddings, "cosine")[0]
        results = zip(range(len(distances)), distances)
        results = sorted(results, key=lambda x: x[1])
        
        for idx, distance in results[0:closest_n]:
            try:
                if New_dictWithPMIDS[cur_corpus[idx]] in savedPMIDSwithTheirAggregatedSentenceScores:
                    # get maximum sentence score
                    # if savedPMIDSwithTheirAggregatedSentenceScores[New_dictWithPMIDS[cur_corpus[idx]]] < distance: 
                    #     savedPMIDSwithTheirAggregatedSentenceScores[New_dictWithPMIDS[cur_corpus[idx]]] =  distance
                    
                    # aggregate the sentences scores of each doc
                    # i need to change this to aggregate the scores of the top 3 sentences and not just find the max score (as implemented above)
                    savedPMIDSwithTheirAggregatedSentenceScores[New_dictWithPMIDS[cur_corpus[idx]]][0] += distance
                    savedPMIDSwithTheirAggregatedSentenceScores[New_dictWithPMIDS[cur_corpus[idx]]][1] += 1
                else:
                    # initialise ordered dictionary with zeros to aggregate the sentences scores for each doc
                    # savedPMIDSwithTheirAggregatedSentenceScores[New_dictWithPMIDS[cur_corpus[idx]]] =  distance
                    savedPMIDSwithTheirAggregatedSentenceScores[New_dictWithPMIDS[cur_corpus[idx]]] = [distance, 1]
            except Exception as e:
                pass
        print('created savedPMIDSwithTheirAggregatedSentenceScores dictionary')
        
        savedPMIDSwithTheirAggregatedSentenceScores_withAverageScores = {}
        for k, v in savedPMIDSwithTheirAggregatedSentenceScores.items():
            savedPMIDSwithTheirAggregatedSentenceScores_withAverageScores[k] = v[0]/v[1]
            
        
        sorted_d = dict(sorted(savedPMIDSwithTheirAggregatedSentenceScores_withAverageScores.items(), key=operator.itemgetter(1),reverse=True))
        # for k, v in savedPMIDSwithTheirAggregatedSentenceScores.items():
        for k, v in sorted_d.items():
            try:
                temp = str(queriesDict[query]) + " " + "QO" + " " + k + " " + str(ranking) + " "  + str(v) + " " + "similarity.tar.title.and.query"
                resultslst.append(temp)
                ranking += 1
            except:
                pass
        print('-------------------------------------------------')
            
dirToWrite = '/home/pfb16181/NetBeansProjects/hedwig/scripts/AverageofAggregatedSentenceScoresfulltext_resultsFSSVmeanPoolingCommonCore_bm25tar.txt'
with open(dirToWrite, 'w') as f:
    for item in resultslst:
        f.write("%s\n" % item)
