# Published coefficient laws and wind-tunnel comparison

These files reproduce the Teamgeist drag and lift relations of Kiratidis and
Leinweber (2018), Eqs. (5), (7)--(9), Table 1, and compare them with digitized
measurements from Asai et al. (2007), Figures 8 and 9. No trajectory integration
is performed, and no existing simulation code is imported or modified.

## Purpose and comparison conditions

Each figure answers one question: how closely does the published coefficient
law reproduce the measured spin dependence at a fixed flow condition?
Both comparisons use the spinning Teamgeist FRP replica, radius 0.11 m,
Re = 455172, airspeed approximately 30 m/s and air density 1.2 kg/m³.
The original experiment's wind-speed/Re correspondence reconstructs
nu = 1.450001318e-5 m²/s. This is a conversion inferred from the figure legend,
not a viscosity reported by the experiment. The same viscosity is used to
evaluate the CL reference anchor at Re = 333793, Sp = 0.19.

The original side-force symbol Cs in Figure 9 is interpreted as Magnus lift
under transverse spin. The data reproduce published markers, not laboratory
raw records. The coefficient model draws on the same literature dataset;
the reported errors measure reproduction rather than independent validation.

## Reproduction

Requires Python 3.10+; the plotting step also requires Matplotlib and NumPy.
From the repository root:

```powershell
python paper/aerodynamics/compute_comparison.py
python paper/aerodynamics/plot_comparison.py
```

The computation uses the Python standard library. The plot reads its saved
CSVs without recalculating coefficients. Both scripts resolve paths relative
to their own location and can be run from any working directory. No random
sampling is used.

## Data and outputs

- `data/asai2007_digitized.csv`: the unchanged 110-point publication-derived
  source table; the two comparisons select five Teamgeist points each.
- `data/digitization_calibration.json`: original PDF hash, marker locations,
  coordinate conversions and graphical reading bounds.
- `data/source_provenance.json`: archived provenance of the wider source study;
  its other listed materials are references, not runtime dependencies.
- `data/comparison_points.csv`: the ten selected measurements, formula values,
  residuals, source point IDs and graphical reading bounds.
- `data/formula_curves.csv`: 401 formula samples per coefficient, restricted to
  that coefficient's measured Sp interval.
- `data/comparison_summary.json`: physical conditions, model parameters,
  normalization checks and error metrics at measured abscissae.
- `data/figure_audit.json`: verifies exactly two curves per plot.
- `cd_comparison` and `cl_comparison`: vector PDF, editable SVG and 300 DPI PNG.

The figures are 5.8 × 3.35 inches, matching their size in the paper. Blue solid
lines show the full published formulas; orange dashed lines with open circles
connect measured positions. There are no other curves or shaded regions.
Times New Roman, different line styles and open markers make the two series
distinguishable in colour and grayscale. No statistical error bands are drawn:
the available digitization bounds are not experimental confidence intervals.

For the selected five points, CD MAE = 0.00984688 and RMSE = 0.01127174;
CL MAE = 0.04505163 and RMSE = 0.05039562. CL overpredicts all five points.

## Sources

1. Asai et al. (2007), *Fundamental aerodynamics of the soccer ball*,
   [DOI](https://doi.org/10.1007/BF02844207), Figures 8 and 9, pp. 102--106.
2. Kiratidis and Leinweber (2018), *An aerodynamic analysis of recent FIFA World
   Cup balls*, [version used](https://arxiv.org/abs/1710.02784v2),
   [journal DOI](https://doi.org/10.1088/1361-6404/aaa888).
3. Grad et al. (2026), *Physics-Based 3D Ball Trajectory Reconstruction from
   Monocular Soccer Video: A Multi-Model Benchmark*, supplementary Section 8.4,
   [project](https://lukaszgrad.github.io/soccer-ball3d/).
4. [MuJoCo 3.8.1 source](https://github.com/google-deepmind/mujoco/blob/3.8.1/src/engine/engine_passive.c),
   spherical specialization of the ellipsoid-fluid torque.

## Scope of the numerical results in the paper

The paper's trajectories now use the same complete CD/CL laws with evolving spin
and the sourced spherical torque closure. Their results are stored separately in
`results/coupled_model/`; the primary case requires spin extrapolation, which is
reported explicitly. These two coefficient-comparison plots retain their matched
experimental Re and viscosity setting and their original digitized measurements.

The preserved-file hash list in this folder describes the pre-coupling snapshot, not the current source. Current program/results verification is in `results/coupled_model/verification.json`.
