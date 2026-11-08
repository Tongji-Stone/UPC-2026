"""Maintain current bilingual section links and narrative around the shared calculations."""
from pathlib import Path
import re,shutil
ROOT=Path(__file__).resolve().parents[1]

INTRO_EN=r'''\subsection{Problem Restatement}
We study a ball travelling from the penalty mark to a goal 7.32 m wide and 2.44 m high, 11 m away. The motion and prediction problem can be organized into three stages:
\begin{enumerate}
\item \textbf{Ball--foot contact.} Contact establishes launch velocity and spin. These initial conditions determine the forward examples and the unknown quantities reconstructed in Section~\ref{sec:solving}.
\item \textbf{Airborne flight.} Gravity, drag and Magnus lift develop the trajectory according to the governing equations established in Section~\ref{sec:model}.
\item \textbf{Goal arrival and shot outcome.} The goal-plane crossing connects the flight to the shot result. Variation in initial motion, aerodynamic parameters and environmental conditions can produce a distribution of crossing locations; Section~\ref{sec:sensitivity} is reserved for that subsequent sensitivity and uncertainty analysis.
\end{enumerate}
We first compare prescribed kicks, then estimate initial states from three real penalties and compare predictions with later recorded positions. Figure~\ref{fig:workflow} summarizes this physical and computational sequence.
\begin{figure}[H]\centering
\resizebox{\textwidth}{!}{\input{assets/workflow_tikz.tex}}
\caption{Three-force modeling, prescribed forward scenarios and real-penalty inverse comparison.}\label{fig:workflow}
\end{figure}

'''
INTRO_ZH=r'''\subsection{问题重述}
本文研究足球从点球点飞向球门的运动，球门宽 7.32 m、高 2.44 m，距点球点 11 m。运动与预测问题可分为三个阶段：
\begin{enumerate}
\item \textbf{触球阶段。} 触球决定足球离脚后的初速度与自旋，这些初始条件构成第~\ref{sec:solving} 章正向算例的输入，也是逆向预测需要反演的未知量。
\item \textbf{空中飞行阶段。} 重力、空气阻力和马格努斯升力共同决定轨迹，其演化由第~\ref{sec:model} 章的控制方程描述。
\item \textbf{射门阶段。} 球门交点将飞行运动与射门结果联系起来。初始运动、气动参数和环境条件的变化可形成落点分布，第~\ref{sec:sensitivity} 章预留相应灵敏性与不确定性分析。
\end{enumerate}
下文先比较自设初始条件的不同踢法，再通过三次真实点球反演初始状态，并与后续实测位置对照。图~\ref{fig:workflow} 概述这一物理与计算过程。
\begin{figure}[H]\centering
\resizebox{\textwidth}{!}{\input{../paper/assets/workflow_tikz.tex}}
\caption{三力建模、自设初值正向情景与真实点球逆向对照。}\label{fig:workflow}
\end{figure}

'''
END_EN=r'''\section{Conclusions}
The model separates the mechanisms of gravity, drag and Magnus lift. Gravity produces downward curvature, drag reduces speed, and spin redirects the path. The complete Teamgeist relations connect coefficient changes to speed and rotation; the matched wind-tunnel comparison reproduces drag more closely than lift.

Five prescribed kick situations provide six initial states and 24 forward flights. The matched top- and backspin pair demonstrates the reversal of vertical Magnus force, while sidespin produces horizontal curvature. In the curved M4 example the goal crossing is $(\CurvedY,\CurvedZ)$ m at $\CurvedTime$ s. The same initial state is used to quantify angular damping, giving a crossing displacement of \TorqueDisplacement\ m under the cited reference setting.

Three actual penalties supply distinct early sampling sequences and held-out trajectories. Coordinate conversion places all three in the competition geometry. The 12 inverse outcomes report early residuals, continuation errors, goal crossings and ground termination separately, connecting the recorded motion to each force assumption. Section 5 remains reserved for sensitivity analysis and crossing-location distributions.

\section{Model Evaluation}
\subsection{Physical Interpretation and Reproduction}
The four-model hierarchy makes the role of each force visible under shared initial conditions. Forward and inverse calculations use the same state derivative and coefficient definitions. Original source coordinates, selected frames, transformed coordinates, numerical settings and candidate solutions are saved with the results.
\subsection{Prediction and Further Development}
The real-penalty comparison evaluates how early motion carries into the later path. Bound-active solutions and residuals identify the influence of the chosen coefficient scale and initial-state search. Ball-specific coefficients, direct spin measurements and higher-rate synchronized tracking would improve these connections. Rotational damping and wind can be included when their effect is relevant to the flight considered.
'''
END_ZH=r'''\section{小结}
模型分别呈现重力、阻力与马格努斯升力的作用：重力使路径向下弯曲，阻力降低速度，自旋改变运动方向。完整 Teamgeist 关系将系数变化与速度、自旋联系起来，同工况风洞对照中阻力的吻合程度高于升力。

五类自设踢法给出六组初始状态和 24 次正向飞行。成对上、下旋展示竖直马格努斯力的反转，侧旋产生水平弯曲。M4 弧线球在 $\CurvedTime$ s 到达球门，交点为 $(\CurvedY,\CurvedZ)$ m；同一初始状态也用于量化旋转阻尼，在所引参考设定下交点移动 \TorqueDisplacement\ m。

三次真实点球提供不同的早期采样序列及后续轨迹，坐标转换将三例统一到题目几何。12 组逆向结果分别报告早期残差、后续路径误差、球门交点和触地状态，将记录运动与受力假设联系起来。第五章继续预留灵敏性分析及落点分布研究。

\section{模型评价}
\subsection{物理解释与复现}
四模型体系在相同初始条件下展示各力的作用，正向与逆向计算采用同一状态导数和系数定义。原始坐标、选定源帧、转换坐标、数值设定与候选解均随结果保存。
\subsection{预测表现与后续改进}
真实点球对照考察早期运动如何影响后续路径，边界取值及残差体现系数尺度与初始状态搜索的作用。球型专用系数、直接自旋测量和高频同步追踪有助于改善预测；具体飞行还可按其影响程度纳入旋转阻尼与风。
'''

