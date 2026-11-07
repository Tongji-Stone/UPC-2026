"""Editorial migration of the drag/lift discussion into quantity-led lists."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];paper=ROOT/'paper/main.tex'
s=paper.read_text(encoding='utf-8')
archive=ROOT/'paper/archive/20261108_before_bilingual_main.tex'
if not archive.exists():archive.write_text(s,encoding='utf-8')
if r'\item \textbf{Drag coefficient \boldmath$C_D(Re,Sp)$.}' in s:
    print('English aerodynamic lists already refined')
    raise SystemExit(0)
if r'\usepackage{capt-of}' not in s:s=s.replace(r'\usepackage{tikz}',r'\usepackage{capt-of}'+'\n'+r'\usepackage{tikz}')
start=s.index(r'\subsubsection{Aerodynamic Drag}')
end=s.index(r'\subsection{Dynamical Equations}')
old=s[start:end]
formula=old[old.index('The drag crisis is'):old.index('Figure~\\ref{fig:cd-comparison}')]
formula=formula.replace(r'\begin{table}[H]\centering',r'\par\smallskip\noindent\begin{minipage}{\linewidth}\centering')
formula=formula.replace(r'\caption{Teamgeist zero-spin',r'\captionof{table}{Teamgeist zero-spin')
formula=formula.replace(r'\end{tabular}\end{table}',r'\end{tabular}\end{minipage}\par\smallskip')
app=old[old.index('The final M4 trajectory'):old.index(r'\subsubsection{Magnus Lift}')].strip()
cl=old[old.index('Rotation creates an asymmetric'):old.index('Figure~\\ref{fig:cl-comparison}')]
new=r'''\subsubsection{Aerodynamic Drag}\label{sec:drag}
A moving ball transfers momentum to the air in its wake. The mass flow through area $A$ scales as $\rho Av$, and the velocity change scales as $v$, giving a force scale $\rho Av^2$. Introducing dynamic pressure $q=\rho v^2/2$ gives the conventional drag expression \cite{goff2009,kiratidis2018},
\begin{equation}
\boldsymbol F_D=-\tfrac12\rho A\alpha_D C_D(Re,Sp)v\boldsymbol u,
\qquad \boldsymbol u=\boldsymbol v-\boldsymbol v_{\rm wind},\quad v=\|\boldsymbol u\|.
\label{eq:drag-force}\end{equation}
Its quantities have the following physical roles:
\begin{enumerate}
\item \textbf{Air density \boldmath$\rho$.} The density measures air mass per unit volume. We use the uniform reference value $1.2$ kg/m$^3$ reported by Asai et al.\ \cite{asai2007}.
\item \textbf{Projected area \boldmath$A=\pi R^2$.} A larger radius intercepts more airflow; the spherical geometry fixes this area throughout flight.
\item \textbf{Relative speed and direction \boldmath$v,\boldsymbol u$.} The quadratic speed dependence gives stronger resistance at higher speed, and the negative direction opposes airflow. The still-air main model has $\boldsymbol u=\boldsymbol v$.
\item \textbf{Drag coefficient \boldmath$C_D(Re,Sp)$.} The coefficient represents boundary-layer transition, separation and wake formation. Following Asai et al.\ and Kiratidis and Leinweber \cite{asai2007,kiratidis2018}, we define
\begin{equation}
Re=\frac{2Rv}{\nu},\qquad Sp=\frac{R\omega}{v},\qquad
\omega=\|\boldsymbol\omega\|,\quad\nu=\frac{\mu}{\rho}.
\label{eq:re-sp}\end{equation}
$Re$ compares inertial and viscous flow effects; $Sp$ compares rotating surface speed with airspeed. Constant spin makes $Sp$ rise as the ball slows.

'''+formula+'\n'+app+r'''
\item \textbf{Drag correction \boldmath$\alpha_D\geq0$.} This dimensionless multiplier equals one in forward calculations and is estimated from early positions in inverse calculations.
\end{enumerate}
\paragraph{Comparison with published wind-tunnel data.}
Asai et al.\ \cite{asai2007} measured soccer-ball forces in Tokai University's low-speed recirculating wind tunnel using a six-component balance ($1.5\times1$ m test section; about 1\% turbulence). We use their spinning full-size Teamgeist FRP replica: $R=0.11$ m, $\rho=1.2$ kg/m$^3$, airspeed 22--30 m/s and spin 2--10 rev/s. Five points per coefficient are digitized from their Figures 8 and 9 at $Re=455172$ (about 30 m/s); the reported side force $C_S$ represents transverse Magnus lift here. The speed--Re correspondence gives $\nu\simeq1.45\times10^{-5}$ m$^2$/s for this matched comparison.

Figure~\ref{fig:cd-comparison} reproduces the increase of drag with $Sp$: the coefficient MAE is 0.00985 and RMSE is 0.01127. Both curves use the same experimental condition and measured spin interval.
\begin{figure}[H]\centering
\includegraphics[width=4.7in]{cd_comparison.pdf}
\caption{Teamgeist drag at $Re=455172$: the complete empirical relation \cite{kiratidis2018} and five digitized Asai measurements \cite{asai2007}, Figure 8.}\label{fig:cd-comparison}
\end{figure}

\subsubsection{Magnus Lift}\label{sec:lift}
Rotation changes the flow on opposite sides of the ball and creates a transverse pressure force. Using the drag dynamic-pressure scale gives $F_L=qAC_L$ for transverse spin \cite{goff2009,kiratidis2018}. For a three-dimensional spin axis, we adopt
\begin{equation}
\begin{aligned}
\boldsymbol F_L&=\tfrac12\rho A\alpha_L C_L(Re,Sp)v^2\sin\theta\,\boldsymbol e_L,\\
\boldsymbol e_L&=\frac{\boldsymbol\omega\times\boldsymbol u}{\|\boldsymbol\omega\times\boldsymbol u\|},\qquad
\sin\theta=\frac{\|\boldsymbol\omega\times\boldsymbol u\|}{\omega v}.
\end{aligned}\label{eq:lift-force}
\end{equation}
Lift is zero for zero spin, zero airspeed or parallel spin and airflow.
\begin{enumerate}
\item \textbf{Dynamic-pressure and area scale \boldmath$\rho Av^2/2$.} Density, projected area and speed have the same meanings as in the drag force.
\item \textbf{Magnus direction \boldmath$\boldsymbol e_L$.} This unit vector is perpendicular to airflow. Topspin bends the path downward, backspin upward, and sidespin horizontally.
\item \textbf{Angular projection \boldmath$\sin\theta$.} The transverse component is one for perpendicular spin and airflow and vanishes for parallel directions. This projection extends the transverse empirical law to an oblique spin axis.
\item \textbf{Lift coefficient \boldmath$C_L(Re,Sp)$.} Rotation and boundary-layer state jointly determine lift.

'''+cl+r'''
\item \textbf{Lift correction \boldmath$\alpha_L\geq0$.} This dimensionless multiplier is one in forward prediction and is fitted to early positions when inverse prediction includes lift.
\end{enumerate}
\paragraph{Comparison with published wind-tunnel data.}
Figure~\ref{fig:cl-comparison} uses the same Asai experiment and flow condition. The complete relation reproduces increasing lift with $Sp$ and lies above all five measured values: MAE 0.04505, RMSE 0.05040 and maximum difference 0.07325. This larger discrepancy motivates the inverse lift correction $\alpha_L$.
\begin{figure}[H]\centering
\includegraphics[width=4.7in]{cl_comparison.pdf}
\caption{Teamgeist transverse lift at $Re=455172$: the complete empirical relation \cite{kiratidis2018} and five digitized Asai side-force measurements \cite{asai2007}, Figure 9.}\label{fig:cl-comparison}
\end{figure}

'''
paper.write_text(s[:start]+new+s[end:],encoding='utf-8')
wf=ROOT/'paper/assets/workflow_tikz.tex';s=wf.read_text(encoding='utf-8')
s=s.replace(r'\path[fill=wfGreen!80!wfInk,rounded corners=6pt] (0.86,9.28) rectangle (5.89,9.83);'+'\n'+r'\node[wfprior,font=\fontsize{12}{13.5}\selectfont] at (3.375,9.55)'+'\n'+r'  {gravity $\cdot$ drag $\cdot$ Magnus lift};','')
wf.write_text(s,encoding='utf-8')
print('force lists reorganized; wind-tunnel discussion shortened; workflow tag removed')
