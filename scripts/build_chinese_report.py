"""Translate the edited English report; preserve equations, results and English figures."""
from pathlib import Path
import json,re,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];ZH=ROOT/'_中文版'
# Paragraph numbers refer to the English editorial revision made by refine_aero_sections.py.
P={
28:r'''重力使足球轨迹向下弯曲，空气阻力降低飞行速度，马格努斯升力改变旋转足球的运动方向。本文建立包含这三种力、保持自旋恒定的三维模型，并比较四种模型：仅考虑重力、加入恒定阻力系数、采用恒定阻力与升力系数，以及采用随速度和自旋变化的完整经验系数。已发表的 Teamgeist 经验关系与所选 2007 年风洞数据对照时，阻力和升力系数的均方根误差分别为 0.0113 和 0.0504。''',
30:r'''正向计算与受控发射实验对照，实验包括一组实测射程为 21.9 m 的无旋转飞行和四组旋转足球轨迹片段。变系数模型对无旋转实验的预测射程为 \ForwardMFourRange\ m。逆向计算利用两个后续时刻的位置反演初始运动状态与非负气动力修正系数，并优先选择接近单位修正的解。五组比赛飞行记录提供后续位置用于比较。对于题目给定数据，变系数模型预测球心在 $t=\ProblemTime$ s 到达球门平面，交点为 $(y,z)=(\ProblemY,\ProblemZ)$ m。另以相同初始条件量化旋转阻尼的影响，并结合已发表的流动结果和气动力估算讨论表面几何与风的作用。''',
32:r'''\noindent\textbf{关键词：}足球；空气阻力；马格努斯效应；逆向预测；轨迹对照''',
36:r'''足球踢出后的轨迹通常会发生弯曲。重力使轨迹向下弯曲，空气阻力使足球减速，自旋还会产生侧向或竖直方向的气动力。这些作用共同决定足球到达球门平面的位置。已有研究将牛顿运动定律与实验气动关系结合，用于描述足球飞行\cite{bray,maponi,kiratidis2018}；高精度模拟也揭示了接缝等表面特征对流动与轨迹的影响\cite{paudel}。''',
38:r'''将计算轨迹与真实踢球过程中记录的位置比较，可以检验物理模型的预测表现。DFL 开放数据集同时提供职业比赛事件和光学追踪数据\cite{bassek,dataset}，可据此识别点球事件、追踪空中飞行，并比较足球在实际球门平面的位置。''',
41:r'''本文研究足球从点球点附近飞向球门的三维运动。球门宽 7.32 m、高 2.44 m，点球点距球门线 11 m。我们建立包含重力、阻力与马格努斯效应的模型，求解飞行轨迹及球门平面交点，并与实测点球飞行对照。题目预测使用初始位置及 0.05、0.10 s 的位置，后续位置用于验证。图~\ref{fig:workflow} 概述受力模型与逆向问题：早期位置确定初始状态和气动力修正系数，后续位置提供比较目标。第二章介绍假设与符号，第三章建立受力和运动方程，第四章比较正向与逆向预测，第五章预留灵敏性分析，第六章讨论表面几何、旋转阻尼和风，第七、八章给出小结与模型评价。''',
51:r'''\item 参照已有足球飞行模型\cite{maponi,bray,myers}，将足球视为质量和半径恒定的刚性球体，迎风面积为 $A=\pi R^2$，位置取球心位置。经验足球气动系数表征表面的平均影响，第~\ref{sec:surface} 节进一步讨论接缝和非对称几何的作用。''',
52:r'''\item 自由飞行中考虑重力、空气阻力与自旋升力\cite{maponi,bray}；到达地面或指定球门平面时停止积分。''',
53:r'''\item 主模型忽略气动力矩，因此自旋向量保持恒定。第~\ref{sec:rotation} 节通过在同一初始状态下加入旋转阻尼，分析这一近似的影响。''',
54:r'''\item 空气密度与黏度均匀，主计算采用静止空气。第~\ref{sec:wind} 节估算风对相对来流和气动力的影响。''',
55:r'''\item 初始位置和随后两个早期位置构成逆向输入，DFL 追踪记录中的后续位置用于比较\cite{bassek,dataset}。记录的竖直坐标按以米为单位的高度处理。''',
76:r'''题目工况的质量、半径与重力加速度采用 Maponi 和 Piombin 的参考值\cite{maponi}，空气密度取自 Asai 等\cite{asai2007}。运动黏度作为参考空气条件给定，动力黏度按 $\mu=\rho\nu$ 统一计算。受控实验采用各自报告的质量、直径及空气参数。''',
79:r'''通过选择纳入的气动力项，同一组牛顿运动方程可形成四类模型。以下先描述几何关系，再将受力与周围流动和球体自旋联系起来。''',
81:r'''以球场中心为原点、球场长 105 m 时，两条球门线位于 $x=\pm52.50$ m。所选踢球方向朝向正 $x$ 球门。题目局部坐标中，球门开口范围为 $-3.66\le y\le3.66$ m、$0\le z\le2.44$ m。球门交点定义为球心沿前进方向首次到达 $x=X_g$ 时的位置。''',
84:r'''图~\ref{fig:geometry} 以点球点为局部原点，球门平面为 $x=11$ m；比赛记录采用球场中心坐标，球门位于 $X_g=52.50$ m。''',
86:r'''在 $x=X_g$ 处，若球心满足 $|y|\leq3.66-R$ 和 $R\leq z\leq2.44-R$，足球可完整通过球门开口。球心下降至 $z=R$ 时视为触地。四种模型统一采用上述事件判据。''',
90:r'''重力提供恒定的竖直向下作用力，''',
92:r'''其中 $\boldsymbol e_z$ 为竖直向上的单位向量。即使不计气动力，重力也会使轨迹向下弯曲。''',
95:r'''运动足球向尾流中的空气传递动量。通过面积 $A$ 的空气质量流率与 $\rho Av$ 成正比，速度变化量与 $v$ 同阶，因此气动力尺度为 $\rho Av^2$。引入动压 $q=\rho v^2/2$，得到常用阻力表达式\cite{goff2009,kiratidis2018}：''',
100:r'''式中各物理量的作用如下：''',
102:r'''\item \textbf{空气密度\boldmath$\rho$。} 密度表示单位体积内的空气质量。本文采用 Asai 等报告的均匀参考值 $1.2$ kg/m$^3$\cite{asai2007}。''',
103:r'''\item \textbf{迎风面积\boldmath$A=\pi R^2$。} 半径越大，球体截获的气流越多；球形几何使该面积在飞行中保持不变。''',
104:r'''\item \textbf{相对速度及方向\boldmath$v,\boldsymbol u$。} 阻力随速度平方增大，负号表明其方向与相对来流相反。静止空气的主模型中，$\boldsymbol u=\boldsymbol v$。''',
105:r'''\item \textbf{阻力系数\boldmath$C_D(Re,Sp)$。} 该系数表征边界层转捩、流动分离和尾流形成。依据 Asai 等及 Kiratidis、Leinweber 的定义\cite{asai2007,kiratidis2018}，引入''',
110:r'''$Re$ 比较流动中的惯性效应与黏性效应，$Sp$ 比较球面旋转速度与来流速度。自旋恒定时，足球减速会使 $Sp$ 增大。''',
112:r'''阻力危机是边界层转捩引起的阻力快速下降过程。经验关系需同时描述这一过渡和超临界区较缓慢的变化。根据 Kiratidis 和 Leinweber\cite{kiratidis2018}，其文献式（5）将无旋转阻力表示为''',
120:r'''系数 $a$ 决定低速阻力水平，$v_c$ 确定转捩位置，$v_s$ 控制过渡宽度，其余参数确定高速段的水平与斜率。表~\ref{tab:teamgeist} 列出该文献表 1 的 Teamgeist 参数\cite{kiratidis2018}。''',
128:r'''对于旋转 Teamgeist 球，Kiratidis 和 Leinweber 的文献式（7）加入斜率为 0.514 的线性自旋修正，该值由超临界风洞数据拟合得到\cite{kiratidis2018}：''',
132:r'''因此，无旋转时阻力系数仍随速度变化，旋转也会增大阻力。系数对照统一采用 Teamgeist 参数；其他球面可采用对应的经验参数。''',
135:r'''最终 M4 轨迹的速度为 \ProblemSpeedMin--\ProblemSpeedMax\ m/s，雷诺数为 $(\ProblemReMin$--$\ProblemReMax)\times10^5$。Kiratidis 和 Leinweber 的 Teamgeist 拟合覆盖至 35 m/s\cite{kiratidis2018}，在本文空气条件下对应 $Re=5.13\times10^5$。题目飞行处于该速度范围和经验关系所描述的超临界流动区，采用这一经验关系具有相应工况依据。Asai 的旋转实测范围为 $Re=333793$--455172，两张系数图固定在实测上限工况进行对照。题目反演得到 $Sp=\ProblemSpMin$--\ProblemSpMax，其较高取值超出所选风洞自旋区间。''',
136:r'''\item \textbf{阻力修正系数\boldmath$\alpha_D\geq0$。} 该无量纲乘子在正向计算中取一，在逆向计算中由早期位置估计。''',
139:r'''Asai 等\cite{asai2007} 在日本东海大学低速回流风洞中利用六分力天平测量足球气动力，测量段为 $1.5\times1$ m，湍流度约 1\%。本文采用其全尺寸旋转 Teamgeist 玻璃纤维增强塑料复制球数据：$R=0.11$ m、$\rho=1.2$ kg/m$^3$，风速 22--30 m/s，转速 2--10 rev/s。在 $Re=455172$（约 30 m/s）下，从原文图 8、9 各提取五个系数数据点；其中侧向力系数 $C_S$ 对应本文的横向马格努斯升力。速度与雷诺数的对应关系给出该对照工况的 $\nu\simeq1.45\times10^{-5}$ m$^2$/s。''',
141:r'''图~\ref{fig:cd-comparison} 再现了阻力随 $Sp$ 增大的趋势，系数平均绝对误差为 0.00985，均方根误差为 0.01127。两条曲线采用相同工况，并在实测自旋区间内比较。''',
148:r'''旋转改变球体两侧的流动，形成横向压力作用。采用与阻力相同的动压尺度，横向旋转时有 $F_L=qAC_L$\cite{goff2009,kiratidis2018}。对于三维旋转轴，本文采用''',
156:r'''自旋为零、来流速度为零，或旋转轴与来流平行时，升力取零。''',
158:r'''\item \textbf{动压与面积尺度\boldmath$\rho Av^2/2$。} 密度、迎风面积和速度的含义与阻力表达式相同。''',
159:r'''\item \textbf{马格努斯力方向\boldmath$\boldsymbol e_L$。} 该单位向量垂直于来流。上旋使轨迹向下弯曲，下旋使其向上弯曲，侧旋使其在水平方向偏转。''',
160:r'''\item \textbf{角度投影\boldmath$\sin\theta$。} 旋转轴与来流垂直时该横向分量为一，平行时为零。此投影将横向旋转经验关系扩展至斜置旋转轴。''',
161:r'''\item \textbf{升力系数\boldmath$C_L(Re,Sp)$。} 旋转强度与边界层状态共同决定升力。''',
163:r'''旋转引起非对称流动和横向马格努斯力，其大小同时受边界层状态与自旋影响。Kiratidis 和 Leinweber\cite{kiratidis2018} 在文献式（8）中给出参考幂律''',
167:r'''并在文献式（9）中用阻力表征流动状态，对该幂律进行缩放\cite{kiratidis2018}。本文采用这一完整关系：''',
173:r'''其中 Teamgeist 参考量为''',
178:r'''$C_{D,\mathrm{ceil}}\simeq0.4927$ 为无旋转低速阻力上限。参考阻力按式~\eqref{eq:cd-full} 计算，包含自旋项，并采用与当前计算一致的 $R$ 和 $\nu$。在参考点 $(Re,Sp)=(333793,0.19)$，缩放因子为一，$C_L\simeq0.290$。阻力上限、参考工况及利用阻力缩放升力的方法均来自 Kiratidis 和 Leinweber\cite{kiratidis2018}；式~\eqref{eq:cl-full} 给出受力模型最终采用的升力系数。''',
181:r'''\item \textbf{升力修正系数\boldmath$\alpha_L\geq0$。} 该无量纲乘子在正向预测中取一，在包含升力的逆向预测中由早期位置拟合。''',
184:r'''图~\ref{fig:cl-comparison} 采用同一 Asai 实验工况。完整经验关系再现了升力随 $Sp$ 增大的趋势，且高于全部五个实测点：平均绝对误差为 0.04505，均方根误差为 0.05040，最大差值为 0.07325。这一较大的偏差说明了逆向计算引入升力修正系数 $\alpha_L$ 的意义。''',
191:r'''牛顿第二定律与角动量定律给出''',
196:r'''外力矩取零、球体转动惯量恒定时，主模型为''',
204:r'''相应初始条件为''',
212:r'''已知初始位置确定飞行起点，三个初速度分量与三个自旋分量描述初始运动。在静止空气中，阻力消耗机械能，马格努斯力沿速度方向不做功，重力使动能与势能相互转换。''',
215:r'''通过逐步增加气动描述，比较各作用对轨迹的影响。表~\ref{tab:models} 定义四类模型。正向预测采用实测或重建的发射条件，气动力修正系数取一；逆向预测利用两个后续位置反演初始运动与气动力修正，再将该状态推进至球门。''',
225:r'''M2、M3 的常系数统一在文献参考点计算：''',
229:r'''在题目的球体与空气参数下，$C_D^*=\ReferenceCD$、$C_L^*=\ReferenceCL$。同一算例中的各模型采用相同物理条件。M1、M2 的轨迹与自旋无关；M3 使用旋转轴方向，M4 同时使用其方向和大小。''',
233:r'''给定 $\boldsymbol r_0$、$\boldsymbol v_0$、$\boldsymbol\omega_0$，取 $\alpha_D=\alpha_L=1$，采用自适应龙格--库塔方法积分式~\eqref{eq:motion}。通过 $x-X_g$ 的零点确定球门交点，通过 $z-R$ 的下降零点确定触地。计算同时记录飞行速度和气动力大小。''',
235:r'''Goff 和 Carr\'e\cite{goff2009} 用独立驱动轮发射 32 块面板足球，并由两台高速相机记录运动。实验球质量为 0.424 kg、直径为 0.218 m，空气密度为 1.2 kg/m$^3$，运动黏度为 $1.54\times10^{-5}$ m$^2$/s。通过球面标记测量旋转，利用地面标记测量落点射程，报告的射程误差不超过 $\pm0.05$ m。''',
237:r'''本文采用其图 3、4、11 的无旋转算例：初速度约 18 m/s、仰角约 $22^\circ$、初始球心高度约 0.85 m，实测射程 21.9 m。其图 14 中的四组上旋实验提供额外空间轨迹片段。已发表的初始 $Re$、$Sp$ 用于确定速度与自旋，前三个数字化位置确定初始空间切线。五组对照均直接提取原矢量 PDF 的红色实测标记中心。无旋转早期标记间隔为 0.005 s；旋转片段按 $z(x)$ 空间曲线与公开坐标比较。''',
239:r'''表~\ref{tab:forward-initial} 列出正向输入。各算例位于 $x$--$z$ 平面，$y_0=v_{y0}=0$、$\omega_{x0}=\omega_{z0}=0$，因此表中的 $v_{x0}$、$v_{z0}$、$\omega_{y0}$ 补全了六个初速度和自旋分量。首个标记给出初始位置。''',
246:r'''仅受重力作用时射程最远。空气阻力消耗水平动量并缩短射程。M2、M3 采用相同恒定阻力系数，因而在无旋转条件下得到重合轨迹。M4 允许阻力系数随减速来流变化，在所述近似发射条件下，其预测射程与实测之差为 \ForwardMFourError\ m。''',
251:r'''上旋产生向下的马格努斯力，增大轨迹向下弯曲的程度。表~\ref{tab:forward-spin} 给出各实测水平位置对应的高度均方根误差，不同发射的模型排序有所变化。初始方向的局部估计和实验球表面都会影响与 Teamgeist 参考关系的对照。在上旋 c 算例中，较大的自旋参数使经验阻力超过式~\eqref{eq:cl-full} 中的上限，M4 因而给出零升力；实测轨迹仍保留向下的旋转弯曲，故 M3 在该算例中的局部误差较小。这些结果将系数关系的差别与预测路径的变化联系起来。''',
255:r'''图~\ref{fig:forward-dynamics} 展示上述路径对应的物理过程：球速较高时阻力较强；上旋的向下升力改变竖直运动与飞行时间。M4 中速度变化还会改变 $Re$ 和 $Sp$，因此气动力演化同时包含动压和系数变化的影响。''',
259:r'''设已知 $\boldsymbol r_0$，其后 $t_1,t_2$ 时刻的位置为 $\boldsymbol p_1,\boldsymbol p_2$。选择初始运动与相应气动力修正，使下式最小：''',
264:r'''随后优先选择接近文献基准气动力尺度的修正系数，''',
266:r'''其中仅保留各模型实际包含的修正项。对拟合质量相同的 M4 状态，再以最小自旋模长选取代表解。确定性多初值优化依次执行这些准则；位置目标允许差额为 $6\times10^{-12}$ m$^2$，系数目标允许差额为 $10^{-8}$，均为数值选解容差。初值由观测位移速度与文献实验转速生成。M3 用两个角度表示旋转轴，其单位向量在式~\eqref{eq:lift-force} 中用于确定方向。''',
269:r'''Sportec Open DFL 数据集将光学追踪与比赛事件关联\cite{bassek,dataset}。本文分析 J03WOH、J03WQQ 两场比赛中的四段飞行，以及一组点球记录；筛选依据为可识别的射门事件和跨越实际球门线平面的连续追踪。四段飞行包括两次头球和两次脚部射门。逆向计算使用 0、0.04、0.08 s 的前三个位置，随后追踪坐标用于确定实测球门交点。点球片段的首次位移较小，之后运动较快，计算沿用原始早期坐标。''',
278:r'''这一对照将早期加速度与后续飞行联系起来。较大的阻力修正会造成较快的动量损失，升力修正则改变轨迹弯曲方向。因此，早期记录位移的变化会明显影响终点预测，各事件结果展示了不同模型对实际记录片段的响应。''',
281:r'''题目给出的观测为''',
288:r'''采用相同逆向流程得到表~\ref{tab:problem}，所选 M4 初始条件为''',
299:r'''重力和阻力保持水平速度分量之比，M1、M2 因而预测近似相同的水平方向。M3、M4 加入马格努斯力后，轨迹产生侧向弯曲。M4 球心在 $\ProblemTime$ s 到达球门平面，交点为 $(\ProblemY,\ProblemZ)$ m，考虑球半径后仍可通过开口。早期坐标最大残差为 \ProblemResidual\ m，反演初始自旋为 \ProblemSpin\ rad/s，为该代表解提供所需的气动弯曲。''',
306:r'''图~\ref{fig:problem-coefficients} 说明了自旋恒定时气动力仍会变化的原因：足球减速使球面速度与来流速度之比增大，阻力缩放也随之改变升力系数。''',
312:r'''主模型突出重力、阻力和马格努斯升力，以下分析其在几何、自旋演化和环境来流中省略的因素。''',
314:r'''Paudel 和 Yan\cite{paudel} 利用真实足球几何进行全程流动模拟，并与光滑球比较。在初速度 10、15、20 m/s，自旋 31.5、63、94.5 rad/s 的工况下，接缝和表面结构会改变流动分离、尾流演化及马格努斯力。九组对照中光滑球的横向弯曲均更强，较高速度和转速下竖直飞行时间的差异也更明显。''',
316:r'''本文的球形几何描述质心运动与迎风面积，气动力系数来自足球实验，因此表面的平均作用已进入 $C_D$、$C_L$。当侧向力细节更为重要时，可进一步描述面板朝向与非对称尾流波动。这些文献结果说明，在球形轨迹模型中保留足球专用气动系数具有物理依据。''',
319:r'''旋转影响马格努斯力，因此自旋衰减会改变弧线球的后续运动。依据 Grad 等的补充材料第 8.4 节\cite{grad2026}和 MuJoCo 椭球流体模型\cite{mujoco381}，球形化简后的惯性与黏性阻尼力矩为''',
325:r'''二次项描述高雷诺数旋转阻力，线性项为黏性阻力。本文采用 MuJoCo 文档给出的参考值 $C_{\rm angular}=1.5$\cite{mujoco381}。定义 $q=\rho v^2/2$、$C_{Q,v}=\|\boldsymbol Q\|/(qAR)$，得到''',
331:r'''$C_{Q,\omega}$ 采用球面旋转速度 $R\omega$ 定义参考动压，$1/Sp^2$ 用于两种归一化之间的换算。黏性力矩与惯性力矩之比为''',
337:r'''在题目反演初始状态下，该比值为 \TorqueViscousRatio，二次项占主导。采用 Maponi 和 Piombin 的薄球壳转动惯量\cite{maponi}，$I_b=2mR^2/3$。加入高雷诺数阻尼后，动力学方程为''',
345:r'''力矩方向与自旋相反，消耗旋转动能。单独考虑二次阻尼时，$\omega(t)=\omega_0/[1+(k_2/I_b)\omega_0t]$，可用于校验转动积分。''',
347:r'''保持 M4 题目算例的初始状态与气动力修正系数相同，分别计算恒定自旋与式~\eqref{eq:motion-torque} 的阻尼飞行，从而直接比较旋转阻尼的作用。''',
353:r'''风通过 $\boldsymbol u=\boldsymbol v-\boldsymbol v_{\rm wind}$ 改变相对来流\cite{maponi}。暂保持气动系数不变，沿飞行方向大小为 $w$ 的风使动压尺度变为''',
359:r'''横风还使来流转过 $\arctan(w/v)$，从而改变气动力方向。表~\ref{tab:wind} 在反演初速度下给出上述粗略估算，列示风速作为比较工况。''',
361:r'''将逆风动压增幅限制在 5\% 时，有 $w/v\leq\sqrt{1.05}-1$，对应本算例的 $w\leq\WindThreshold$ m/s。静止空气近似更适合室内或弱风飞行；风速较大时应通过相对速度纳入计算。''',
364:r'''三力模型将足球飞行与三种作用联系起来：重力造成向下弯曲，阻力消耗动量，马格努斯升力改变方向。完整 Teamgeist 经验关系描述流动状态与自旋变化，2007 年同工况风洞对照中，阻力的定量吻合程度高于升力。''',
366:r'''受控无旋转算例说明，阻力对射程预测十分重要；M4 预测 \ForwardMFourRange\ m，文献实测为 21.9 m。旋转轨迹片段展示了上旋造成的向下弯曲，以及同一系数关系在不同算例中的表现差异。比赛记录对照则说明早期位移和拟合修正系数如何影响后续预测。''',
368:r'''对于题目 B，M4 的球门交点为 $(y,z)=(\ProblemY,\ProblemZ)$ m。马格努斯力解释了其与仅含重力、阻力模型之间明显的水平差别。相同初始状态下，采用所引力矩参考值使交点移动 \TorqueDisplacement\ m。风的估算给出了静止空气近似对应的弱风条件，灵敏性分析结论将在第五章完成后补充。''',
372:r'''模型层级使各力的作用清晰可见，同一套动力学支持正向求解、早期位置反演和终点预测。气动力修正系数直接联系实测轨迹差异，各实验与数值输入均保留相应来源。''',
374:r'''风洞系数、受控发射和比赛飞行分别考察系数趋势、曲率与射程、以及依据早期位置进行预测的表现。逐事件误差展示了经验足球系数与早期轨迹对后续运动的描述情况。球型专用气动测量、直接自旋测量和同步高频位置记录有助于改善预测，具体应用还可纳入表面朝向、旋转阻尼与风。''',
}

