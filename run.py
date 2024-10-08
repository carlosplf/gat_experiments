import argparse
import logging
from runners import gae_runner
from utils.graph_creator import get_planetoid_dataset
from utils.b_matrix import BMatrix


parser = argparse.ArgumentParser()

parser.add_argument(
    "--epochs", type=int, help="Define number of EPOCHS for training.", default=10
)
parser.add_argument("-d", "--debug", action="store_true")
parser.add_argument(
    "-fa",
    "--find_centroids_alg",
    type=str,
    help="Define the method to find \
        centroids. Options: KMeans, FastGreedy.",
    default="KMeans",
)
parser.add_argument(
    "-ds",
    "--dataset_name",
    type=str,
    help="Define the dataset to use.",
    default="Cora",
)
parser.add_argument(
    "-log",
    "--loss_log_file",
    type=str,
    help="Define the CSV file name to \
        save loss logs.",
    default="loss_log.csv",
)
parser.add_argument(
    "-cl",
    "--c_loss_gama",
    type=int,
    help="Define the multiplier for Clustering Loss.",
    default=20,
)
parser.add_argument(
    "-pi",
    "--p_interval",
    type=int,
    help="Define the interval for calculating P.",
    default=10,
)
parser.add_argument(
    "-cf",
    "--centroids_plot_file",
    type=str,
    help="Define the PNG file name to \
        save plot image.",
    default="centroids_plot.png",
)


def run(
    epochs,
    find_centroids_alg,
    loss_log_file,
    c_loss_gama,
    p_interval,
    centroids_plot_file,
    dataset_name,
):
    dataset = get_planetoid_dataset(name=dataset_name)

    data = dataset[0]
    num_classes = dataset.num_classes
    num_nodes = len(data.x)  # pyright: ignore

    logging.info("Number of nodes: " + str(num_nodes))
    logging.info("Number of classes: " + str(num_classes))

    b_matrix = BMatrix(data)

    logging.debug("B Matrix:")
    logging.debug(str(b_matrix))

    b_matrix.calc_t_order_neighbors(data, t=2)
    b_matrix.create_edge_index()

    runner = gae_runner.GaeRunner(
        epochs=epochs,
        data=data,
        b_edge_index=b_matrix.edge_index,
        n_clusters=num_classes,
        find_centroids_alg=find_centroids_alg,
        c_loss_gama=c_loss_gama,
        p_interval=p_interval,
        centroids_plot_file=centroids_plot_file,
        loss_log_file=loss_log_file,
    )

    data, att_tuple = runner.run_training()

    logging.debug("Attention values: " + str(att_tuple))

    return True


if __name__ == "__main__":
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    epochs = args.epochs
    c_loss_gama = args.c_loss_gama
    p_interval = args.p_interval
    find_centroids_alg = args.find_centroids_alg
    loss_log_file = args.loss_log_file
    centroids_plot_file = args.centroids_plot_file
    dataset_name = args.dataset_name

    logging.info("Chosen dataset: " + str(dataset_name))

    logging.info("Considering %s epochs", epochs)

    run(
        epochs,
        find_centroids_alg,
        loss_log_file,
        c_loss_gama,
        p_interval,
        centroids_plot_file,
        dataset_name,
    )
