from __future__ import absolute_import, division, unicode_literals

import sys
import io
import numpy as np
import logging
import argparse
import codecs
import array

parser = argparse.ArgumentParser(description='Flair Embeddings')

parser.add_argument("--data_path", type=str, default='./data', help="Path to data (default ./data)")
parser.add_argument('--embedding_path', type=str, default= './embeddings/glove/glove.840B.300d.txt',help="Path to embeddings (default ./embeddings/glove/glove.840B.300d.txt")
parser.add_argument("--nhid", type=int, default=0, help="number of hidden layers: 0 for Logistic Regression or >0 for MLP (default 0)")
parser.add_argument('--tasks', nargs='+', default= ['BioC','CitationSA','ClinicalSA','BioASQ','PICO','PUBMED20K','RQE','ClinicalSTS','BIOSSES','MEDNLI'] ,help="Bio Tasks to evaluate (default ALL TASKS)")
parser.add_argument("--folds", type=int, default=10, help="number of k-folds for cross validations(default 10)")
parser.add_argument("--dim", type=int, default=300, help="Embedding dimension (default 300)")
parser.add_argument("--usescikitlearn", action='store_false', default=True, help="Use scikit-learn(default cuda-pytorch)")
params, _ = parser.parse_known_args()
# Set PATHs
PATH_TO_SENTEVAL = '../'
PATH_TO_DATA = params.data_path
PATH_TO_VEC =  params.embedding_path
params_senteval = {'task_path': PATH_TO_DATA, 'usepytorch': params.usescikitlearn, 'kfold': params.folds}

# Set up logger
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.DEBUG)
logging.info("-------------------------------------BOW MODEL-------------------------------------"+"\nPATH_TO_DATA: " + str(PATH_TO_DATA) +"\nPATH_TO_VEC: "+ str(PATH_TO_VEC)+"\nTASKS: "+ str(params.tasks))

dim=params.dim
nhid=params.nhid
params_senteval['classifier'] ={'nhid': nhid, 'optim': 'adam','batch_size': 64, 'tenacity': 5,'epoch_size': 4}

# import SentEval
sys.path.insert(0, PATH_TO_SENTEVAL)
import senteval


# Create dictionary
def create_dictionary(sentences, threshold=0):
    words = {}
    for s in sentences:
        for word in s:
            words[word] = words.get(word, 0) + 1

    if threshold > 0:
        newwords = {}
        for word in words:
            if words[word] >= threshold:
                newwords[word] = words[word]
        words = newwords
    words['<s>'] = 1e9 + 4
    words['</s>'] = 1e9 + 3
    words['<p>'] = 1e9 + 2

    sorted_words = sorted(words.items(), key=lambda x: -x[1])  # inverse sort
    id2word = []
    word2id = {}
    for i, (w, _) in enumerate(sorted_words):
        id2word.append(w)
        word2id[w] = i

    return id2word, word2id

def getFileSize(inf):
    curIx = inf.tell()
    inf.seek(0, 2)  # jump to end of file
    file_size = inf.tell()
    inf.seek(curIx)
    return file_size
# Get word vectors from vocabulary (glove, word2vec, fasttext ..)

# Get word vectors from vocabulary (glove, word2vec, fasttext ..)
def get_wordvec(path_to_vec, word2id):
    word_vec = {}
    
    
    #
    if path_to_vec.endswith('.bin'):
        vocab_words=[]
        inf = open(path_to_vec, 'rb')
        vocab='/content/gdrive/My Drive/MedSentEval/models/glove/PubMed_Glove_vocab'
        if not vocab:
            raise Exception("vocab must be specified for GloVe embeddings")
        h = codecs.open(vocab, 'r', 'utf-8')
        for line in h:
            vocab_words.append(line.strip().split()[0])
        h.close()
        
    # set up for parsing the stored numbers
        real_size = 8  # default double precision
        file_size = getFileSize(inf)
        dim = int((float(file_size) / (real_size * len(vocab_words))) / 2)
        for i in range(len(vocab_words)):
            word, vec = vocab_words[i],array.array( 'd',inf.read(dim*2*real_size))
            if word in word2id:
                word_vec[word] = np.asarray(vec)
                #print(word_vec)
        wvec_dim=(len( np.asarray(vec)))
        inf.close()
    else:
        with io.open(path_to_vec, 'r', encoding='utf-8') as f:
        # if word2vec or fasttext file : skip first line "next(f)"
            for line in f:
                word, vec = line.split(' ', 1)
                if word in word2id:
                    word_vec[word] = np.fromstring(vec, sep=' ')
        wvec_dim=(len( np.fromstring(vec, sep=' ')))
    #
    
    

    #with io.open(path_to_vec, 'r', encoding='utf-8') as f:
    #    # if word2vec or fasttext file : skip first line "next(f)"
    #    for line in f:
    #        word, vec = line.split(' ', 1)
    #        #print(np.fromstring(vec, sep=' ').shape, len(np.fromstring(vec, sep=' ')))
     #       if word in word2id:
      #          word_vec[word] = np.fromstring(vec, sep=' ')
                


    logging.info('Found {0} words with word vectors, out of \
        {1} words'.format(len(word_vec), len(word2id)))
    
    
    print(wvec_dim)
    #print(word_vec)
    return word_vec,wvec_dim



# SentEval prepare and batcher
def prepare(params, samples):
    _, params.word2id = create_dictionary(samples)
    params.word_vec,params.wvec_dim = get_wordvec(PATH_TO_VEC, params.word2id)
    #print(params.wvec_dim)
    #params.wvec_dim= 300
    return

def batcher(params, batch):
    batch = [sent if sent != [] else ['.'] for sent in batch]
    embeddings = []

    for sent in batch:
        sentvec = []
        for word in sent:
            if word in params.word_vec:
                sentvec.append(params.word_vec[word])
        if not sentvec:
            vec = np.zeros(params.wvec_dim)
            sentvec.append(vec)
        sentvec = np.mean(sentvec, 0)
        embeddings.append(sentvec)

    embeddings = np.vstack(embeddings)
    return embeddings



# Set up logger
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.DEBUG)

# Set up logger
if __name__ == "__main__":
    se = senteval.engine.SE(params_senteval, batcher, prepare)
    transfer_tasks=[]
    for i in params.tasks:
        transfer_tasks.append(i)
    results = se.eval(transfer_tasks)
    print(results)