TITLES={
'Modeling and Validation of a Soccer Ball\'s Three-Dimensional Flight to the Goal':'足球三维飞行至球门的建模与实测对照',
'Introduction':'引言','Problem Background':'问题背景','Problem Restatement':'问题重述',
'Preparation of the Models':'模型准备','Assumptions':'基本假设','Notations':'符号说明',
'Model Establishment':'模型建立','Geometry and Goal Plane':'几何与球门平面','Force Analysis':'受力分析',
'Aerodynamic Drag':'空气阻力','Magnus Lift':'马格努斯升力','Gravity':'重力','Dynamical Equations':'动力学方程',
'Model Solving':'模型求解','Forward Prediction':'正向预测','Prediction procedure and experimental conditions':'求解方法与实验条件',
'Calculated trajectories and physical interpretation':'计算轨迹与物理分析','Inverse Prediction':'逆向预测',
'Early-position fitting and representative solution':'早期位置反演与代表解','Comparison with recorded match flights':'比赛实测飞行对照',
'Competition Problem B':'题目 B 算例','Sensitivity Analysis':'灵敏性分析','Discussion of Other Factors':'其他因素讨论',
'Asymmetric Surface Geometry':'足球表面的非对称几何','Rotation and Aerodynamic Damping':'足球旋转与气动阻尼',
'Wind Speed and Force Estimates':'风速与气动力估算','Conclusions':'小结','Model Evaluation':'模型评价',
'Physical Interpretation and Computational Use':'物理解释与计算应用','Predictive Performance and Improvements':'预测表现与改进方向',
'Comparison with published wind-tunnel data.':'与已发表风洞数据的对照。',
'References':'参考文献','Reproduction Code':'复现代码','To be completed.':'待完成。',
}
CAPTIONS={
'fig:workflow':'三力建模、四类模型比较与球门交点预测。',
'tab:notations':'主要物理量及题目参考值。',
'fig:geometry':'点球局部坐标几何。虚线及点 $P$ 表示示意交点。',
'tab:teamgeist':r'Teamgeist 无旋转阻力参数，取自 Kiratidis 和 Leinweber\cite{kiratidis2018}。',
'fig:cd-comparison':r'$Re=455172$ 下的 Teamgeist 阻力：完整经验关系\cite{kiratidis2018}与 Asai 原文图 8 的五个数字化实测点\cite{asai2007}。',
'fig:cl-comparison':r'$Re=455172$ 下的 Teamgeist 横向升力：完整经验关系\cite{kiratidis2018}与 Asai 原文图 9 的五个数字化侧向力实测点\cite{asai2007}。',
'tab:models':'四类模型。各模型均考虑重力，并保持自旋恒定。',
'fig:forward-range':r'Goff 和 Carr\'e 无旋转实验的正向预测\cite{goff2009}。左图为计算路径、数字化早期位置及实测落点；右图将各模型射程与实测 21.9 m 比较。初始自旋为零时 M2、M3 重合。',
'fig:forward-spin':r'从 Goff 和 Carr\'e 原文图 14 提取的四组上旋轨迹\cite{goff2009}。黑点为实测标记中心，各模型采用单位气动力修正和已列初始条件，显示范围为公开的早期空间片段。',
'fig:forward-dynamics':'无旋转与上旋 b 正向算例中的速度、阻力和升力。力的大小由同一组方程计算；即使系数恒定，动压随速度变化仍使气动力变化。',
'fig:inverse-errors':r'五组比赛飞行各模型的球门交点误差，每个标记对应一个事件和模型。零线下的叉号表示未给出有效球门交点，具体状态见表~\ref{tab:match-results}。',
'fig:penalty':r'点球记录的已收敛逆向预测及全部追踪位置。前三个位置用于反演，其余位置展示实测后续运动；各模型状态见表~\ref{tab:match-results}。',
'fig:problem-prediction':'题目 B 的四类逆向预测：水平路径、竖直路径和球门平面球心位置。黑点为题目给定的早期位置。',
'fig:problem-dynamics':'题目 B 四类反演模型的速度与气动力大小。同一组观测在不同受力假设下给出不同后续路径。',
'fig:problem-coefficients':'题目 B 中 M4 的完整气动系数与自旋参数。自旋恒定、速度下降使 $Sp$ 增大，完整经验关系决定相应阻力与升力系数。',
'fig:torque':'题目 B 相同初始状态下恒定自旋与高雷诺数旋转阻尼的对照。旋转阻力参考系数为 1.5，转动惯量采用薄球壳近似。',
}

