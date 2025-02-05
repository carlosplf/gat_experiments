import warnings
import torch
import numpy as np
import logging
import time
from torch_geometric.nn import GAE
from gat_model import gat_model
from sklearn.metrics.cluster import normalized_mutual_info_score
from sklearn.metrics.cluster import adjusted_rand_score
from utils import clustering_loss
from utils import csv_writer
from utils import plot_functions
from metrics import modularity
from centroids_finder import (
    random_seeds,
    fastgreedy,
    kcore,
    weighted_modularity,
    pagerank,
    kmeans,
    betweenness_centrality,
    weighted_betweenness_centrality,
    eigenvector_centrality,
    closeness_centrality
)
from centroids_finder import arguments_map


# Ignore torch FutureWarning messages
warnings.simplefilter(action="ignore", category=FutureWarning)


LEARNING_RATE = 0.0001  # Learning rate
LR_CHANGE_GAMMA = 0.5  # Multiplier for the Learning Rate
LR_CHANGE_EPOCHS = 20  # Interval to apply LR change
UPDATE_CLUSTERS_STEP_SIZE = 0.001  # Step size for clusters update
RECHOSE_CENTROIDS = True # If true, the algorithm will rechose the centroids when not improving loss
NOT_IMPROVING_LIMIT = 100 # Max number of iterations that loss is not improving


