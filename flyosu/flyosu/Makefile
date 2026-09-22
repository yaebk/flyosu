FLYWIRE := https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/main
ANNOT   := https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files

.PHONY: all data cache check check-play check-reservoir experiment experiment2 experiment3 experiment4 experiment5 experiment6 experiment7 figures figures2 figures3 figures4 figures5 figures6 figures7 play clean-derived

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

check-reservoir: cache
	python3 -m tests.test_reservoir

experiment: cache
	python3 -m experiments.e1_sensorimotor

# the fly plays: untrained on the curriculum + readout learning, real vs controls
experiment2: cache
	N_CTRL=3 N_LEARN=2 N_EPISODES=30 python3 -m experiments.e2_play

# annealed readout learning, real vs rewired, three conditions; plus radius sweep
experiment3: cache
	N_LEARN=4 N_EPISODES=30 python3 -m experiments.e3_learning
	N_SEEDS=6 python3 -m experiments.e3_stability

# recurrent gain vs untrained behaviour across 20 rewired graphs
experiment4: cache
	N_SEEDS=20 python3 -m experiments.e4_covariate

# closed-form (ridge) readouts of four sizes, real vs three control families
experiment5: cache
	N_CTRL=10 python3 -m experiments.e5_reservoir

experiment5-malecns:
	DATASET=malecns FAMILIES=rewired,retino N_CTRL=4 python3 -m experiments.e5_reservoir

# what predicts untrained play: probes, per-key thresholds, and the theta sweep
experiment6: cache
	N_SEEDS=20 python3 -m experiments.e6_timing
	PHASE=2 N_SEEDS=20 python3 -m experiments.e6_timing
	PHASE=3 N_SEEDS=20 python3 -m experiments.e6_timing

# the same comparison with the wiring rule chosen on the band
experiment7: cache
	N_SEEDS=20 python3 -m experiments.e7_wiring

figures:
	python3 -m experiments.figures

figures2:
	python3 -m experiments.figures_e2

figures3:
	python3 -m experiments.figures_e3

figures4:
	python3 -m experiments.figures_e4

figures5:
	python3 -m experiments.figures_e5
	DATASET=malecns python3 -m experiments.figures_e5

figures6:
	python3 -m experiments.figures_e6

figures7:
	python3 -m experiments.figures_e7

play: cache
	python3 run_play.py --stage 2

clean-derived:
	rm -f data/flywire783_cache.npz data/flywire783_ann.parquet
	rm -rf data/models
