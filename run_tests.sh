#!/bin/bash

FAIL=0

echo "Testing KMeans..."
echo "Starting KMeans batch tests."
python run.py --epochs 145 --find_centroids_alg KMeans -cl 10 2>kmeans_test_1.txt &
python run.py --epochs 145 --find_centroids_alg KMeans -cl 20 2>kmeans_test_2.txt &
python run.py --epochs 145 --find_centroids_alg KMeans -cl 30 2>kmeans_test_3.txt &
python run.py --epochs 145 --find_centroids_alg KMeans -cl 40 2>kmeans_test_4.txt &
python run.py --epochs 145 --find_centroids_alg KMeans -cl 50 2>kmeans_test_5.txt &
python run.py --epochs 145 --find_centroids_alg KMeans -cl 100 2>kmeans_test_6.txt &
echo "Done"

for job in $(jobs -p); do
  echo $job
  wait $job || let "FAIL+=1"
done

echo $FAIL

if [ "$FAIL" == "0" ]; then
  echo "Batch finished. No fails."
else
  echo "# of FAILS: ($FAIL)"
fi

FAIL=0

echo "Testing KCore..."
echo "Starting KCore batch tests."
python run.py --epochs 145 --find_centroids_alg KCore -cl 10 2>kcore_test_1.txt &
python run.py --epochs 145 --find_centroids_alg KCore -cl 20 2>kcore_test_2.txt &
python run.py --epochs 145 --find_centroids_alg KCore -cl 30 2>kcore_test_3.txt &
python run.py --epochs 145 --find_centroids_alg KCore -cl 40 2>kcore_test_4.txt &
python run.py --epochs 145 --find_centroids_alg KCore -cl 50 2>kcore_test_5.txt &
python run.py --epochs 145 --find_centroids_alg KCore -cl 100 2>kcore_test_6.txt &
echo "Done"

for job in $(jobs -p); do
  echo $job
  wait $job || let "FAIL+=1"
done

echo $FAIL

if [ "$FAIL" == "0" ]; then
  echo "Batch finished. No fails."
else
  echo "# of FAILS: ($FAIL)"
fi

FAIL=0

echo "Testing PageRank..."
echo "Starting KCore batch tests."
python run.py --epochs 145 --find_centroids_alg PageRank -cl 10 2>pagerank_test_1.txt &
python run.py --epochs 145 --find_centroids_alg PageRank -cl 20 2>pagerank_test_2.txt &
python run.py --epochs 145 --find_centroids_alg PageRank -cl 30 2>pagerank_test_3.txt &
python run.py --epochs 145 --find_centroids_alg PageRank -cl 40 2>pagerank_test_4.txt &
python run.py --epochs 145 --find_centroids_alg PageRank -cl 50 2>pagerank_test_5.txt &
python run.py --epochs 145 --find_centroids_alg PageRank -cl 100 2>pagerank_test_6.txt &
echo "Done"

for job in $(jobs -p); do
  echo $job
  wait $job || let "FAIL+=1"
done

echo $FAIL

if [ "$FAIL" == "0" ]; then
  echo "Batch finished. No fails."
else
  echo "# of FAILS: ($FAIL)"
fi