def replace_caption(line,translation):
    command=r'\captionof{table}' if r'\captionof{table}' in line else r'\caption'
    start=line.index(command)+len(command)
    assert line[start]=='{'
    depth=0
    for end in range(start,len(line)):
        if line[end]=='{' and (end==0 or line[end-1]!='\\'):depth+=1
        if line[end]=='}' and line[end-1]!='\\':
            depth-=1
            if not depth:return line[:start+1]+translation+line[end:]
    raise ValueError(line)

def main():
    source=(ROOT/'paper/main.tex').read_text(encoding='utf-8');lines=source.splitlines();records=[]
    source_hash=hashlib.sha256(source.encode()).hexdigest()
    guard=Path(__file__).with_name('chinese_translation_source.sha256')
    if guard.exists() and guard.read_text(encoding='utf-8').strip()!=source_hash:
        raise RuntimeError('English source changed: update the translation catalog before rebuilding Chinese text')
    if not guard.exists():guard.write_text(source_hash+'\n',encoding='utf-8')
    if not ZH.exists():shutil.copytree(ROOT/'paper',ZH)
    if not (ZH/'figures').exists():shutil.copytree(ROOT/'results/structure_v2/figures',ZH/'figures')
    if not (ZH/'assets/geometry.pdf').exists():shutil.copy2(ROOT/'results/paper_geometry/geometry.pdf',ZH/'assets/geometry.pdf')
    for number,target in P.items():
        records.append(dict(line=number,source=lines[number-1],translation=target));lines[number-1]=target
    for i,line in enumerate(lines):
        if '\\caption' in line:
            label=re.search(r'\\label\{([^}]+)\}',line)
            if label and label[1] in CAPTIONS:line=replace_caption(line,CAPTIONS[label[1]])
        for original,target in sorted(TITLES.items(),key=lambda p:-len(p[0])):
            # Only headings/title commands are affected; prose was translated explicitly above.
            if line.startswith(('\\section','\\subsection','\\subsubsection','\\paragraph','\\addcontentsline','{\\Large')):
                line=line.replace(original,target)
        if line.startswith('The accompanying project'):
            line=r'随附项目包含固定输入、矢量标记提取、四模型计算、结果表及制图脚本。以下节选展示统一状态方程和受力计算。逆向求解按第~\ref{sec:inverse} 节的三级准则调用同一状态导数。计算与制图分别执行，可直接利用保存结果更新图表。'
        lines[i]=line
    text='\n'.join(lines)+'\n'
    text=text.replace(r'\usepackage{microtype,needspace,fontspec}',r'\usepackage{microtype,needspace,fontspec}'+'\n'+r'\usepackage[UTF8,fontset=none,scheme=plain]{ctex}')
    text=text.replace(r'\setmainfont{Times New Roman}',r'''\setmainfont{Times New Roman}
\setCJKmainfont{SimSun}[BoldFont=SimHei,ItalicFont=KaiTi,BoldItalicFont=KaiTi]
\setCJKsansfont{SimHei}
\setCJKmonofont{SimSun}[BoldFont=SimHei,ItalicFont=KaiTi]
\ctexset{contentsname=目录,figurename=图,tablename=表}
\renewcommand{\refname}{参考文献}
\setlength{\emergencystretch}{3em}
\setlength{\parindent}{2em}''')
    text=text.replace(r'\fancyhead[L]{\normalsize Problem B}',r'\fancyhead[L]{\normalsize 题目 B}')
    text=text.replace('The University Physics Competition','国际大学生物理竞赛')
    text=text.replace(r'Page \thepage\ of \pageref{LastPage}',r'第 \thepage\ 页，共 \pageref{LastPage} 页')
    text=text.replace(r'{\bfseries Problem B\par}',r'{\bfseries 题目 B\par}').replace(r'{\bfseries Abstract\par}',r'{\bfseries 摘要\par}')
    text=text.replace(r'\textit{To be completed.}',r'\textit{待完成。}')
    text=text.replace(r'\addcontentsline{toc}{section}{Reproduction Code}',r'\addcontentsline{toc}{section}{复现代码}')
    text=text.replace(r'\setlength{\parindent}{1.5em}',r'\setlength{\parindent}{2em}')
    text=text.replace(r'\graphicspath{{aerodynamics/}{assets/}{../results/structure_v2/figures/}{../results/paper_geometry/}}',r'\graphicspath{{aerodynamics/}{assets/}{figures/}}')
    cell={'Symbol & Meaning & Value or unit':'符号 & 含义 & 数值或单位',
        'Ball-centre position and velocity':'球心位置与速度','Spin vector and its magnitude':'自旋向量及其模长',
        'Mass, radius and frontal area':'质量、半径与迎风面积','Gravitational acceleration':'重力加速度',
        'Air-relative velocity and its magnitude':'相对空气速度及其模长','Air density':'空气密度',
        'Kinematic and dynamic viscosity':'运动黏度与动力黏度','Reynolds number and spin parameter':'雷诺数与自旋参数',
        'Drag and transverse lift coefficients':'阻力与横向升力系数','Multiplicative force corrections':'气动力乘法修正系数',
        'Spin--airflow angle and Magnus direction':'自旋与来流夹角、升力方向','Local goal-plane coordinate':'局部球门平面坐标',
        'Damping torque and moment of inertia (Section 6)':'阻尼力矩与转动惯量（第六章）',
        'dimensionless':'无量纲','rad; unit vector':'rad；单位向量',
        'Model & Drag & Magnus lift & Inverse quantities':'模型 & 阻力 & 马格努斯升力 & 反演量',
        ' & none & ':' & 无 & ',' & constant ':' & 恒定系数 ', 'spin axis':'旋转轴',
        'Data mirror:':'数据镜像：','Equations and parameters:':'公式及参数：','Supplementary material':'补充材料',
        'Section~8.4':'第 8.4 节','Version 3.8.1 source':'3.8.1 版源代码',
        'default angular drag:':'默认旋转阻力：','XML reference, geom/fluidcoef':'XML 参考，geom/fluidcoef',
        'Accessed 8 November 2026.':'访问日期：2026 年 11 月 8 日。'}
    for a,b in sorted(cell.items(),key=lambda p:-len(p[0])):text=text.replace(a,b)
    # Consecutive absent terms in M1 share the separator, so translate any remaining table-only cell.
    text=text.replace(' & none & ',' & 无 & ')
    ZH.mkdir(exist_ok=True);(ZH/'main.tex').write_text(text,encoding='utf-8')
    (ZH/'translation_catalog.json').write_text(json.dumps(dict(english_sha256=hashlib.sha256(source.encode()).hexdigest(),
        policy='normal Chinese: SimSun; English bold -> SimHei; English italic -> KaiTi; figures retain English',
        paragraphs=records),ensure_ascii=False,indent=2),encoding='utf-8')
    translate_results()
    (ZH/'README.md').write_text('''# 中文版编译说明

本目录由修改后的完整英文 LaTeX 编译目录复制，正文、表格与图注译为中文，图内文字和路线图保留英文。数值、公式和引用编号与英文稿一致。

字体按原英文样式对应：普通正文译文使用宋体（SimSun），原加粗内容译文使用黑体（SimHei），原斜体内容译文使用楷体（KaiTi）。西文字母和数学符号保持原字体。

在本目录执行三次 `xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex`。需安装宋体、黑体、楷体和 Times New Roman。附录引用同一仓库 `../src/` 下的计算程序；图表均随本目录保存。

`translation_catalog.json` 记录英文源稿 SHA256 和段落译文；`archive/` 保留复制时的历史源稿。更新译文可在仓库根目录运行 `python scripts/build_chinese_report.py`，图像和路线图的英文标注保持不变。
''',encoding='utf-8')
    print('Chinese body, captions and tables generated; English figures preserved')

