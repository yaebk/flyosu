# Data sources

Both files are public mirrors reachable without credentials. Neither is
redistributed in this repository; `make data` (or the commands below) fetches
them.

## `Connectivity_783.parquet` — 96 MB, 15,091,983 edges

FlyWire whole-brain connectome, release **v783**. Columns used:
`Presynaptic_ID`, `Postsynaptic_ID`, `Connectivity` (synapse count),
`Excitatory` (+1 / −1 from the predicted neurotransmitter).

```
curl -L -o data/Connectivity_783.parquet \
  https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/main/Connectivity_783.parquet
```

Mirrored from the code release of:

> Shiu, P.K., Sterne, G.R., Spiller, N. et al. **A Drosophila computational brain
> model reveals sensorimotor processing.** *Nature* 634, 210–219 (2024).

whose LIF parameters this project also uses as its starting point (see
`docs/CALIBRATION.md`). The underlying reconstruction is:

> Dorkenwald, S., Matsliah, A., Sterling, A.R. et al. **Neuronal wiring diagram of
> an adult brain.** *Nature* 634, 124–138 (2024).

## `neuron_annotations.tsv` — 32 MB, 139,248 neurons

Per-neuron annotations: `super_class`, `cell_class`, `cell_type`, `side`,
`pos_x/y/z`, `top_nt`, hemilineage, and more.

```
curl -L -o data/neuron_annotations.tsv \
  https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files/Supplemental_file1_neuron_annotations.tsv
```

From:

> Schlegel, P., Yin, Y., Bates, A.S. et al. **Whole-brain annotation and
> multi-connectome cell typing of Drosophila.** *Nature* 634, 139–152 (2024).

## What is *not* here

**The male CNS connectome** (Janelia/Google, ~166k neurons, brain + optic lobes
+ ventral nerve cord) that motivated the project. It is served from
`neuprint-cns.janelia.org`, which this sandbox's egress policy blocks; it also
needs an access token. FlyWire v783 is the closest public equivalent for the
brain and optic lobes.

**MANC**, the male adult nerve cord dataset. This is what would be needed to put
*real* leg motor neurons under the descending neurons — see the note about
T1L/T2L naming in `docs/CALIBRATION.md`. Same access constraint.

## Derived files

Built on first run and cached; safe to delete.

| File | What |
|---|---|
| `flywire783_cache.npz` | index-aligned edge arrays (pre, post, syn, sign) |
| `flywire783_ann.parquet` | annotations re-indexed to match |
| `models/fly_*.pkl` | calibrated networks, keyed by their settings |
