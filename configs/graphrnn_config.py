from torch import nn
from torch.optim import Adam
from torch.optim.lr_scheduler import MultiStepLR

from openchem.utils.graph import Attribute
from openchem.data.graph_data_layer import BFSGraphDataset
from openchem.models.GraphRNN import GraphRNNModel
from openchem.modules.embeddings.basic_embedding import Embedding
from openchem.modules.mlp.openchem_mlp import OpenChemMLP
from openchem.utils.utils import identity
from openchem.modules.gru_plain import GRUPlain


max_prev_nodes = 12
# this in Carbon original id in the Periodic Table
original_start_node_label = 6
# edge_relabel_map = {
#     0.: 0,
#     1.: 1,
#     1.5: 2,
#     2.: 3,
#     3.: 4
# }
# TODO: watch out for broken inverse_relabel_map in this case
edge_relabel_map = {
    0.: 0,
    1.: 1,
    1.5: 1,
    2.: 1,
    3.: 1
}
# node_relabel_map = {
#     0.: 0,
#     5.: 1,
#     6.: 1,
#     7.: 1,
#     8.: 1,
#     9.: 1,
#     14.: 1,
#     15.: 1,
#     16.: 1,
#     17.: 1,
#     33.: 1,
#     34.: 1,
#     35.: 1,
#     53.: 1,
# }


def get_atomic_attributes(atom):
    atomic_num = atom.GetAtomicNum()
    attr_dict = dict(atom_element=atomic_num)
    return attr_dict


node_attributes = dict(
    atom_element=Attribute('node', 'atom_element', one_hot=False),
)

train_dataset = BFSGraphDataset(
    get_atomic_attributes, node_attributes,
    './benchmark_datasets/logp_dataset/logP_labels.csv',
    delimiter=',', cols_to_read=[1, 2],
    random_order=True, max_prev_nodes=max_prev_nodes,
    original_start_node_label=original_start_node_label,
    edge_relabel_map=edge_relabel_map,
    # node_relabel_map=node_relabel_map,
)

num_edge_classes = train_dataset.num_edge_classes
num_node_classes = train_dataset.num_node_classes
node_relabel_map = train_dataset.node_relabel_map
inverse_node_relabel_map = train_dataset.inverse_node_relabel_map
max_num_nodes = train_dataset.max_num_nodes
start_node_label = train_dataset.start_node_label

edge_embedding_dim = 128

if num_edge_classes > 2:
    node_rnn_input_size = edge_embedding_dim * max_prev_nodes
    node_embedding_dim = 128
else:
    node_rnn_input_size = max_prev_nodes
    node_embedding_dim = max_prev_nodes
# TODO: maybe update node rnn input size to include previous predicted node label
if num_node_classes > 2:
    node_rnn_input_size += node_embedding_dim

node_rnn_hidden_size = 16


class DummyCriterion(object):
    def __call__(self, inp, out):
        return inp

    def cuda(self):
        return self


model = GraphRNNModel
model_params = {
    'task': 'graph_generation',
    'use_cuda': True,
    'random_seed': 5,
    'use_clip_grad': True,
    'max_grad_norm': 10.0,
    'batch_size': 32,
    'num_epochs': 3000,
    ########################################
    'logdir': './logs/graphrnn_log',
    'print_every': 1,
    'save_every': 5,
    'train_data_layer': train_dataset,
    'criterion': DummyCriterion(),

    # TODO: update these
    'eval_metrics': None,
    'val_data_layer': None,

    'optimizer': Adam,
    'optimizer_params': {
        'lr': 0.003,
        },
    'lr_scheduler': MultiStepLR,
    'lr_scheduler_params': {
        'milestones': [400, 1000],
        'gamma': 0.3
    },

    'num_node_classes': num_node_classes,
    'num_edge_classes': num_edge_classes,
    'max_num_nodes': max_num_nodes,
    'start_node_label': start_node_label,

    'EdgeEmbedding': Embedding,
    'edge_embedding_params': dict(
        num_embeddings=num_edge_classes,
        embedding_dim=edge_embedding_dim
    ),

    'NodeEmbedding': Embedding,
    'node_embedding_params': dict(
        num_embeddings=num_node_classes,
        embedding_dim=node_embedding_dim
    ),

    'NodeMLP': OpenChemMLP,
    'node_mlp_params': dict(
        input_size=node_rnn_hidden_size,
        n_layers=2,
        hidden_size=[64, num_node_classes],
        activation=[nn.ReLU(inplace=True), identity],
    ),

    # TODO: reconsider these params
    'NodeRNN': GRUPlain,
    'node_rnn_params': dict(
        input_size=node_rnn_input_size,
        embedding_size=64,
        hidden_size=128,
        num_layers=4,
        has_input=True,
        has_output=True,
        output_size=16
    ),

    'EdgeRNN': GRUPlain,
    'edge_rnn_params': dict(
        input_size=1,
        embedding_size=8,
        hidden_size=16,
        num_layers=4,
        has_input=True,
        has_output=True,
        output_size=num_edge_classes if num_edge_classes > 2 else 1
    )


}