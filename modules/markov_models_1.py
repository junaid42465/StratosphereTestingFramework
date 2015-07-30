# Part of this file was taken from Viper - https://github.com/botherder/viper
# The rest is from the Stratosphere Testing Framework
# See the file 'LICENSE' for copying permission.

# This module implements markov chains of first order over the letters in the chain of states of the behavioral models.
import persistent
import pykov
import BTrees.OOBTree
from subprocess import Popen, PIPE
import copy
import re
import numpy as np

from stf.common.out import *
from stf.common.abstracts import Module
from stf.core.models import  __groupofgroupofmodels__ 
from stf.core.labels import __group_of_labels__
from stf.core.database import __database__








#################
#################
#################
class Markov_Model(persistent.Persistent):
    """ This class is the actual markov model of first order to each label"""
    def __init__(self, id):
        self.mm_id = id
        self.state = ""
        self.label_id = -1
        self.connections = BTrees.OOBTree.BTree()

    def get_id(self):
        return self.mm_id

    def set_id(self, id):
        self.mm_id = id

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state

    def get_label_id(self):
        return self.label_id

    def set_label_id(self, label_id):
        self.label_id = label_id

    def get_connections(self):
        return self.connections
    
    def set_connections(self, connections):
        # Use deepcopy so we store a copy of the connections and not the connections themselves. This is needed because more connections can be added to the label, however the state in this markov chain will miss them. Also because the original connections can be deleted
        self.connections = copy.deepcopy(connections)

    def set_self_probability(self, prob):
        """ Set the probability of detecting itself """
        self.self_probability = prob

    def get_self_probability(self):
        try:
            return self.self_probability
        except AttributeError:
            return False

    def count_connections(self):
        """ Return the amount of connections in the markov model """
        count = 0
        for id in self.connections:
            for conn in self.connections[id]:
                count += 1
        return count

    def get_init_vector(self):
        return self.init_vector

    def set_matrix(self, matrix):
        self.matrix = matrix

    def get_matrix(self):
        return self.matrix

    def create(self, state):
        """ Create the Markov chain itself. We use the parameter instead of the attribute so we can compute the matrix for different states """
        # Separete the letters considering the letter and the symbol as a unique state:
        # So from "88,a,b," we get: '8' '8,' 'a,' 'b,'
        try:
            # This is a first order markov model. Each individual object (letter, number, etc.) is a state
            separated_letters = list(state)
        except AttributeError:
            print_error('There is no state yet')
            return False
        # Generate the MC
        self.init_vector, self.matrix = pykov.maximum_likelihood_probabilities(separated_letters, lag_time=1, separator='#')


    def get_matrix(self):
        """ Return the matrix """
        return self.matrix

    def print_matrix(self):
        print_info('Matrix of the Markov Model {}'.format(self.get_id()))
        for first in self.matrix:
            print first, self.matrix[first]

    def simulate(self, amount):
        print type(self.matrix.walk(5))
        """ Generate a simulated chain using this markov chain """
        chain = ''
        chain += state[0]
        chain += state[1]
        chain += state[2]
        chain += ''.join(self.matrix.walk(amount))
        print chain
        return True

    def compute_probability(self, state):
        """ Given a chain of letters, return the probability that it was generated by this MC """
        # Our computation is different of the normal one in:
        # - If a transition of states is not in the MC, we just ignore the transition and continue.
        i = 0
        probability = 0
        ignored = 0
        # We should have more than 2 states at least
        while i < len(state) and len(state) > 1:
            try:
                vector = state[i] + state[i+1]
                growing_v = state[0:i+2]
                # The transitions that include the # char will be automatically excluded
                log_temp_prob = self.matrix.walk_probability(vector)
                temp_prob = log_temp_prob
                i += 1
                if temp_prob != float('-inf'):                
                    probability = probability + temp_prob # logs should be +
                    #print_info('\tTransition [{}:{}]: {} -> Prob:{:.10f}. CumProb: {}'.format(i-1, i,vector, temp_prob, probability))
                else:
                    # Here is our trick. If two letters are not in the matrix... ignore the transition.
                    # The temp_prob is the penalty we assign if we can't find the transition
                    #temp_prob = -2.3
                    temp_prob = -4.6 # Which is approx 0.01 probability
                    probability = probability + temp_prob # logs should be +
                    if '#' not in vector:
                        ignored += 1
                    continue
            except IndexError:             
                # We are out of letters        
                break
        #if ignored:
            #print_warning('Ignored transitions: {}'.format(ignored))
            #ignored = 0
        return probability       

    def get_label(self):
        """ Return the label name"""
        label = __group_of_labels__.get_label_by_id(self.get_label_id())
        if label:
            label_name = label.get_name()
        else:
            print_error('The label used in the markov model {} does not exist anymore. You should delete the markov chain manually (The markov chain {} does not appear in the following list).'.format(self.get_id(), self.get_id()))
        return label
            
    def __repr__(self):
        label = __group_of_labels__.get_label_by_id(self.get_label_id())
        if label:
            label_name = label.get_name()
        else:
            label_name = 'Deleted'
        #current_connections = label.get_connections_complete()
        response = "Id:"+str(self.get_id())+", Label: "+label_name+", State Len:"+str(len(self.get_state()))+", #Conns:"+str(self.count_connections())+", First 50 states: "+self.get_state()[0:50]
        return(response)



