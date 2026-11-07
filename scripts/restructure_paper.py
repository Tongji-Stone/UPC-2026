"""One-time structural migration; subsequent numerical refresh uses four_model_paper_values.py."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PAPER=ROOT/'paper'
archive=PAPER/'archive/pre_structure_main.tex';archive.parent.mkdir(exist_ok=True)
if not archive.exists():archive.write_text((PAPER/'main.tex').read_text(encoding='utf-8'),encoding='utf-8')
old=archive.read_text(encoding='utf-8')
header=old.split(r'\begin{document}')[0].replace('results/coupled_model/figures/','results/structure_v2/figures/').replace('coupled_results.tex','report_results.tex')
intro=old[old.index(r'\section{Introduction}'):old.index(r'\section{Preparation')]
intro=intro.replace('summarizes the coupled model and inverse problem: early positions determine candidate initial states, while later positions provide validation targets.',
    'summarizes the force models and inverse problem: early positions determine initial conditions and force corrections, while later positions provide validation targets. Section 2 states the assumptions and notation. Section 3 establishes the forces and equations. Section 4 compares forward and inverse predictions. Section 5 is reserved for sensitivity analysis. Section 6 discusses surface geometry, spin damping and wind, followed by conclusions and model evaluation in Sections 7 and 8.')
intro=intro.replace('Coupled translation--rotation model, initial-state fitting and goal-plane validation.','Three-force modeling, four-model comparison and goal-plane validation.')
geometry=old[old.index(r'\subsection{Geometry'):old.index(r'\subsection{State Variables')]
geometry+=r'''
The ball crosses the opening cleanly when its centre satisfies $|y|\leq3.66-R$ and $R\leq z\leq2.44-R$ at $x=X_g$. Ground contact occurs when the descending centre reaches $z=R$. These event definitions are used consistently for all four models.
'''
experiment=old[old.index('To assess whether a coefficient'):old.index(r'\paragraph{Reynolds-number applicability')]
experiment=experiment.replace('rather than judging it from a trajectory alone','at the same flow condition')
drag=old[old.index('The drag crisis is'):old.index(r'\subsection{Spin-Induced Lift}')]
lift=old[old.index('Rotation creates an asymmetric'):old.index(r'\subsection{Rotational Drag')]
lift=lift.replace('Both curves increase across the measured interval, but the formula is above all five measured values.',
    'Both curves increase across the measured interval; the formula is above all five measured values.')
lift=lift.replace('The coefficients should therefore be used with their ball type and measured range specified. In particular, large-$Sp$ extrapolation is not established by this experiment.',
    r'The comparison captures the growth of transverse force with spin and motivates the lift correction $\alpha_L$ in the inverse calculation.')
lift=lift.replace('Eq.~\\eqref{eq:cl-reference} is an intermediate reference, while Eq.~\\eqref{eq:cl-full} supplies the lift coefficient in the force model.',
    'Eq.~\\eqref{eq:cl-full} supplies the final lift coefficient in the force model.')
refs=old[old.index(r'\addcontentsline{toc}{section}{References}'):old.index(r'\newpage',old.index(r'\end{thebibliography}'))]
refs=refs.replace(r'\end{thebibliography}',r'''\bibitem{goff2009} J. E. Goff and M. J. Carr\'e, ``Trajectory analysis of a soccer ball,'' \emph{American Journal of Physics}, 77, 1020--1027, 2009. \url{https://doi.org/10.1119/1.3197187}.
\end{thebibliography}''').replace('Accessed 7 November 2026','Accessed 8 November 2026')
front=r'''
\begin{document}
\begin{center}
{\Large\bfseries Modeling and Validation of a Soccer Ball's Three-Dimensional Flight to the Goal\par}
\vspace{2mm}{\bfseries Problem B\par}
\vspace{3mm}{\bfseries Abstract\par}
\end{center}
Gravity bends a soccer ball's path, drag reduces its speed, and Magnus lift redirects a spinning ball. We formulate a three-dimensional model with these three forces and constant spin. Four models distinguish gravity alone, constant drag, constant drag and lift, and complete speed- and spin-dependent aerodynamic coefficients. Published Teamgeist relations reproduce the selected 2007 wind-tunnel drag and lift curves with coefficient RMSE values of 0.0113 and 0.0504.

Forward calculations are compared with controlled launch experiments, including a measured range of 21.9 m and four rotating-ball trajectory segments. The variable-coefficient model predicts a range of \ForwardMFourRange\ m in the nonspinning experiment. Inverse calculations estimate initial motion and nonnegative force corrections from two later positions, selecting corrections close to unity. Five recorded match flights provide subsequent positions for comparison. For the competition data, the variable-coefficient model predicts the goal-plane centre $(y,z)=(\ProblemY,\ProblemZ)$ m at $t=\ProblemTime$ s. A separate same-initial-state calculation quantifies rotational damping, while surface geometry and wind are discussed through published flow results and force estimates.

\noindent\textbf{Keywords:} Soccer ball, aerodynamic drag, Magnus effect, inverse prediction, trajectory comparison
\newpage\tableofcontents\newpage
'''
preparation=r'''
\section{Preparation of the Models}
\subsection{Assumptions}
\begin{itemize}
\item The ball is idealized as a rigid sphere of constant mass and radius, with cross-sectional area $A=\pi R^2$ and position at its centre, following common soccer-ball flight models \cite{maponi,bray,myers}. Empirical football coefficients represent the average aerodynamic effect of its surface. Section~\ref{sec:surface} discusses the effect of seams and asymmetric geometry.
\item Gravity, aerodynamic drag and spin-induced lift act during free flight \cite{maponi,bray}. Integration ends at ground contact or the selected goal plane.
\item The main model neglects aerodynamic torque, so its spin vector remains constant. Section~\ref{sec:rotation} examines this approximation by adding rotational damping to the same initial state.
\item Air density and viscosity are uniform, and the main calculation uses still air. Section~\ref{sec:wind} estimates how wind changes relative airflow and force magnitude.
\item The initial position and the next two early positions determine the inverse input. Subsequent positions from the DFL tracking records are used for comparison \cite{bassek,dataset}. The recorded vertical coordinate is treated as height in metres, consistently with the existing extraction.
\end{itemize}
\subsection{Notations}
\begin{table}[H]\centering\small
\caption{Principal quantities and competition reference values.}\label{tab:notations}
\begin{tabular}{p{.25\textwidth}p{.46\textwidth}p{.20\textwidth}}\toprule
Symbol & Meaning & Value or unit\\\midrule
$\boldsymbol r,\boldsymbol v$ & Ball-centre position and velocity & m; m/s\\
$\boldsymbol\omega,\omega$ & Spin vector and its magnitude & rad/s\\
$m,R,A$ & Mass, radius and frontal area & 0.43 kg; 0.11 m; $\pi R^2$\\
$g$ & Gravitational acceleration & 9.81 m/s$^2$\\
$\boldsymbol u,v$ & Air-relative velocity and its magnitude & m/s\\
$\rho$ & Air density & 1.2 kg/m$^3$\\
$\nu,\mu=\rho\nu$ & Kinematic and dynamic viscosity & $1.50\times10^{-5}$ m$^2$/s; Pa\,s\\
$Re,Sp$ & Reynolds number and spin parameter & dimensionless\\
$C_D,C_L$ & Drag and transverse lift coefficients & dimensionless\\
$\alpha_D,\alpha_L$ & Multiplicative force corrections & dimensionless\\
$\theta,\boldsymbol e_L$ & Spin--airflow angle and Magnus direction & rad; unit vector\\
$X_g$ & Local goal-plane coordinate & 11 m\\
$\boldsymbol Q,I_b$ & Damping torque and moment of inertia (Section 6) & N\,m; kg\,m$^2$\\\bottomrule
\end{tabular}\end{table}
The competition mass, radius and gravity follow the reference values of Maponi and Piombin \cite{maponi}; the air density follows Asai et al.\ \cite{asai2007}. The viscosity is a declared reference air setting, with $\mu=\rho\nu$. Controlled experiments use their reported mass, diameter and air properties.

\section{Model Establishment}
The same Newtonian equations generate all four models by selecting the included aerodynamic terms. We first describe the geometry, then connect the forces to the surrounding flow and ball rotation.
'''
force=r'''
\subsection{Force Analysis}
\subsubsection{Gravity}
Gravity supplies a constant downward force,
\begin{equation}\boldsymbol F_g=-mg\boldsymbol e_z,\end{equation}
where $\boldsymbol e_z$ is the upward vertical unit vector. It produces downward curvature even when all aerodynamic forces are removed.

\subsubsection{Aerodynamic Drag}\label{sec:drag}
A moving ball transfers momentum to the air in its wake. The mass flow through an area $A$ scales as $\rho Av$, and its velocity change scales as $v$, giving a force scale $\rho Av^2$. Writing the proportionality through dynamic pressure $q=\rho v^2/2$ gives the conventional drag expression \cite{goff2009,kiratidis2018},
\begin{equation}
\boldsymbol F_D=-\tfrac12\rho A\alpha_D C_D(Re,Sp)v\boldsymbol u,
\qquad \boldsymbol u=\boldsymbol v-\boldsymbol v_{\rm wind},\quad v=\|\boldsymbol u\|.
\label{eq:drag-force}\end{equation}
Its quantities have the following physical roles:
\begin{enumerate}
\item $\rho$ measures the amount of air displaced per unit volume. Uniform density is appropriate over the short flight; the reference value is $1.2$ kg/m$^3$ \cite{asai2007}.
\item $A=\pi R^2$ is the frontal area of the spherical ball. A larger radius intercepts more airflow.
\item $v^2$ sets the leading force scale, so fast motion produces stronger resistance. The negative direction makes drag oppose relative airflow. In the main still-air model, $\boldsymbol u=\boldsymbol v$.
\item $C_D$ represents the boundary layer, flow separation and wake. According to Asai et al.\ and Kiratidis and Leinweber \cite{asai2007,kiratidis2018}, speed and rotation are described by
\begin{equation}
Re=\frac{2Rv}{\nu},\qquad Sp=\frac{R\omega}{v},\qquad
\omega=\|\boldsymbol\omega\|,\quad\nu=\frac{\mu}{\rho}.
\label{eq:re-sp}\end{equation}
$Re$ compares inertial and viscous flow effects; $Sp$ compares rotating surface speed with airspeed. Spin remains constant in the main model, while $Sp$ rises as the ball slows.
\item $\alpha_D\geq0$ is the drag correction introduced for trajectory fitting. It equals one in forward calculations and is estimated from early positions in inverse calculations.
\end{enumerate}
\paragraph{Wind-tunnel evidence.}
'''
after_drag=r'''
\paragraph{Applicability to the competition flight.}
The final M4 trajectory has speeds of \ProblemSpeedMin--\ProblemSpeedMax\ m/s and Reynolds numbers of $(\ProblemReMin$--$\ProblemReMax)\times10^5$. Kiratidis and Leinweber's Teamgeist fit extends to 35 m/s \cite{kiratidis2018}, corresponding to $Re=5.13\times10^5$ for the reference air. The competition flight lies in this speed range and in the supercritical regime represented by the empirical relation, supporting its use here. The rotating Asai measurements span $Re=333793$--455172; the coefficient figures use the measured upper condition exactly. The inferred competition spin gives $Sp=\ProblemSpMin$--\ProblemSpMax; its higher values extend beyond the selected wind-tunnel spin interval.

\subsubsection{Magnus Lift}\label{sec:lift}
Rotation changes the flow on opposite sides of the ball, producing a pressure imbalance and a transverse Magnus force. Using the same dynamic-pressure scale as drag gives $F_L=qAC_L$ for transverse spin \cite{goff2009,kiratidis2018}. For a three-dimensional rotation axis, we adopt
\begin{equation}
\begin{aligned}
\boldsymbol F_L&=\tfrac12\rho A\alpha_L C_L(Re,Sp)v^2\sin\theta\,\boldsymbol e_L,\\
\boldsymbol e_L&=\frac{\boldsymbol\omega\times\boldsymbol u}{\|\boldsymbol\omega\times\boldsymbol u\|},\qquad
\sin\theta=\frac{\|\boldsymbol\omega\times\boldsymbol u\|}{\omega v}.
\end{aligned}\label{eq:lift-force}
\end{equation}
The angular projection extends the transverse empirical relation to an oblique spin axis. The force is zero at zero spin, zero airspeed or parallel spin and airflow.
\begin{enumerate}
\item $\rho$, $A$ and $v^2$ have the same dynamic-pressure and area meanings as in drag.
\item $\boldsymbol e_L$ is perpendicular to airflow, so lift redirects the ball. Topspin bends its path downward, backspin upward, and sidespin horizontally.
\item $\sin\theta$ measures the transverse part of rotation. It is one for perpendicular spin and airflow, and vanishes when they are parallel.
\item $C_L$ depends on rotation through $Sp$ and on the boundary-layer state through $Re$ and drag. The complete published relation below combines these influences.
\item $\alpha_L\geq0$ corrects the lift magnitude. It is one in forward prediction and joins the inverse unknowns when lift is included.
\end{enumerate}
\paragraph{Empirical relation and experimental comparison.}
'''
dynamics=r'''
\subsection{Dynamical Equations}\label{sec:dynamics}
Newton's second law and angular-momentum balance give
\begin{equation}
m\dot{\boldsymbol v}=\sum\boldsymbol F,\qquad
\frac{d\boldsymbol L}{dt}=\boldsymbol Q,\qquad\boldsymbol L=I_b\boldsymbol\omega.
\end{equation}
With zero applied torque and constant spherical inertia, the main model is
\begin{equation}
\left\{\begin{aligned}
\dot{\boldsymbol r}&=\boldsymbol v,\\
m\dot{\boldsymbol v}&=\boldsymbol F_g+\boldsymbol F_D+\boldsymbol F_L,\\
\dot{\boldsymbol\omega}&=\boldsymbol0.
\end{aligned}\right.\label{eq:motion}
\end{equation}
Its initial conditions are
\begin{equation}
\left\{\begin{aligned}
\boldsymbol r(0)&=\boldsymbol r_0,\\
\boldsymbol v(0)&=(v_{x0},v_{y0},v_{z0}),\\
\boldsymbol\omega(0)&=(\omega_{x0},\omega_{y0},\omega_{z0}).
\end{aligned}\right.\label{eq:initial}
\end{equation}
The observed initial position fixes the origin of the flight. The six velocity and spin components determine its initial motion. In still air, drag removes mechanical energy while Magnus lift does no work along the velocity; gravity converts kinetic and potential energy during flight.

\section{Model Solving}\label{sec:solving}
We compare increasing levels of aerodynamic description to identify which effects control the trajectory. Table~\ref{tab:models} defines the four models. Forward prediction uses measured or reconstructed launch conditions and unit force corrections. Inverse prediction uses two later positions to estimate the initial motion and force corrections, then propagates the fitted state to the goal.
\begin{table}[H]\centering\small
\caption{Four-model hierarchy. Gravity and constant spin are common to all models.}\label{tab:models}
\begin{tabular}{llll}\toprule
Model & Drag & Magnus lift & Inverse quantities\\\midrule
M1 & none & none & $\boldsymbol v_0$ (3)\\
M2 & constant $C_D^*$ & none & $\boldsymbol v_0,\alpha_D$ (4)\\
M3 & constant $C_D^*$ & constant $C_L^*$ & $\boldsymbol v_0$, spin axis, $\alpha_D,\alpha_L$ (7)\\
M4 & $C_D(Re,Sp)$ & $C_L(Re,Sp)$ & $\boldsymbol v_0,\boldsymbol\omega_0,\alpha_D,\alpha_L$ (8)\\\bottomrule
\end{tabular}\end{table}
For M2 and M3, the constants are evaluated once at the published reference point:
\begin{equation}
C_D^*=C_D(333793,0.19),\qquad C_L^*=C_L(333793,0.19)=1.15(0.19)^{0.83}.
\end{equation}
For the competition air and ball parameters, $C_D^*=\ReferenceCD$ and $C_L^*=\ReferenceCL$. All models use the same physical conditions within each comparison. M1 and M2 have no spin-dependent trajectory; M3 uses the spin-axis direction, and M4 uses both its direction and magnitude.

\subsection{Forward Prediction}\label{sec:forward}
\subsubsection{Prediction procedure and experimental conditions}
Given $\boldsymbol r_0$, $\boldsymbol v_0$ and $\boldsymbol\omega_0$, we set $\alpha_D=\alpha_L=1$ and integrate Eq.~\eqref{eq:motion} using an adaptive Runge--Kutta method. A root of $x-X_g$ locates the goal-plane crossing, and a descending root of $z-R$ locates ground contact. The calculation records speed and aerodynamic force magnitudes along the flight.

Goff and Carr\'e \cite{goff2009} launched a 32-panel soccer ball using independently driven wheels and recorded its motion with two high-speed cameras. The reported ball mass is 0.424 kg, diameter 0.218 m, air density 1.2 kg/m$^3$ and kinematic viscosity $1.54\times10^{-5}$ m$^2$/s. Rotation was measured by tracking marks on the ball. Ground markers provided landing ranges with a reported error of at most $\pm0.05$ m.

We use the nonspinning launch in their Figures 3, 4 and 11: approximate initial speed 18 m/s, elevation $22^\circ$, initial centre height about 0.85 m, and measured range 21.9 m. Four topspin launches from their Figure 14 provide additional spatial trajectory segments. Their published initial $Re$ and $Sp$ determine speed and spin; the first three digitized positions determine the initial spatial tangent. All five comparisons use red measurement-marker centres extracted from the vector PDF. The nonspinning early markers have 0.005 s spacing. Rotating segments are compared as $z(x)$ curves, matching their published spatial coordinates.

\subsubsection{Calculated trajectories and physical interpretation}
\ForwardRangeTable
\begin{figure}[H]\centering\includegraphics[width=\textwidth]{forward_range.pdf}
\caption{Forward prediction of Goff and Carr\'e's nonspinning experiment \cite{goff2009}. Left: calculated flight paths, digitized early positions and measured landing. Right: individual model ranges against the measured 21.9 m. M2 and M3 coincide because the initial spin is zero.}\label{fig:forward-range}\end{figure}
Gravity alone produces the longest range. Air resistance removes horizontal momentum and shortens flight distance. M2 and M3 use the same constant drag and predict identical nonspinning trajectories. M4 allows drag to change with the slowing airflow; its predicted range differs from the measured value by \ForwardMFourError\ m under the stated approximate launch conditions.

\ForwardSpinTable
\begin{figure}[H]\centering\includegraphics[width=\textwidth]{forward_topspin.pdf}
\caption{Four topspin launches digitized from Goff and Carr\'e \cite{goff2009}, Figure 14. Black points are measured marker centres; model curves use unit force corrections and the stated initial conditions. Each panel covers the published early spatial segment.}\label{fig:forward-spin}\end{figure}
Topspin produces downward Magnus force and increases the downward curvature. Table~\ref{tab:forward-spin} gives the RMSE of height at the measured horizontal positions. The ranking varies between launches: local direction estimates and the difference between the experimental 32-panel ball and the Teamgeist reference both influence the comparison. The rotating examples show where adding lift improves curvature and where a common empirical law leaves a visible difference.

\begin{figure}[H]\centering\includegraphics[width=\textwidth]{forward_dynamics.pdf}
\caption{Speed, drag and lift during the nonspinning and topspin-b forward examples. Force magnitudes are calculated from the shared equations. Constant aerodynamic coefficients still produce changing forces because dynamic pressure varies with speed.}\label{fig:forward-dynamics}\end{figure}
Figure~\ref{fig:forward-dynamics} shows the mechanism behind these paths. Drag is strongest when the ball is fast. Downward lift in a topspin flight changes its vertical motion and flight duration. In M4, changing speed also changes $Re$ and $Sp$, so the force evolution includes both dynamic-pressure and coefficient effects.

\subsection{Inverse Prediction}\label{sec:inverse}
\subsubsection{Early-position fitting and representative solution}
Let $\boldsymbol p_1$ and $\boldsymbol p_2$ be positions at $t_1,t_2$ after the known $\boldsymbol r_0$. The initial motion and applicable force corrections are chosen to minimize
\begin{equation}
J_r=\sum_{i=1}^{2}\|\boldsymbol r(t_i;\boldsymbol\eta)-\boldsymbol p_i\|^2,\qquad
\boldsymbol\eta_{\rm M4}=(\boldsymbol v_0,\boldsymbol\omega_0,\alpha_D,\alpha_L).
\end{equation}
The next selection criterion favors the published force scale,
\begin{equation}J_\alpha=(\alpha_D-1)^2+(\alpha_L-1)^2,\end{equation}
using only the terms present in each model. Among equal-quality M4 states, the smallest spin magnitude selects a representative state. Deterministic multi-start optimization applies these criteria in order. The position-error allowance is $6\times10^{-12}$ m$^2$, and the coefficient-objective allowance is $10^{-8}$; both are numerical selection tolerances. Initial guesses use measured displacement velocities and the literature's experimental spin rates. M3 represents its spin axis by two angles; its unit vector serves only to carry direction in Eq.~\eqref{eq:lift-force}.

\subsubsection{Comparison with recorded match flights}\label{sec:real-validation}
The Sportec Open DFL dataset associates optical tracking with match events \cite{bassek,dataset}. We retain the four previously selected flights from matches J03WOH and J03WQQ, and one recorded penalty. The four flights comprise two headers and two foot shots. Each inverse calculation uses only the first three available positions at 0, 0.04 and 0.08 s. Later tracking coordinates determine the observed crossing of the goal plane. The penalty segment begins with a slower first displacement before the faster recorded flight; its early coordinates are used as recorded.

\MatchResultsTable
\MatchAggregateTable
\begin{figure}[H]\centering\includegraphics[width=\textwidth]{inverse_errors.pdf}
\caption{Individual goal-plane prediction errors for the five recorded flights. Each marker is one event and model. Crosses below zero denote trajectories that provide no goal-plane prediction; their termination status appears in Table~\ref{tab:match-results}.}\label{fig:inverse-errors}\end{figure}
\MatchDiscussion
\begin{figure}[H]\centering\includegraphics[width=\textwidth]{penalty_prediction.pdf}
\caption{Inverse predictions for the recorded penalty, with all tracked positions shown. Only the first three positions enter the fit. The remaining positions display the observed continuation of the flight.}\label{fig:penalty}\end{figure}
The comparison links early acceleration to later flight. A large fitted drag correction produces rapid momentum loss, while lift corrections alter the direction of curvature. Changes in early recorded displacement therefore have a strong effect on the predicted endpoint. The event-level results show how each model responds to the actual recorded segment.

\subsubsection{Competition Problem B}\label{sec:example}
The supplied observations are
\begin{equation}
\begin{array}{c|ccc}
t\ (\mathrm{s})&x\ (\mathrm{m})&y\ (\mathrm{m})&z\ (\mathrm{m})\\\hline
0&0&0&0.11\\0.05&1.50&0.45&0.44\\0.10&2.96&0.86&0.74
\end{array}
\end{equation}
Applying the same inverse procedure gives Table~\ref{tab:problem}. The preferred M4 initial conditions are
\begin{equation}
\begin{aligned}
\boldsymbol v_0&=(\ProblemVX,\ProblemVY,\ProblemVZ)\ \mathrm{m/s},\\
\boldsymbol\omega_0&=(\ProblemWX,\ProblemWY,\ProblemWZ)\ \mathrm{rad/s},\\
(\alpha_D,\alpha_L)&=(\ProblemAlphaD,\ProblemAlphaL).
\end{aligned}
\end{equation}
\ProblemResultsTable
\begin{figure}[H]\centering\includegraphics[width=\textwidth]{problem_prediction.pdf}
\caption{Four inverse predictions for Problem B: horizontal path, vertical path and ball-centre positions at the goal plane. Black points are the supplied early observations.}\label{fig:problem-prediction}\end{figure}
M1 and M2 predict nearly the same horizontal direction because gravity and drag preserve the horizontal velocity ratio. Adding Magnus lift in M3 and M4 bends the ball laterally. The M4 goal-plane centre is $(\ProblemY,\ProblemZ)$ m at $\ProblemTime$ s and fits inside the goal with the ball-radius margin. Its early maximum coordinate residual is \ProblemResidual\ m. The inferred initial spin is \ProblemSpin\ rad/s; it supplies the aerodynamic curvature required by this representative fit.

\begin{figure}[H]\centering\includegraphics[width=\textwidth]{problem_dynamics.pdf}
\caption{Speed and aerodynamic force magnitudes for the four fitted Problem B models. All share the same observations, while their force assumptions produce different continuation paths.}\label{fig:problem-dynamics}\end{figure}

\section{Sensitivity Analysis}\label{sec:sensitivity}
\textit{To be completed.}

\section{Discussion of Other Factors}\label{sec:other}
The main model isolates gravity, drag and Magnus lift. We now examine the physical effects omitted from its geometry, spin evolution and ambient airflow.
\subsection{Asymmetric Surface Geometry}\label{sec:surface}
Paudel and Yan \cite{paudel} performed full-flight flow simulations using realistic football geometry and a smooth-sphere comparison. For launch speeds of 10, 15 and 20 m/s and spin rates of 31.5, 63 and 94.5 rad/s, their results show that seams and surface structure alter separation, wake dynamics and Magnus force. The smooth sphere produces greater lateral bending in their nine comparisons, and vertical flight-time differences become more visible at higher speed and rotation.

The spherical geometry in the present report describes the centre-of-mass motion and projected area. Its force coefficients come from football measurements, so the average surface influence enters through $C_D$ and $C_L$. Explicit panel orientation and asymmetric wake fluctuations provide a further level of description when lateral-force details are important. These published results support retaining football-specific coefficients in a spherical trajectory model.

\subsection{Rotation and Aerodynamic Damping}\label{sec:rotation}
Rotation changes Magnus force, so a declining spin can change the continuation of a curved shot. According to Grad et al.\ \cite{grad2026}, Supplementary Section 8.4, and the MuJoCo ellipsoid model \cite{mujoco381}, the spherical inertial and viscous damping torques are
\begin{equation}
\boldsymbol Q=-k_2\omega\boldsymbol\omega-k_1\boldsymbol\omega,
\quad k_2=\frac{8\pi}{15}\rho C_{\rm angular}R^5,\quad k_1=8\pi\mu R^3.
\label{eq:torque-dimensional}
\end{equation}
The quadratic term describes high-Reynolds-number angular drag; the linear term is viscous resistance. We use MuJoCo's documented reference value $C_{\rm angular}=1.5$ \cite{mujoco381}. Defining $q=\rho v^2/2$ and $C_{Q,v}=\|\boldsymbol Q\|/(qAR)$ gives
\begin{equation}
C_{Q,v}=\frac{16}{15}C_{\rm angular}Sp^2+\frac{32Sp}{Re},\qquad
C_{Q,\omega}=\frac{C_{Q,v}}{Sp^2}=\frac{16}{15}C_{\rm angular}+\frac{32}{Re\,Sp}.
\label{eq:cq-full}
\end{equation}
$C_{Q,\omega}$ uses rotating surface speed $R\omega$ in its reference pressure. The factor $1/Sp^2$ converts between the two normalizations. The viscous-to-inertial torque ratio is
\begin{equation}
\frac{Q_{\rm viscous}}{Q_{\rm inertial}}=
\frac{30}{C_{\rm angular}Re\,Sp}=
\frac{15\nu}{C_{\rm angular}R^2\omega}.
\end{equation}
It is \TorqueViscousRatio\ at the fitted competition launch, so the quadratic term dominates. Following the thin-shell inertia used by Maponi and Piombin \cite{maponi}, $I_b=2mR^2/3$. Adding the high-Reynolds-number torque gives
\begin{equation}
\left\{\begin{aligned}
\dot{\boldsymbol r}&=\boldsymbol v,\\
m\dot{\boldsymbol v}&=\boldsymbol F_g+\boldsymbol F_D+\boldsymbol F_L,\\
I_b\dot{\boldsymbol\omega}&=-k_2\omega\boldsymbol\omega.
\end{aligned}\right.\label{eq:motion-torque}
\end{equation}
The torque opposes spin and removes rotational energy. With this isolated quadratic law, $\omega(t)=\omega_0/[1+(k_2/I_b)\omega_0t]$, providing an integration check.

We repeat the M4 Problem B flight with exactly its fitted initial state and force corrections, first with constant spin and then with Eq.~\eqref{eq:motion-torque}. The state is held fixed so the comparison measures the damping effect directly.
\begin{figure}[H]\centering\includegraphics[width=\textwidth]{torque_comparison.pdf}
\caption{Same-initial-state comparison of constant spin and high-Reynolds-number rotational damping for Problem B. The documented angular-drag reference is 1.5, and the ball uses thin-shell inertia.}\label{fig:torque}\end{figure}
\TorqueResults

\subsection{Wind Speed and Force Estimates}\label{sec:wind}
Wind changes the airflow through $\boldsymbol u=\boldsymbol v-\boldsymbol v_{\rm wind}$ \cite{maponi}. At fixed coefficients, a wind speed $w$ along the flight direction changes the dynamic-pressure scale by
\begin{equation}
\frac{q_{\rm head}}{q_0}=(1+w/v)^2,\qquad
\frac{q_{\rm tail}}{q_0}=(1-w/v)^2,\qquad
\frac{q_{\rm cross}}{q_0}=1+(w/v)^2.
\end{equation}
Crosswind also rotates the airflow by $\arctan(w/v)$, changing the force direction. Table~\ref{tab:wind} evaluates these rough estimates at the fitted initial speed. The listed wind speeds are illustrative conditions for comparison.
\WindResultsTable
A 5\% limit on the headwind dynamic-pressure change corresponds to $w/v\leq\sqrt{1.05}-1$, or $w\leq\WindThreshold$ m/s at this launch. The still-air approximation is most suitable for indoor or weak-wind flight; stronger wind should enter through the relative-velocity calculation.

\section{Conclusions}
The three-force model connects soccer-ball flight to three distinct mechanisms: gravity produces downward curvature, drag removes momentum, and Magnus lift changes direction. The complete Teamgeist coefficient relations represent flow-state and spin changes, while the matched 2007 wind-tunnel comparison gives a closer reproduction for drag than for lift.

The controlled nonspinning example shows that including drag is essential for range prediction. Its M4 range is \ForwardMFourRange\ m against the published 21.9 m. The rotating trajectory segments display the downward curvature of topspin and variation in the accuracy of the common coefficient law. Recorded match comparisons show how early displacement and fitted force corrections affect subsequent prediction.

For Problem B, M4 gives $(y,z)=(\ProblemY,\ProblemZ)$ m at the goal plane. Magnus lift accounts for the marked horizontal difference from the gravity-only and drag-only predictions. The same-state rotational-damping comparison shifts the crossing by \TorqueDisplacement\ m under the documented torque setting. Wind estimates give the weak-wind condition for the still-air approximation. Sensitivity-analysis findings will be added after Section 5 is completed.

\section{Model Evaluation}
\subsection{Physical Interpretation and Computational Use}
The hierarchy makes the contribution of each force visible. The same dynamics handles forward calculation, early-position inversion and endpoint prediction. Force corrections provide a direct way to accommodate measured trajectory differences, and all experimental and numerical inputs are retained with their sources.
\subsection{Predictive Performance and Improvements}
The wind-tunnel comparisons, controlled launches and recorded match flights examine complementary aspects of the model: coefficient trends, curvature and range, and prediction from early observations. Their event-level errors identify where a common football coefficient law and an early trajectory segment give a useful continuation. Ball-specific aerodynamic measurements, directly measured spin and synchronized higher-rate positions would improve this connection. Explicit surface orientation, rotational damping and wind can be included as the application requires.
'''
appendix=r'''
\newpage\addcontentsline{toc}{section}{Reproduction Code}
\section*{Reproduction Code}
The accompanying project contains the frozen inputs, vector-marker extraction, four-model calculation, result tables and figure scripts. The following excerpts show the shared state equation and force evaluation. The inverse solver uses the same state derivative with the three selection criteria described in Section~\ref{sec:inverse}. Calculation and figure generation are separate commands, allowing plots to be refreshed from saved results.
\lstinputlisting[language=Python,firstline=177,lastline=181]{../src/football/physics/model.py}
\lstinputlisting[language=Python,firstline=217,lastline=237]{../src/football/physics/model.py}
\end{document}
'''
(PAPER/'main.tex').write_text(header+front+intro+preparation+geometry+force+experiment+drag+after_drag+lift+dynamics+refs+appendix,encoding='utf-8')
print('eight-section English report rebuilt; numerical inputs are separate')
