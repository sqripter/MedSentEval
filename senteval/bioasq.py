# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#

'''
BioASQ : Medical Question Answering 
'''
from __future__ import absolute_import, division, unicode_literals

import os
import logging
import numpy as np
import io
import copy

from senteval.tools.validation import KFoldClassifier

from sklearn.metrics import f1_score


class BioASQEval(object):
    def __init__(self, task_path, seed=1111):
        logging.info('***** Transfer task : BioASQ task b / Phase b / yes_no quetsions *****\n\n')
        self.seed = seed
        train = self.loadFile(os.path.join(task_path,
                              'BioASQ_train.txt'))
        test = self.loadFile(os.path.join(task_path,
                             'BioASQ_test.txt'))
        
        self.qa_data = {'train': train, 'test': test}
        

    def do_prepare(self, params, prepare):
        # TODO : Should we separate samples in "train, test"?
        samples = self.qa_data['train']['question'] + \
                  self.qa_data['train']['snippet'] + \
                  self.qa_data['test']['question'] + self.qa_data['test']['snippet']
        return prepare(params, samples)

    def loadFile(self, fpath):
        qa_data = {'question': [], 'snippet': [], 'label': []}
        tgt2idx = {'no': 0, 'yes': 1}
        with io.open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    question, snippet, label = line.strip().split('\t')
                    qa_data['question'].append(question.split(' '))
                    qa_data['snippet'].append(snippet.split(' '))
                    qa_data['label'].append(tgt2idx[label.strip()])
                except:
                    continue
        return qa_data

    def run(self, params, batcher):
        qa_embed = {'train': {}, 'test': {}}

        for key in self.qa_data:
            logging.info('Computing embedding for {0}'.format(key))
            # Sort to reduce padding
            text_data = {}
            sorted_corpus = sorted(zip(self.qa_data[key]['question'],
                                       self.qa_data[key]['snippet'],
                                       self.qa_data[key]['label']),
                                   key=lambda z: (len(z[0]), len(z[1]), z[2]))
            text_data['question'] = [x for (x, y, z) in sorted_corpus]
            text_data['snippet'] = [y for (x, y, z) in sorted_corpus]
            text_data['label'] = [z for (x, y, z) in sorted_corpus]
            
            for txt_type in ['question', 'snippet']:
                qa_embed[key][txt_type] = []
                for ii in range(0, len(text_data['label']), params.batch_size):
                    batch = text_data[txt_type][ii:ii + params.batch_size]
                    #print(batch)
                    embeddings = batcher(params, batch)
                    #print(embeddings.shape)
                    #for i,j in zip(batch,embeddings):
                    #    print(i,j)
                    qa_embed[key][txt_type].append(embeddings)
                qa_embed[key][txt_type] = np.vstack(qa_embed[key][txt_type])
            qa_embed[key]['label'] = np.array(text_data['label'])
            logging.info('Computed {0} embeddings'.format(key))

        # Train
        trainQ = qa_embed['train']['question']
        trainS = qa_embed['train']['snippet']
        #trainQS = np.c_[np.abs(trainQ - trainS), trainQ * trainS]
        trainQS = np.hstack((trainQ, trainS, trainQ * trainS,np.abs(trainQ - trainS)))
        trainY = qa_embed['train']['label']
        #print(trainQ)
        #print(trainS)
        #print(trainQS)

        # Test
        testQ = qa_embed['test']['question']
        testS = qa_embed['test']['snippet']
        #testQS = np.c_[np.abs(testQ - testS), testQ * testS]
        testQS = np.hstack((testQ, testS, testQ * testS,np.abs(testQ - testS)))
        testY = qa_embed['test']['label']
        
        config = {'nclasses': 2, 'seed': self.seed,
                  'usepytorch': params.usepytorch,
                  'classifier': params.classifier,
                  'nhid': params.nhid, 'kfold': params.kfold}

        config_classifier = copy.deepcopy(params.classifier)
        config_classifier['max_epoch'] = 1
        config_classifier['epoch_size'] = 64
        config_classifier['batch_size'] =64
        config['classifier'] = config_classifier
        print(config_classifier)
        
        clf = KFoldClassifier(train={'X': trainQS, 'y': trainY},
                              test={'X': testQS, 'y': testY}, config=config)

        devacc, testacc, yhat = clf.run()
        testf1 = round(100*f1_score(testY, yhat), 2)
        logging.debug('Dev acc : {0} Test acc {1}; Test F1 {2} for BioASQ 5b task (yes/no questions).\n'
                      .format(devacc, testacc, testf1))
        return {'devacc': devacc, 'acc': testacc, 'f1': testf1,
                'ndev': len(trainQS), 'ntest': len(testQS)}

