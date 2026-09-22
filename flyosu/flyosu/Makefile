FLYWIRE := https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/main
ANNOT   := https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files

.PHONY: all data cache check check-play experiment experiment2 experiment3 figures figures2 figures3 play clean-derived

all: cache

data: data/Connectivity_783.parquet data/neuron_annotations.tsv

data/Connectivity_783.parquet:
	curl -fL -o $@ $(FLYWIRE)/Connectivity_783.parquet

data/neuron_annotations.tsv:
	curl -fL -o $@ $(ANNOT)/Supplemental_file1_neuron_annotations.tsv

cache: data
	python3 -m flyosu.connectome

check: cache
	python3 -m flyosu.retina
	python3 -m flyosu.subgraph
	python3 -m tests.test_pipeline

check-play: cache
	python3 -m tests.test_play

experiment: cache
	python3 -m experiments.e1_sensorimotor

# the fly plays: untrained on the curriculum + readout learning, real vs controls
experiment2: cache
	N_CTRL=3 N_LEARN=2 N_EPISODES=30 python3 -m experiments.e2_play

# annealed readout learning, real vs rewired, three conditions; plus radius sweep
experiment3: cache
	N_LEARN=4 N_EPISODES=30 python3 -m experiments.e3_learning
	N_SEEDS=6 python3 -m experiments.e3_stability

figures:
	python3 -m experiments.figures

figures2:
	python3 -m experiments.figures_e2

figures3:
	python3 -m experiments.figures_e3

play: cache
	python3 run_play.py --stage 2

clean-derived:
	rm -f data/flywire783_cache.npz data/flywire783_ann.parquet
	rm -rf data/models
