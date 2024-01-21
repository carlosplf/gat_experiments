import networkx as nx
import torch
import numpy as np
import random
import argparse
from utils.utils import edges_to_edgeindex
from utils.utils import remove_min_weight_edges
from utils.graph_viewer import show_graph
from utils.graph_viewer import plot_weights
from utils.graph_creator import define_graph
from utils.graph_creator import create_from_dataset
from gat_model import gat_model
import torch_geometric.utils as utils
from torch_geometric.nn import GAE
from cora_dataset import planetoid_dataset


parser = argparse.ArgumentParser()
parser.add_argument("--dummy", action="store_true", help="Use a dummy smal graph for testing.")
parser.add_argument("--cora", action="store_true", help="Use the Cora Planetoid dataset.")
parser.add_argument("--epochs", type=int,
                    help="Define number of EPOCHS for training.",
                    default=100)


# Defining random seeds
random.seed(81)
np.random.seed(81)
torch.manual_seed(81)
torch.cuda.manual_seed(81)


def train_network(gae, optimizer, graph):
    gae.train()
    optimizer.zero_grad()

    att_tuple, H_L = gae.encode(graph.features.float(), graph.edge_index)

    # Decode por multiplicação pela transposta
    loss = gae.recon_loss(H_L, graph.edge_index)

    return float(loss), H_L, att_tuple


def run(epochs, dataset_to_use):

    if dataset_to_use == "cora":
        data = planetoid_dataset.download_dataset()
        G, communities = create_from_dataset(data)
        X = data.x
    elif dataset_to_use == "dummy":
        G, communities = define_graph()
        # Adding some features to the Graph
        X = torch.tensor(np.eye(18), dtype=torch.float)
    else:
        print("No dataset specified. Exiting...")

    # TODO: move this to the method that builds the Graph
    G.features = X

    for i in range(len(G.nodes())):
        G.nodes[i]['features'] = X[i]
        G.nodes[i]['label'] = communities[i]

    device = torch.device('cpu')

    dataset = utils.from_networkx(G)

    in_channels, hidden_channels, out_channels = len(dataset.features[0]), 8, 2

    gae = GAE(gat_model.GATLayer(in_channels, hidden_channels, out_channels))

    gae = gae.to(device)
    gae = gae.float()

    dataset = dataset.to(device)

    optimizer = torch.optim.Adam(gae.parameters(), lr=0.005)

    losses = []
    embs_list = []

    for epoch in range(epochs):
        loss, H_L, att_tuple = train_network(gae, optimizer, dataset)
        if epoch % 10 == 0:
            print("Loss:", loss)
        losses.append(loss)
        embs_list.append(H_L)

    # Add the Attention values to the original Graph edges
    weight = att_tuple[1]
    src = att_tuple[0][0]
    tgt = att_tuple[0][1]

    for i in range(len(weight)):
        G.add_edge(src[i].item(), tgt[i].item(), weight=weight[i].item())

    # Plot original graph with edge weights
    # plot_weights(G, communities)

    if dataset_to_use == "cora":
        G, communities = remove_edges(G, communities, num_edges_to_remove=6000)
    else:
        G, communities = remove_edges(G, communities)

    plot_weights(G, communities)


def remove_edges(G, communities, num_edges_to_remove=None):
    # Remove weights with small weights, based on the Attention values.

    print("Removing edges with small Attention values...")

    num_rem = 0
    if not num_edges_to_remove:
        while nx.number_connected_components(G.to_undirected()) != 3:
            G = remove_min_weight_edges(G)
            num_rem += 1
    else:
        for i in range(num_edges_to_remove):
            G = remove_min_weight_edges(G)
            num_rem += 1

    print("Removed", num_rem, "edges.")

    return G, communities


if __name__ == "__main__":
    dataset_to_use = "cora"
    args = parser.parse_args()

    if args.cora:
        print("Using Cora Planetoid dataset...")
        dataset_to_use = "cora"

    elif args.dummy:
        print("Using Dummy dataset...")
        dataset_to_use = "dummy"

    epochs = args.epochs

    print("Considering", epochs, "epochs...")

    run(epochs, dataset_to_use)
