# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#

from __future__ import absolute_import, division

import os
import sys
import logging
import tensorflow as tf
import tensorflow_hub as hub
tf.logging.set_verbosity(0)

import argparse

parser = argparse.ArgumentParser(description='Goggle USE Embeddings')

parser.add_argument("--data_path", type=str, default='./data', help="Path to data (default ./data)")
parser.add_argument("--nhid", type=int, default=0, help="number of hidden layers: 0 for Logistic Regression or >0 for MLP (default 0)")
parser.add_argument('--tasks', nargs='+', default= ['BioC','CitationSA','ClinicalSA','BioASQ','PICO','PUBMED20K','RQE','ClinicalSTS','BIOSSES','MEDNLI'] ,help="Bio Tasks to evaluate (default ALL TASKS)")
parser.add_argument("--folds", type=int, default=10, help="number of k-folds for cross validations(default 10)")
parser.add_argument("--usescikitlearn", action='store_false', default=True, help="Use scikit-learn(default cuda-pytorch)")

params, _ = parser.parse_known_args()
# Set PATHs
PATH_TO_SENTEVAL = '../'
PATH_TO_DATA = params.data_path
params_senteval = {'task_path': PATH_TO_DATA, 'usepytorch': params.usescikitlearn, 'kfold': params.folds}

# Set up logger
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.DEBUG)
logging.info("-------------------------------------GOOGLE USE MODEL-------------------------------------"+"\nPATH_TO_DATA: " + str(PATH_TO_DATA) +"\nTASKS: "+ str(params.tasks))


nhid=params.nhid
params_senteval['classifier'] ={'nhid': nhid, 'optim': 'adam','batch_size': 64, 'tenacity': 5,'epoch_size': 4}


# import SentEval
sys.path.insert(0, PATH_TO_SENTEVAL)
import senteval

# tensorflow session
session = tf.Session()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# SentEval prepare and batcher
def prepare(params, samples):
    return

def batcher(params, batch):
    batch = [' '.join(sent) if sent != [] else '.' for sent in batch]
    embeddings = params['google_use'](batch)
    return embeddings

def make_embed_fn(module):
  with tf.Graph().as_default():
    sentences = tf.placeholder(tf.string)
    embed = hub.Module(module)
    embeddings = embed(sentences)
    session = tf.train.MonitoredSession()
  return lambda x: session.run(embeddings, {sentences: x})


# Start TF session and load Google Universal Sentence Encoder
encoder = make_embed_fn("https://tfhub.dev/google/universal-sentence-encoder-large/3")


params_senteval['google_use'] = encoder

if __name__ == "__main__":
    se = senteval.engine.SE(params_senteval, batcher, prepare)
    transfer_tasks = params.tasks
    results = se.eval(transfer_tasks)
    print(results)