def main():
    # One canonical geometry and workflow, shared by both language editions.
    target=ROOT/'paper/assets/geometry.pdf'
    if not target.exists():shutil.copy2(ROOT/'results/paper_geometry/geometry.pdf',target)
    for lang,folder in [('en','paper'),('zh','_中文版')]:
        p=ROOT/folder/'main.tex';s=p.read_text(encoding='utf-8');chinese=lang=='zh'
        restate='问题重述' if chinese else 'Problem Restatement';prep='模型准备' if chinese else 'Preparation of the Models'
        a=s.index('\\subsection{'+restate+'}');b=s.index('\\section{'+prep+'}',a)
        s=s[:a]+(INTRO_ZH if chinese else INTRO_EN)+s[b:]
        model='模型建立' if chinese else 'Model Establishment'
        s=s.replace('\\section{'+model+'}','\\section{'+model+'}\\label{sec:model}',1) if r'\label{sec:model}' not in s else s
        # Replace the two input/time assumptions, keeping the other mechanical assumptions intact.
        name='基本假设' if chinese else 'Assumptions';a=s.index('\\subsection{'+name+'}')
        b=s.index(r'\end{itemize}',a);block=s[a:b];items=block.split(r'\item')
        if len(items)==9:
            items[1]=(r' \textbf{触球与建模起点。} 自设正向算例从离脚后的初始状态开始；实测反演以首个可用追踪帧定义 $t=0$，触球作用通过初始运动条件体现。' if chinese else
                r' \textbf{Contact and model start.} Prescribed examples begin just after contact. Real inversions define $t=0$ at the first available tracking frame; contact is represented through the initial motion.')+'\n'
            items[-1]=(r' \textbf{观测与未知量。} 真实点球的三个指定位置用于有界确定性反演，随后位置用于比较。Z 原值按米及球心高度解释。初速度、自旋和气动力修正的搜索范围在第四章列明；第五章预留这些未定量对落点分布的影响。' if chinese else
                r' \textbf{Observations and unknowns.} Three specified real-penalty positions enter a bounded deterministic fit, and subsequent positions supply the comparison. Released Z values are interpreted as metres and centre height. Section 4 states the search ranges for velocity, spin and force corrections; Section 5 is reserved for their effect on crossing distributions.')+'\n'
            s=s[:a]+r'\item'.join(items)+s[b:]
        # Local penalty-mark geometry is common to all calculations.
        geom='几何与球门平面' if chinese else 'Geometry and Goal Plane';force='受力分析' if chinese else 'Force Analysis'
        a=s.index('\\subsection{'+geom+'}');b=s.index('\\subsection{'+force+'}',a)
        image=re.search(r'\\begin\{figure\}.*?\\end\{figure\}',s[a:b],re.S)[0]
        opening=(r'局部坐标原点位于名义点球点，$x$ 朝向球门，$y$ 水平横向，$z$ 竖直向上。球门平面为 $x=11$ m，开口为 $-3.66\le y\le3.66$ m、$0\le z\le2.44$ m。实测球场中心坐标的转换见第~\ref{sec:inverse} 节。' if chinese else
            r'The local horizontal origin is the nominal penalty mark, with $x$ towards the goal, $y$ lateral and $z$ upward. The goal plane is $x=11$ m and the opening is $-3.66\le y\le3.66$ m, $0\le z\le2.44$ m. Section~\ref{sec:inverse} converts the measured pitch-centred coordinates.')
        ending=(r'当球心满足 $|y|\le3.66-R$、$R\le z\le2.44-R$ 时，足球可完整通过球门开口。下降球心到达 $z=R$ 时视为触地，所有模型统一采用此判据。' if chinese else
            r'A clean opening crossing requires $|y|\le3.66-R$ and $R\le z\le2.44-R$. Descending centre height $z=R$ defines ground contact. Every model uses these same event definitions.')
        s=s[:a]+'\\subsection{'+geom+'}\n'+opening+'\n'+image+'\n'+ending+'\n\n'+s[b:]
        for line in s.splitlines():
            if '\\ProblemSpeedMin' in line:
                replacement=(r'自设初速度为 14--27 m/s，对应 $Re=(\ForwardReMin$--$\ForwardReMax)\times10^5$，处于 Teamgeist 经验式覆盖的速度范围内。该关系描述转捩及超临界流动，最高参考速度为 35 m/s\cite{kiratidis2018}。以下风洞图固定在实测 $Re=455172$；逆向算例则逐步按其实际 $Re$、$Sp$ 更新系数。' if chinese else
                    r'The prescribed launch speeds are 14--27 m/s, giving $Re=(\ForwardReMin$--$\ForwardReMax)\times10^5$ within the speed range represented by the Teamgeist fit. The relation describes transition and supercritical flow up to the reference 35 m/s \cite{kiratidis2018}. The comparison figures below use measured $Re=455172$; inverse flights update the coefficients at their actual $Re$ and $Sp$.')
                s=s.replace(line,replacement)
        solving='模型求解' if chinese else 'Model Solving';sensitivity='灵敏性分析' if chinese else 'Sensitivity Analysis'
        if '\\section{'+solving+'}' in s:
            a=s.index('\\section{'+solving+'}');b=s.index('\\section{'+sensitivity+'}',a)
            s=s[:a]+r'\input{sections/model_solving.tex}'+'\n\n'+s[b:]
        # Change only the comparison reference in the retained torque/airflow discussion.
        lines=[]
        for line in s.splitlines():
            if (not chinese and line.startswith('We repeat the M4 Problem B flight')) or (chinese and line.startswith('保持 M4 题目算例')):
                line=(r'取第~\ref{sec:forward} 节的弧线球，初速度为 $(\CurvedVX,0,\CurvedVZ)$ m/s，自旋为 $(0,0,35)$ rad/s，气动力修正均为一。保持这些初始条件相同，比较恒定自旋与式~\eqref{eq:motion-torque} 的旋转阻尼。' if chinese else
                    r'Use the curved shot of Section~\ref{sec:forward}, with initial velocity $(\CurvedVX,0,\CurvedVZ)$ m/s, spin $(0,0,35)$ rad/s and unit force corrections. Holding this state fixed, we compare constant spin with Eq.~\eqref{eq:motion-torque}.')
            line=line.replace('at the fitted competition launch','at the prescribed curved-shot launch').replace('at the fitted initial speed','at the curved-shot launch speed')
            line=line.replace('Same-initial-state comparison of constant spin and high-Reynolds-number rotational damping for Problem B.','Same-initial-state comparison of constant spin and high-Reynolds-number rotational damping for the prescribed curved shot.')
            line=line.replace('在题目反演初始状态下','在自设弧线球初始状态下').replace('在反演初速度下','在弧线球初速度下').replace('题目 B 相同初始状态下','自设弧线球相同初始状态下')
            lines.append(line)
        s='\n'.join(lines)+'\n'
        conclusion='小结' if chinese else 'Conclusions';references='参考文献' if chinese else 'References'
        a=s.index('\\section{'+conclusion+'}');b=s.index('\\addcontentsline{toc}{section}{'+references+'}',a)
        s=s[:a]+(END_ZH if chinese else END_EN)+s[b:]
        abs_a=s.index(r'\end{center}')+len(r'\end{center}');abs_b=s.index(r'\noindent\textbf{',abs_a)
        abstract=(r'''重力、阻力与马格努斯升力共同决定足球的三维飞行。本文建立恒定自旋三力模型，比较仅重力、恒定阻力、恒定阻力与升力，以及完整变系数四类模型。第三章保留经验气动关系及同工况风洞对照。

五类自设踢法对应六组初始状态和 24 次正向飞行，用于分析速度、仰角与自旋方向的作用。三次真实比赛点球提供 39 个原始采样帧；坐标统一到点球点后，利用各例指定的三个位置完成 12 组有界反演，并与后续真实采样曲线比较。结果逐项报告拟合残差、后续误差、球门交点与触地状态。另用同一弧线球初始条件比较旋转阻尼，其球门交点位移为 \TorqueDisplacement\ m。第五章预留灵敏性与落点分布研究。''' if chinese else r'''Gravity, drag and Magnus lift govern a soccer ball's three-dimensional flight. We formulate a constant-spin model and compare gravity alone, constant drag, constant drag and lift, and complete variable coefficients. Empirical aerodynamic relations and a matched wind-tunnel comparison provide the coefficient basis.

Five prescribed kick situations give six initial states and 24 forward flights, illustrating the roles of speed, elevation and spin direction. Three actual match penalties provide 39 original sampled frames. After conversion to penalty-mark coordinates, three selected positions per event enter 12 bounded inversions, whose continuations are compared with later measured samples. Results report fitting residuals, held-out errors, crossings and ground termination individually. A separate same-state curved-shot calculation quantifies angular damping, shifting the crossing by \TorqueDisplacement\ m. Sensitivity and crossing-distribution analysis remain reserved for Section 5.''')
        s=s[:abs_a]+'\n'+abstract+'\n\n'+s[abs_b:]
        s=re.sub(r'\\graphicspath\{[^\n]*',lambda m:(r'\graphicspath{{../paper/aerodynamics/}{../paper/assets/}{../results/current_report/figures/}}' if chinese else r'\graphicspath{{aerodynamics/}{assets/}{../results/current_report/figures/}}'),s)
        if chinese:s=s.replace(r'\input{assets/workflow_tikz.tex}',r'\input{../paper/assets/workflow_tikz.tex}')
        paragraphs=s.splitlines()
        for i,line in enumerate(paragraphs):
            if line.startswith('The accompanying project') or line.startswith('随附项目包含'):
                paragraphs[i]=(r'随附项目保存原始点球 CSV、坐标转换、统一反演、预测结果和制图脚本。以下节选展示共享状态方程和受力计算，正文与程序采用同一组系数及边界设定。计算、制图和中英文数值表生成分别执行。' if chinese else
                    r'The project contains the original penalty CSV, coordinate conversion, shared inversion, prediction results and figure scripts. The excerpts show the common state equation and force evaluation. Paper and program use the same coefficients and bounds; computation, plotting and bilingual table generation are separate commands.')
        p.write_text('\n'.join(paragraphs)+'\n',encoding='utf-8')
    print('current bilingual narrative and section links updated')

if __name__=='__main__':main()
