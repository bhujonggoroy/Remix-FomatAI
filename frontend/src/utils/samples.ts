export interface AcademicSample {
  id: string;
  title: string;
  preset: 'academic' | 'research_paper' | 'exam' | 'study_notes' | 'textbook';
  description: string;
  rawText: string;
}

export const ACADEMIC_SAMPLES: AcademicSample[] = [
  {
    id: 'deep_learning_survey',
    title: 'Self-Supervised Representation Learning in High-Dimensional Manifolds',
    preset: 'research_paper',
    description: 'IEEE-format machine learning paper with mathematical derivations, tabular benchmarks, and APA citations.',
    rawText: `# Self-Supervised Representation Learning in High-Dimensional Manifolds

**Abstract**
Recent advances in self-supervised representation learning demonstrate competitive empirical performance against fully supervised regimes. However, the geometric convergence dynamics across non-convex latent manifolds remain incompletely characterized. In this study, we formalize the contrastive objective under spherical uniform distribution bounds and establish that latent representations achieve optimal separability when the projection metric satisfies Lipschitz continuity with constant $L \\le 1.25$. Our experimental evaluations across three benchmark datasets validate a 4.2% top-1 accuracy improvement alongside a 28% reduction in sample variance.

## 1. Introduction
High-dimensional visual representations often collapse into degenerate subspaces unless explicit regularization constraints are enforced. Contrastive objectives, such as InfoNCE, address this limitation by optimizing the mutual information lower bound between positive pairs while repelling negative distractors [1]. 

Let $\\mathcal{X} \\subset \\mathbb{R}^D$ denote the input observation space and $f_\\theta: \\mathcal{X} \\to \\mathbb{S}^{d-1}$ represent the deep neural encoder mapping inputs onto the unit hypersphere. The temperature-scaled objective is defined as:

$$\\mathcal{L}_{\\text{contrastive}} = -\\log \\frac{\\exp(f(x)^T f(x^+) / \\tau)}{\\exp(f(x)^T f(x^+) / \\tau) + \\sum_{k=1}^{K} \\exp(f(x)^T f(x_k^-) / \\tau)}$$

Where $\\tau > 0$ represents the temperature hyperparameter and $K$ denotes the negative batch cardinality.

## 2. Theoretical Formulation & Convergence
To evaluate empirical stability, we compute the sample variance $\\sigma^2$ across $N$ mini-batch projections:

$$\\sigma^2 = \\frac{1}{N} \\sum_{i=1}^{N} (z_i - \\bar{z})^2$$

Under stochastic gradient descent, parameter updates exhibit bounded asymptotic variance when learning rates satisfy $\\eta_t = \\eta_0 (1 + \\gamma t)^{-0.5}$.

## 3. Empirical Benchmark Evaluations
We conduct comparative benchmarks against representative state-of-the-art architectures using identical hardware environments.

| Model Architecture | Latent Dim ($d$) | Top-1 Accuracy (%) | Inference Latency (ms) | Training FLOPs |
| --- | --- | --- | --- | --- |
| ResNet-50 (Baseline) | 2048 | 76.4 | 14.2 | $4.1 \\times 10^9$ |
| ViT-Base / 16 | 768 | 81.8 | 22.6 | $17.6 \\times 10^9$ |
| FormatAI Contrastive | 512 | 84.6 | 11.8 | $3.4 \\times 10^9$ |
| Swin-Transformer V2 | 1024 | 83.9 | 28.4 | $21.2 \\times 10^9$ |

Table 1: Quantitative benchmark comparison on ImageNet-1k validation split after 300 pre-training epochs.

## 4. Discussion & Limitations
While contrastive representations demonstrate robust transferability across downstream tasks, downstream alignment is sensitive to data augmentation policies. Extreme cropping policies occasionally discard semantically discriminative features.

## References
[1] He, K., Fan, H., Wu, Y., Xie, S., & Girshick, R. (2020). Momentum contrast for unsupervised visual representation learning. *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition*, 9729-9738.
[2] Chen, T., Kornblith, S., Norouzi, M., & Hinton, G. (2020). A simple framework for contrastive learning of visual representations. *International Conference on Machine Learning*, 1597-1607.
[3] Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., & Sutskever, I. (2021). Learning transferable visual models from natural language supervision. *ICML 2021*, 8748-8763.`
  },
  {
    id: 'thermodynamics_exam',
    title: 'Advanced Thermodynamics & Statistical Mechanics — Midterm Examination',
    preset: 'exam',
    description: 'Structured academic exam with formula derivations, multi-part questions, and score distributions.',
    rawText: `# Department of Mechanical & Aerospace Engineering
## ENGR 402: Advanced Thermodynamics & Transport Phenomena
**Examination Duration:** 120 Minutes | **Total Marks:** 100

### Instructions to Candidates
1. Answer all four questions in the spaces provided.
2. Scientific calculators and standard property steam tables are permitted.
3. Show all intermediate steps; partial credit is awarded for clear derivation methodology.

---

### Question 1: Fundamental Thermodynamic Relations (25 Marks)
Consider an ideal monoatomic gas undergoing a reversible polytropic process where $P V^n = C$.

**(a)** Derive the general expression for work done $W_{12}$ during expansion from initial state $(P_1, V_1)$ to final state $(P_2, V_2)$ for cases where $n \\ne 1$. [8 Marks]

**(b)** Using the Maxwell relations, prove that the isothermal compressibility $\\kappa_T$ satisfies:

$$\\kappa_T = -\\frac{1}{V} \\left( \\frac{\\partial V}{\\partial P} \\right)_T = \\frac{1}{P}$$

**(c)** State the Clausius-Clapeyron relation and explain its physical significance in liquid-vapor phase coexistence boundaries. [9 Marks]

---

### Question 2: Entropy Generation in Steady-Flow Open Systems (25 Marks)
Superheated steam enters an adiabatic turbine at $P_1 = 6.0\\text{ MPa}$ and $T_1 = 450^\\circ\\text{C}$ with mass flow rate $\\dot{m} = 15.0\\text{ kg/s}$. The steam exhausts at $P_2 = 10\\text{ kPa}$ with a quality factor $x_2 = 0.92$.

| Parameter | State 1 (Inlet) | State 2 (Exit) | Units |
| --- | --- | --- | --- |
| Pressure ($P$) | 6.0 | 0.01 | MPa |
| Temperature ($T$) | 450.0 | 45.8 | $^\\circ$C |
| Specific Enthalpy ($h$) | 3302.9 | 2403.1 | kJ/kg |
| Specific Entropy ($s$) | 6.7219 | 7.5028 | kJ/(kg·K) |

**(a)** Calculate the actual electrical power output generated by the turbine in megawatts (MW). [10 Marks]
**(b)** Determine the rate of entropy generation $\\dot{S}_{\\text{gen}}$ within the turbine. [10 Marks]
**(c)** What is the isentropic efficiency $\\eta_t$ of the turbine expansion process? [5 Marks]`
  },
  {
    id: 'quantum_condensed_matter',
    title: 'Topological Invariants and Berry Curvature in Quantum Hall Systems',
    preset: 'academic',
    description: 'APA-style theoretical physics manuscript with inline equations and formal reference catalog.',
    rawText: `# Topological Invariants and Berry Curvature in Quantum Hall Systems

**Abstract**
We investigate the quantization of Hall conductance in two-dimensional electron gases subjected to strong perpendicular magnetic fields. By establishing the geometric connection between the Chern number $\\mathcal{C} \\in \\mathbb{Z}$ and the integration of Berry curvature $\\Omega(\\mathbf{k})$ over the first Brillouin zone, we demonstrate exact topological protection against weak disorder potentials.

## 1. Hamiltonian Formulation
The single-particle Hamiltonian for an electron of effective mass $m^*$ in a uniform magnetic field $\\mathbf{B} = B \\hat{\\mathbf{z}}$ is expressed through canonical momentum operators:

$$\\mathcal{H} = \\frac{1}{2m^*} \\left( \\mathbf{p} + e\\mathbf{A} \\right)^2 + V(\\mathbf{r})$$

Where $\\mathbf{A} = (-By, 0, 0)$ in the Landau gauge. The resulting energy eigenvalues collapse into degenerate discrete levels known as Landau levels:

$$E_n = \\hbar \\omega_c \\left( n + \\frac{1}{2} \\right), \\quad \\omega_c = \\frac{eB}{m^*}$$

## 2. Chern Invariant Calculation
The Hall conductivity $\\sigma_{xy}$ is quantized in integer multiples of the fundamental conductance quantum:

$$\\sigma_{xy} = \\frac{e^2}{h} \\mathcal{C}$$

Where the first Chern number $\\mathcal{C}$ is given by the surface integral of the Berry curvature tensor:

$$\\mathcal{C} = \\frac{1}{2\\pi} \\int_{\\text{BZ}} \\Omega_{xy}(\\mathbf{k}) \\, d^2\\mathbf{k}$$

## References
1. Thouless, D. J., Kohmoto, M., Nightingale, M. P., & den Nijs, M. (1982). Quantized Hall conductance in a two-dimensional periodic potential. *Physical Review Letters*, 49(6), 405.
2. Haldane, F. D. M. (1988). Model for a quantum Hall effect without Landau levels: Condensed-matter realization of the "parity anomaly". *Physical Review Letters*, 61(18), 2015.`
  }
];
