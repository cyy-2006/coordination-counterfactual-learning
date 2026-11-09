# Coordination Counterfactual Learning

Research code and paper sources for studying temporal counterfactual data augmentation in bimanual manipulation. The current implementation focuses on action-complete suffix delays in DexMimicGen `TwoArmThreading`, stable-success relabeling, paired sensitivity analysis, and robomimic-compatible policy datasets.

## Current status

- Full timing-intervention screening completed on 50 demonstrations (2 arms × 4 onset stages × 6 delays).
- Counterfactual HDF5 export, stable-positive / hard-negative masks, and closed-loop evaluation are implemented.
- Three-view image BC-RNN data loading and training have passed a local smoke test.
- Publication-scale visual policy training and multi-seed comparisons still require a GPU environment.

See [`paper/SUBMISSION_READINESS.md`](paper/SUBMISSION_READINESS.md) for the evidence gates and known limitations.

## Main entry points

- `local_runs/run_counterfactual_coordination.py`: execute timing interventions.
- `local_runs/analyze_coordination_results.py`: aggregate paired outcomes and confidence intervals.
- `local_runs/export_counterfactual_dataset.py`: export robomimic-style counterfactual datasets.
- `local_runs/make_hdf5_subset.py`: construct lightweight image subsets with HDF5 external links.
- `local_runs/make_bc_config.py`: generate reproducible state or image BC-RNN configs.
- `local_runs/evaluate_robomimic_policy.py`: closed-loop policy evaluation.

## Data

Large datasets, checkpoints, virtual environments, and generated results are intentionally excluded from Git. Download the official DexMimicGen data separately and place it under `local_runs/datasets/generated/`.

## Paper

The evolving manuscript is in `paper/`. Experimental placeholders are deliberately retained where multi-seed policy results are not yet available; software smoke tests are not presented as scientific results.