######################
######################
######################
class Group_of_Markov_Models_1(Module, persistent.Persistent):
    cmd = 'markov_models_1'
    description = 'This module implements markov chains of first order over the letters in the chains of states in a LABEL. ' + yellow('Warning') + ', if the original models or labels are deleted, you should fix these models by hand.'
    authors = ['Sebastian Garcia']
    # Markov Models main dictionary
    markov_models = BTrees.OOBTree.BTree()

    # Mandatory Method!
    def __init__(self):
        # Call to our super init
        super(Group_of_Markov_Models_1, self).__init__()
        self.parser.add_argument('-l', '--list', action='store_true', help='List the markov models already applied. You can use a filter with -f.')
        self.parser.add_argument('-g', '--generate', metavar='generate', help='Generate the markov chain for this label. Give label name.')
        self.parser.add_argument('-m', '--printmatrix', metavar='printmatrix', help='Print the markov chains matrix of the given markov model id.')
        self.parser.add_argument('-S', '--simulate', metavar='simulate', help='Use this markov chain to generate a new simulated chain of states. Give the markov chain id. The length is now fixed in 100 states.')
        self.parser.add_argument('-d', '--delete', metavar='delete', help='Delete this markov chain. Give the markov chain id.')
        self.parser.add_argument('-p', '--printstate', metavar='printstate', help='Print the chain of states of all the models included in this markov chain. Give the markov chain id.')
        self.parser.add_argument('-r', '--regenerate', metavar='regenerate', help='Regenerate the markov chain. Usually because more connections were added to the label. Give the markov chain id.')
        self.parser.add_argument('-a', '--generateall', action='store_true', help='Generate the markov chain for all the labels that don\'t have one already')
        self.parser.add_argument('-f', '--filter', metavar='filter', nargs = '+', default="", help='Filter the markov models. For example for listing. Keywords: name. Usage: name=<text>. Partial matching.')
        self.parser.add_argument('-n', '--numberoffflows', metavar='numberofflows', default="3", help='When creating the markov models, this is the minimum number of flows that the connection should have. Less than this and the connection will be ignored. Be default 3.')
        self.parser.add_argument('-t', '--train', metavar='markovmodelid', help='Train the distance threshold of this Markov Model. Use -f to give a list of test Markov Models')

    # Mandatory Method!
    def get_name(self):
        """ Return the name of the module"""
        return self.cmd

    # Mandatory Method!
    def get_main_dict(self):
        """ Return the main dict where we store the info. Is going to the database"""
        return self.markov_models

    # Mandatory Method!
    def set_main_dict(self, dict):
        """ Set the main dict where we store the info. From the database"""
        self.markov_models = dict

    def get_markov_model_by_label_id(self, id):
        """ Search a markov model by label id """
        for markov_model in self.get_markov_models():
            if markov_model.get_label_id() == id:
                return True
        return False

    def get_markov_model(self, id):
        try:
            return self.markov_models[id]
        except KeyError:
            return False

    def get_markov_models(self):
        return self.markov_models.values()

    def print_matrix(self, markov_model_id):
        try:
            self.markov_models[int(markov_model_id)].print_matrix()
        except KeyError:
            print_error('That markov model id does not exists.')

    def construct_filter(self, filter):
        """ Get the filter string and decode all the operations """
        # If the filter string is empty, delete the filter variable
        if not filter:
            try:
                del self.filter 
            except:
                pass
            return True
        self.filter = []
        # Get the individual parts. We only support and's now.
        for part in filter:
            # Get the key
            try:
                key = re.split('<|>|=|\!=', part)[0]
                value = re.split('<|>|=|\!=', part)[1]
            except IndexError:
                # No < or > or = or != in the string. Just stop.
                break
            try:
                part.index('<')
                operator = '<'
            except ValueError:
                pass
            try:
                part.index('>')
                operator = '>'
            except ValueError:
                pass
            # We should search for != before =
            try:
                part.index('!=')
                operator = '!='
            except ValueError:
                # Now we search for =
                try:
                    part.index('=')
                    operator = '='
                except ValueError:
                    pass
            self.filter.append((key, operator, value))

    def apply_filter(self, model):
        """ Use the stored filter to know what we should match"""
        responses = []
        try:
            self.filter
        except AttributeError:
            # If we don't have any filter string, just return true and show everything
            return True
        # Check each filter
        for filter in self.filter:
            key = filter[0]
            operator = filter[1]
            value = filter[2]
            if key == 'name':
                # For filtering based on the label assigned to the model with stf (contrary to the flow label)
                label = model.get_label()
                try:
                    labelname = label.get_name()
                except AttributeError:
                    # Label was deleted
                    labelname = False
                    responses.append(False)
                    continue
                if operator == '=':
                    if value in labelname:
                        responses.append(True)
                    else:
                        responses.append(False)
                elif operator == '!=':
                    if value not in labelname:
                        responses.append(True)
                    else:
                        responses.append(False)
            else:
                return False

        for response in responses:
            if not response:
                return False
        return True

    def list_markov_models(self, filter):
        self.construct_filter(filter)
        print_info('First Order Markov Models')
        rows = []
        for markov_model in self.get_markov_models():
            if self.apply_filter(markov_model):
                label = markov_model.get_label()
                if not label:
                    label_name = 'Deleted'
                    current_connections = 'Unknown'
                else:
                    label_name = label.get_name()
                    current_connections = label.get_connections_complete()
                needs_regenerate = True
                # Do we need to regenerate this mc?
                if current_connections == markov_model.get_connections():
                    needs_regenerate = False
                rows.append([ markov_model.get_id(), len(markov_model.get_state()), markov_model.count_connections(), label_name, needs_regenerate, markov_model.get_state()[0:100]])
        print(table(header=['Id', 'State Len', '# Connections', 'Label', 'Needs Regenerate', 'First 100 Letters in State'], rows=rows))

    def create_new_model(self, label_name, number_of_flows):
        """ Given a label name create a new markov chain object"""
        # Get the label object
        label_to_model = __group_of_labels__.get_label(label_name)
        if label_to_model:
            # Create a new markov chain object
            ## Get the new id
            try:
                mm_id = self.markov_models[list(self.markov_models.keys())[-1]].get_id() + 1
            except (KeyError, IndexError):
                mm_id = 1
            markov_model = Markov_Model(mm_id)
            # Store the label id
            markov_model.set_label_id(label_to_model.get_id())
            state = ""
            # Get all the connections in the label
            connections = label_to_model.get_connections_complete()
            # Get all the group of models and connections names
            for group_of_model_id in connections:
                # Get all the connections
                for conn in connections[group_of_model_id]:
                    # Get the model group
                    group = __groupofgroupofmodels__.get_group(group_of_model_id)
                    # Get the model
                    model = group.get_model(conn)
                    # Get each state
                    state += model.get_state() + '#'
            # Delete the last #
            state = state[:-1]
            # Store the state
            markov_model.set_state(state)
            # Store the connections
            markov_model.set_connections(connections)
            # Create the MM itself
            markov_model.create(markov_model.get_state())
            # Generate the self probability
            prob = markov_model.compute_probability(markov_model.get_state())
            markov_model.set_self_probability(prob)
            # Store
            self.markov_models[mm_id] = markov_model
        else:
            print_error('No label with that name')

    def simulate(self, markov_model_id):
        """ Generate a new simulated chain of states for this markov chain """
        try:
            markov_model = self.get_markov_model(int(markov_model_id))
            markov_model.simulate(100)
        except KeyError:
            print_error('No such markov model id')

    def delete(self, markov_model_id):
        """ Delete the markvov chain """
        try:
            self.markov_models.pop(int(markov_model_id))
        except KeyError:
            print_error('No such markov model id')

    def printstate(self, markov_model_id):
        """ Print all the info about the markov chain """
        try:
            markov_model = self.get_markov_model(int(markov_model_id))
        except KeyError:
            print_error('No such markov model id')
            return False
        print_info('Markov Chain ID {}'.format(markov_model_id))
        print_info('Label')
        label_name = __group_of_labels__.get_label_name_by_id(markov_model.get_label_id())
        print '\t', 
        print_info(label_name)
        state = markov_model.get_state()
        print_info('Len of State: {} (Max chars printed: 2000)'.format(len(state)))
        print '\t', 
        print_info(state[0:2000])
        print_info('Connections in the Markov Chain')
        connections = markov_model.get_connections()
        print '\t', 
        print_info(connections)
        # Plot the histogram of letters
        print_info('Histogram of Amount of Letters')
        dist_path,error = Popen('bash -i -c "type distribution"', shell=True, stderr=PIPE, stdin=PIPE, stdout=PIPE).communicate()
        if not error:
            distribution_path = dist_path.split()[0]
            list_of_letters = ''.join([i+'\n' for i in list(state)])[0:65535]
            print 'Key=Amount of letters (up to the first 65536 letters)'
            Popen('echo \"' + list_of_letters + '\" |distribution --height=50 | sort -nk1', shell=True).communicate()
        else:
            print_error('For ploting the histogram we use the tool https://github.com/philovivero/distribution. Please install it in the system to enable this command.')
        #print_info('Test Probability: {}'.format(markov_model.compute_probability("r*R*")))
        log_self_prob = markov_model.compute_probability(markov_model.get_state())
        print_info('Log Probability of detecting itself: {}'.format(log_self_prob))

    def regenerate(self, markov_model_id):
        """ Regenerate the markvov chain """
        try:
            markov_model = self.get_markov_model(int(markov_model_id))
        except KeyError:
            print_error('No such markov model id')
            return False
        label = __group_of_labels__.get_label_by_id(markov_model.get_label_id())
        connections = label.get_connections_complete()
        # Get all the group of models and connections names
        state = ""
        for group_of_model_id in connections:
            # Get all the connections
            for conn in connections[group_of_model_id]:
                # Get the model group
                group = __groupofgroupofmodels__.get_group(group_of_model_id)
                # Get the model
                model = group.get_model(conn)
                # Get each state
                state += model.get_state() + '#'
        # Delete the last #
        state = state[:-1]
        # Store the state
        markov_model.set_state(state)
        # Store the connections
        markov_model.set_connections(connections)
        # Create the MM itself
        markov_model.create(markov_model.get_state())
        print_info('Markov model {} regenerated.'.format(markov_model_id))

    def generate_all_models(self, number_of_flows):
        """ Read all the labels and generate all the markov models if they dont already have one """
        labels = __group_of_labels__.get_labels()
        for label in labels:
            if not self.get_markov_model_by_label_id(label.get_id()):
                # We dont have it
                self.create_new_model(label.get_name(), number_of_flows)

    def compute_errors(self, train_label, test_label, positive_label='CC', negative_label='Normal'):
        """ Get the train and test labels and figure it out the errors. A TP is when we detect CC not Botnet."""
        errors = {}
        errors['TP'] = 0.0
        errors['TN'] = 0.0
        errors['FN'] = 0.0
        errors['FP'] = 0.0
        if positive_label in train_label and positive_label in test_label:
            errors['TP'] += 1
        elif positive_label in train_label and negative_label in test_label:
            errors['FP'] += 1
        elif negative_label in train_label and negative_label in test_label:
            errors['TN'] += 1
        elif negative_label in train_label and positive_label in test_label:
            errors['FN'] += 1
        return errors

    def compute_error_metrics(self, errors):
        """ Given the errors, compute the performance metrics """
        TP = errors['TP']
        TN = errors['TN']
        FN = errors['FN']
        FP = errors['FP']
        """ Get the errors and compute the metrics """
        metrics = {}
        # The order is important, because later we sort based on the order. More important to take a decision should be up
        try:
            metrics['FMeasure1'] = 2 * TP / ((2 * TP) + FP + FN)
        except ZeroDivisionError:
            metrics['FMeasure1'] = -1
        try:
            metrics['FPR'] = FP / (FP + TN) 
        except ZeroDivisionError:
            metrics['FPR'] = -1
        try:
            metrics['TPR'] = TP / (TP + FN)
        except ZeroDivisionError:
            metrics['TPR'] = -1
        try:
            metrics['FNR'] = FN / (TP + FN)
        except ZeroDivisionError:
            metrics['FNR'] = -1
        try:
            metrics['TNR'] = TN / (TN + FP)
        except ZeroDivisionError:
            metrics['TNR'] = -1
        try:
            metrics['Precision'] = TP / (TP + FN)
        except ZeroDivisionError:
            metrics['Precision'] = -1
        try:
            # False discovery rate
            metrics['FDR'] = FP / (TP + FP)
        except ZeroDivisionError:
            metrics['FDR'] = -1
        try:
            # Negative Predictive Value
            metrics['NPV'] = TN / (TN + FN)
        except ZeroDivisionError:
            metrics['NPV'] = -1
        try:
            metrics['Accuracy'] = (TP + TN) / (TP + TN + FP + FN)
        except ZeroDivisionError:
            metrics['Accuracy'] = -1
        try:
            # Positive likelihood ratio
            metrics['PLR'] = metrics['TPR'] / metrics['FPR']
        except ZeroDivisionError:
            metrics['PLR'] = -1
        try:
            # Negative likelihood ratio
            metrics['NLR'] = metrics['FNR'] / metrics['TNR']
        except ZeroDivisionError:
            metrics['NLR'] = -1
        try:
            # Diagnostic odds ratio
            metrics['DOR'] = metrics['PLR'] / metrics['NLR']
        except ZeroDivisionError:
            metrics['DOR'] = -1
        return metrics

    def sum_up_errors(self, vector):
        """ Given a vector of values, sum up the errors """
        sum_errors = {}
        sum_errors['TP'] = 0.0
        sum_errors['TN'] = 0.0
        sum_errors['FN'] = 0.0
        sum_errors['FP'] = 0.0
        for i in vector:
            errors = i['Errors']
            sum_errors['TP'] += errors['TP']
            sum_errors['TN'] += errors['TN']
            sum_errors['FN'] += errors['FN']
            sum_errors['FP'] += errors['FP']
        return sum_errors

    def train(self, model_id_to_train, filter):
        """ Train the distance threshold of a model """
        self.construct_filter(filter)
        train_model = self.get_markov_model(model_id_to_train)
        print_info('Training model: {}'.format(train_model))
        print_info('With testing models:')
        # To store the training data
        thresholds_train = {}
        for test_model in self.get_markov_models():
            # Apply the filter and avoid training with itself
            try:
                test_model_id = test_model.get_id()
                train_model_id = train_model.get_id()
            except AttributeError:
                print_error('No such id available')
                return False
            if self.apply_filter(test_model) and test_model_id != train_model_id:
                # Store info about this particular test training. Later stored within the threshold vector
                # train_vector = [test model id, distance, N flow that matched, errors, errors metrics]
                train_vector = {}
                train_vector['ModelId'] = test_model_id
                print '\t', test_model
                # For each threshold to train
                # Now we go from 1.1 to 2
                exit_threshold_for = False
                for threshold in np.arange(1.1,2.1,0.1):
                    # Store the original matrix and prob for later
                    original_matrix = train_model.get_matrix()
                    original_self_prob = test_model.get_self_probability()
                    # For each test state
                    index = 0
                    while index < len(test_model.get_state()):
                        # Get the states so far
                        train_sequence = train_model.get_state()[0:index+1]
                        test_sequence = test_model.get_state()[0:index+1]
                        #print train_sequence
                        #print test_sequence
                        # Prob of the states so far
                        train_prob = float(train_model.compute_probability(train_sequence))
                        test_prob = float(train_model.compute_probability(test_sequence))
                        #print train_prob
                        #print test_prob
                        # Compute distance
                        if train_prob < test_prob:
                            try:
                                distance = train_prob / test_prob
                            except ZeroDivisionError:
                                distance = -1
                        elif train_prob > test_prob:
                            try:
                                distance = test_prob / train_prob
                            except ZeroDivisionError:
                                distance = -1
                        elif train_prob == test_prob:
                            distance = 1
                        # Is distance < threshold? We found a good match.
                        if index > 2 and distance < threshold and distance > 0:
                            # Compute the errors: TP, TN, FP, FN
                            #errors = self.compute_errors(train_model.get_label().get_name(), test_model.get_label().get_name())
                            train_label = train_model.get_label().get_name()
                            test_label = test_model.get_label().get_name()
                            errors = self.compute_errors(train_label, test_label, positive_label='Botnet')
                            print '\t\tTraining with threshold: {}. Distance: {}. Errors: {}'.format(threshold, distance, errors)
                            # Store the info
                            train_vector['Distance'] = distance
                            train_vector['IndexFlow'] = index
                            train_vector['Errors'] = errors
                            # Get the old vector for this threshold
                            try:
                                prev_threshold = thresholds_train[threshold]
                            except KeyError:
                                # First time for this threshold
                                thresholds_train[threshold] = []
                                prev_threshold = thresholds_train[threshold]
                            # Store this train vector in the threshold vectors
                            prev_threshold.append(train_vector)
                            thresholds_train[threshold] = prev_threshold
                            # Tell the threshold for to exit
                            exit_threshold_for = False
                            # Exit the test chain of state evaluation
                            break
                        # Next letter
                        index += 1
                        # Put a limit in the amount of letters by now. VERIFY THIS
                        if index > 100:
                            break
                    if exit_threshold_for:
                        break
        # Compute the error metrics for each threshold
        final_errors_metrics = {}
        for threshold in thresholds_train:
            #print 'Threshold: {}'.format(threshold)
            # Sum up together all the errors for this threshold
            sum_errors = self.sum_up_errors(thresholds_train[threshold])
            # Compute the metrics
            metrics = self.compute_error_metrics(sum_errors)
            final_errors_metrics[threshold] = metrics
            #print metrics

        sorted_metrics = sorted(final_errors_metrics.items(), key=lambda x: x[1], reverse=True)
        for threshold in sorted_metrics:
            print 'Threshold: {}'.format(threshold[0])
            print '\t',
            print threshold[1]

    # The run method runs every time that this command is used
    def run(self):
        # Register the structure in the database, so it is stored and use in the future. 
        if not __database__.has_structure(Group_of_Markov_Models_1().get_name()):
            print_info('The structure is not registered.')
            __database__.set_new_structure(Group_of_Markov_Models_1())
        else:
            main_dict = __database__.get_new_structure(Group_of_Markov_Models_1())
            self.set_main_dict(main_dict)

        # List general help. Don't modify.
        def help():
            self.log('info', self.description)

        # Run
        super(Group_of_Markov_Models_1, self).run()
        if self.args is None:
            return
        
        # Process the command line
        if self.args.list:
            self.list_markov_models(self.args.filter)
        elif self.args.generate:
            self.create_new_model(self.args.generate, self.args.numberofflows)
        elif self.args.printmatrix:
            self.print_matrix(self.args.printmatrix)
        elif self.args.simulate:
            self.simulate(self.args.simulate)
        elif self.args.delete:
            self.delete(self.args.delete)
        elif self.args.printstate:
            self.printstate(self.args.printstate)
        elif self.args.regenerate:
            self.regenerate(self.args.regenerate)
        elif self.args.train:
            self.train(int(self.args.train), self.args.filter)
        elif self.args.generateall:
            self.generate_all_models(self.args.numberofflows)
        else:
            print_error('At least one of the parameter is required in this module')
            self.usage()

__group_of_markov_models__ = Group_of_Markov_Models_1()