def translate_results():
    s=(ROOT/'paper/report_results.tex').read_text(encoding='utf-8')
    captions={
    'Initial conditions for the controlled forward examples, reconstructed as described above.':'按正文方法重建的受控正向算例初始条件。',
    'Nonspinning controlled launch: predicted landing and signed range error. The reported range is 21.9 m.':'无旋转受控发射的预测射程与带符号误差；文献实测射程为 21.9 m。',
    'Height RMSE (m) at digitized horizontal positions for the four topspin segments.':'四组上旋片段在实测水平位置处的高度均方根误差（m）。',
    'Inverse predictions for the competition observations. Residual is the maximum absolute early-coordinate difference.':'题目给定观测的逆向预测；残差为早期坐标最大绝对差。',
    'All five recorded flights and all four inverse models. Error is the Euclidean difference in goal-plane $(y,z)$.':'五组实测飞行与四类逆向模型的完整结果；误差为球门平面 $(y,z)$ 的欧氏距离。',
    'Reached-case errors and termination counts. Individual errors are retained in the preceding table.':'到达球门平面算例的误差与各终止状态计数，逐事件误差见前表。',
    'Illustrative wind estimates at the fitted launch speed. Percentages describe dynamic pressure at fixed aerodynamic coefficients.':'反演初速度下的示例风速估算；百分比表示气动系数固定时的动压变化。'}
    for a,b in captions.items():s=s.replace(a,b)
    cells={'Prediction minus measurement (m)':'预测减去实测（m）','Early residual (m)':'早期残差（m）',
        'Plane error (m)':'交点误差（m）','Mean error (m)':'平均误差（m）','Range (m)':'射程（m）','Residual (m)':'残差（m）',
        'Launch &':'发射 &','Model &':'模型 &','Event &':'事件 &','Termination &':'终止状态 &',
        'Reached & Ground & Other & Fit failures':'到达 & 触地 & 其他 & 拟合失败',
        'Zero spin &':'无旋转 &','Topspin ':'上旋 ','(head)':'（头球）','(foot)':'（脚部）','Penalty &':'点球 &',
        'early termination':'提前终止','fit failure':'拟合失败',' & plane &':' & 到达平面 &',' & ground &':' & 触地 &',
        'Headwind (\\%)':'逆风（\\%）','Tailwind (\\%)':'顺风（\\%）','Crosswind (\\%)':'横风（\\%）',
        'Airflow angle ($^\\circ$)':'来流夹角（$^\\circ$）'}
    for a,b in sorted(cells.items(),key=lambda p:-len(p[0])):s=s.replace(a,b)
    s=re.sub(r'\\newcommand\{\\MatchDiscussion\}\{[^\n]*\}',lambda m:r'\newcommand{\MatchDiscussion}{M1 在五组飞行中有四组到达球门平面，M2 为三组，M3、M4 各为一组。M1 在这些记录中给出最多的球门交点预测。表中同时报告到达算例的平均误差与对应数量。较大的气动力修正及迭代上限情况表明，预测对早期记录运动十分敏感。拟合失败表示达到数值迭代上限，相应候选轨迹保存在计算记录中。}',s)
    s=re.sub(r'\\newcommand\{\\TorqueResults\}\{[^\n]*\}',lambda m:r'\newcommand{\TorqueResults}{加入阻尼后，球门交点为 $(2.541,1.996)$ m，恒定自旋时为 $(2.683,1.959)$ m。交点位移为 0.147 m，占 11 m 飞行距离的 1.34\%；自旋减小 41.24\%，到达球门的时间变化为 $-1.60$\%。再加入较弱的黏性项后，阻尼交点变化为 $6.5\times10^{-6}$ m。因此，该参考力矩明显改变自旋，同时使短程飞行终点发生较小而可量化的变化。}',s)
    (ZH/'report_results.tex').write_text(s,encoding='utf-8')

if __name__=='__main__':main()
