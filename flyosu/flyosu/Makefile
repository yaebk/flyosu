FLYWIRE := https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/main
ANNOT   := https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files

.PHONY: all data cache check experiment figures clean-derived

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

experiment: cache
	python3 -m experiments.e1_sensorimotor

figures:
	python3 -m experiments.figures

clean-derived:
	rm -f data/flywire783_cache.npz data/flywire783_ann.parquet
	rm -rf data/models