class GaeRunner:
    def __init__(
        self,
        epochs,
        data,
        b_edge_index,
        n_clusters,
        find_centroids_alg,
        c_loss_gama,
        p_interval,
        centroids_plot_file,
        clustering_plot_file,
        loss_log_file,
        metrics_log_file,
        hidden_layer,
        output_layer
    ):
        self.epochs = epochs
        self.data = data
        self.b_edge_index = b_edge_index
        self.n_clusters = n_clusters
        self.Q = 0
        self.P = 0
        self.clusters_centroids = None
        self.first_interaction = True
        self.communities = None
        self.mod_score = None
        self.find_centroids_alg = find_centroids_alg
        self.c_loss_gama = c_loss_gama
        self.p_interval = p_interval
        self.centroids_plot_file = centroids_plot_file
        self.clustering_plot_file = clustering_plot_file
        self.loss_log_file = loss_log_file
        self.metrics_log_file = metrics_log_file
        self.hidden_layer_size = hidden_layer
        self.output_layer_size = output_layer

    def __print_values(self):
        logging.info("C_LOSS_GAMMA: " + str(self.c_loss_gama))
        logging.info("LEARNING_RATE: " + str(LEARNING_RATE))
        logging.info("CALC_P_INTERVAL: " + str(self.p_interval))
        logging.info("LR_CHANGE_GAMMA: " + str(LR_CHANGE_GAMMA))
        logging.info("LR_CHANGE_EPOCHS: " + str(LR_CHANGE_EPOCHS))

    def run_training(self):
        # TODO: Refactor. Method is too big and complex.

        self.__print_values()

        # Check if CUDA is available and define the device to use.
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        logging.info("Running on " + str(device))

        in_channels, hidden_channels, out_channels = (
            self.data.x.shape[1],
            self.hidden_layer_size,
            self.output_layer_size
        )

        # 1 Hidden Layer GAT
        gae = GAE(gat_model.GATLayer(in_channels, hidden_channels, out_channels))

        # 2 Hidden Layer GAT
        # gae = GAE(gat_model.GAT2Layer(in_channels, [2048, 1024], out_channels))

        gae = gae.float()

        # Move everything to the right device
        gae = gae.to(device)
        self.data = self.data.to(device)
        self.b_edge_index = self.b_edge_index.to(device)

        optimizer = torch.optim.Adam(gae.parameters(), lr=LEARNING_RATE)  # pyright: ignore
        scheduler = torch.optim.lr_scheduler.StepLR(
            optimizer, step_size=LR_CHANGE_EPOCHS, gamma=LR_CHANGE_GAMMA
        )

        losses = []
        metrics_log = []
        att_tuple = [[]]
        loss_log = []
        best_nmi = {"epoch": 0, "value": 0.0}
        best_ari = {"epoch": 0, "value": 0.0}
        best_mod = {"epoch": 0, "value": 0.0}
        loss_not_improving_counter = 0
        Z = None
        loss = 0
        past_loss = 0
        chose_centroids = False

        for epoch in range(self.epochs):
            # If is the first iteration, chose centroids;
            # If loss not improving, chose centroids again;
            if epoch == 0 or loss_not_improving_counter == NOT_IMPROVING_LIMIT:
                if RECHOSE_CENTROIDS:
                    chose_centroids = True
                loss_not_improving_counter = 0

            # Save past loss to compare
            past_loss = loss

            loss, Z, att_tuple, c_loss, gae_loss = self.__train_network(
                gae, optimizer, epoch, scheduler, chose_centroids
            )

            chose_centroids = False

            # Check if loss is lowering
            if loss >= past_loss:
                loss_not_improving_counter += 1
            else:
                loss_not_improving_counter = 0

            logging.info("=> " + str(epoch) + " - Loss: " + str(loss))
            losses.append(loss)
            loss_log.append([epoch, loss, c_loss, gae_loss])

            logging.debug("GAE Loss: " + str(gae_loss))
            logging.debug("Clustering Loss (*10000): " + str(10000 * c_loss))

            r = []

            for line in self.Q:  # pyright: ignore
                r.append(np.argmax(line))

            mod = modularity.calculate(self.data, r)
            nmi = normalized_mutual_info_score(self.data.y.tolist(), r)
            ari = adjusted_rand_score(self.data.y.tolist(), r)
            metrics_log.append([epoch, mod, nmi, ari])

            logging.info("=> Modularity: " + str(mod))
            logging.info("=> NMI: " + str(nmi))
            logging.info("=> ARI: " + str(ari))

            if nmi > best_nmi["value"]:
                best_nmi["value"] = nmi
                best_nmi["epoch"] = epoch

            if ari > best_ari["value"]:
                best_ari["value"] = ari
                best_ari["epoch"] = epoch

            if mod > best_mod["value"]:
                best_mod["value"] = mod
                best_mod["epoch"] = epoch

            clustering_filename = (
                self.clustering_plot_file[:-4] + "_" + str(epoch) + ".png"
            )
            plot_functions.plot_clustering(
                Z.detach().cpu().numpy(), r, clustering_filename
            )

        logging.info(
            "=> Best Modularity score: "
            + str(best_mod["value"])
            + " at epoch "
            + str(best_mod["epoch"])
        )
        logging.info(
            "=> Best NMI score: "
            + str(best_nmi["value"])
            + " at epoch "
            + str(best_nmi["epoch"])
        )
        logging.info(
            "=> Best ARI score: "
            + str(best_ari["value"])
            + " at epoch "
            + str(best_ari["epoch"])
        )

        csv_writer.write_loss(loss_log, self.loss_log_file)
        csv_writer.write_metrics(metrics_log, self.metrics_log_file)

        return self.data, att_tuple

    def __train_network(self, gae, optimizer, epoch, scheduler, chose_centroids):
        gae.train()
        optimizer.zero_grad()

        att_tuple, Z = gae.encode(
            self.data.x.float(),
            self.b_edge_index.edge_index,
            self.b_edge_index.edge_attr,
        )

        if chose_centroids:
            self._find_centroids(Z)
            plot_functions.plot_centroids(
                Z, self.clusters_centroids, self.centroids_plot_file
            )

        if self.clusters_centroids is None:
            logging.error("Centroids must be chosen first. Aborting!")
            return None

        self.Q = clustering_loss.calculate_q(self.clusters_centroids, Z)

        if epoch % self.p_interval == 0:
            self.P = clustering_loss.calculate_p(self.Q)

        Lc, Q, P = clustering_loss.kl_div_loss(self.Q, self.P)

        gae_loss = gae.recon_loss(Z, self.data.edge_index)

        total_loss = gae_loss + self.c_loss_gama * Lc

        total_loss.backward()

        if self.first_interaction is False and Lc != 0:
            self.clusters_centroids = clustering_loss.update_clusters_centers(
                self.clusters_centroids, Q.grad, step_size=UPDATE_CLUSTERS_STEP_SIZE
            )

        optimizer.step()
        scheduler.step()

        self.first_interaction = False

        return float(total_loss), Z, att_tuple, float(Lc), float(gae_loss)

    def _find_centroids(self, Z):
        """
        Find the centroids using the selected algorithm.
        Args:
            Z: The matrix representing the embeddings AFTER the Encoding process.
        """
        start = time.time()

        if self.find_centroids_alg not in arguments_map.map:
            logging.error("FIND_CENTROIDS_ALG not known. Aborting...")
            return

        self.clusters_centroids = arguments_map.map[self.find_centroids_alg].select_centroids(
            data=self.data, Z=Z, n_clusters=self.n_clusters
        )

        done = time.time()
        msg = str("Finished centroids finding operation: " + str(done - start))
        logging.info(msg)

        log_msg = "Centroids: " + str(self.clusters_centroids)
        logging.debug(log_msg)
