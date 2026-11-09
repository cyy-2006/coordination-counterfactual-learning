from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "pdf" / "Ego_to_Dexterous_论文流程与创新点简报.pdf"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

pdfmetrics.registerFont(TTFont("Hei", r"C:\Windows\Fonts\simhei.ttf"))
pdfmetrics.registerFont(TTFont("Noto", r"C:\Windows\Fonts\NotoSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("NotoBold", r"C:\Windows\Fonts\NotoSans-Bold.ttf"))

NAVY = colors.HexColor("#17324D")
INK = colors.HexColor("#183147")
MUTED = colors.HexColor("#536678")
TEAL = colors.HexColor("#087E80")
PALE = colors.HexColor("#EAF5F3")
PALEBLUE = colors.HexColor("#EEF3F8")
BORDER = colors.HexColor("#DDE5EC")
AMBER = colors.HexColor("#9C6815")
AMBER_BG = colors.HexColor("#FFF5E3")

title = ParagraphStyle("title", fontName="Hei", fontSize=21, leading=30, textColor=NAVY, spaceAfter=7)
subtitle = ParagraphStyle("subtitle", fontName="Hei", fontSize=11, leading=17, textColor=MUTED)
section = ParagraphStyle("section", fontName="Hei", fontSize=13.1, leading=20, textColor=NAVY, spaceBefore=10, spaceAfter=7)
subsection = ParagraphStyle("subsection", fontName="Hei", fontSize=10.5, leading=16, textColor=TEAL, spaceBefore=7, spaceAfter=5)
body = ParagraphStyle("body", fontName="Hei", fontSize=9.1, leading=14.1, textColor=INK)
small = ParagraphStyle("small", fontName="Hei", fontSize=8.2, leading=12.4, textColor=MUTED)
cardtitle = ParagraphStyle("cardtitle", fontName="Hei", fontSize=10.2, leading=15, textColor=NAVY)
cardbody = ParagraphStyle("cardbody", fontName="Hei", fontSize=8.9, leading=13.8, textColor=INK)
cell = ParagraphStyle("cell", fontName="Hei", fontSize=8.7, leading=13.4, textColor=INK)
cellhead = ParagraphStyle("cellhead", fontName="Hei", fontSize=8.7, leading=13.4, textColor=NAVY)


def P(s, style=body):
    return Paragraph(s, style)


def linked(name, url):
    return f'<link href="{escape(url)}" color="#087E80">{escape(name)}</link>'


def block(text, bg=PALEBLUE, border=BORDER, pad=9):
    t = Table([[P(text)]], colWidths=[180*mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.65, border),
        ("LEFTPADDING", (0, 0), (-1, -1), pad),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
    ]))
    return t


def paper_card(num, name, venue, layer, direction, contribution, url):
    head = P(f'<b>[{num:02d}] {linked(name, url)}</b> <font color="#536678">· {escape(venue)} · {escape(layer)}</font>', cardtitle)
    text = P(f'<font color="#536678">研究方向：</font>{escape(direction)}<br/><font color="#087E80">创新点：</font>{escape(contribution)}', cardbody)
    tbl = Table([[head], [text]], colWidths=[180*mm], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.65, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    return KeepTogether([tbl, Spacer(1, 5)])


PAPERS = [
    (1, "HaWoR", "CVPR 2025", "状态恢复", "从第一视角视频恢复世界坐标中的连续手运动。", "相机轨迹与手部重建解耦，并补全出画或遮挡时的手运动。", "https://openaccess.thecvf.com/content/CVPR2025/html/Zhang_HaWoR_World-Space_Hand_Motion_Reconstruction_from_Egocentric_Videos_CVPR_2025_paper.html"),
    (2, "BIGS", "CVPR 2025", "状态恢复", "单目双手与未知物体的三维交互重建。", "3D Gaussian 手物表示结合手模型与生成先验，联合优化遮挡下的手物对齐。", "https://openaccess.thecvf.com/content/CVPR2025/html/On_BIGS_Bimanual_Category-agnostic_Interaction_Reconstruction_from_Monocular_Videos_via_3D_CVPR_2025_paper.html"),
    (3, "HOT3D", "CVPR 2025", "数据与真值", "为第一视角多视图手物跟踪提供基准。", "光学动捕标记得到手和物体逐帧位姿，提供 UmeTrack/MANO 与物体网格；人工质检有效帧。", "https://arxiv.org/html/2406.09598"),
    (4, "OAKINK2", "CVPR 2024", "任务语义", "表示双手、多物体、长时序操作。", "以可供性、基本任务、复杂任务的层级组织轨迹，适合抽取接触事件和双手角色。", "https://openaccess.thecvf.com/content/CVPR2024/html/Zhan_OAKINK2_A_Dataset_of_Bimanual_Hands-Object_Manipulation_in_Complex_Task_CVPR_2024_paper.html"),
    (5, "2HandedAfforder", "ICCV 2025", "接触候选", "从人类视频预测双手可操作区域。", "把物体区域与双手动作语义关联，输出比普通分割更适合执行的可供性目标。", "https://openaccess.thecvf.com/content/ICCV2025/html/Heidinger_2HandedAfforder_Learning_Precise_Actionable_Bimanual_Affordances_from_Human_Videos_ICCV_2025_paper.html"),
    (18, "WHOLE", "CVPR Findings 2026", "联合状态恢复", "遮挡与出画条件下重建世界坐标手物轨迹。", "手物联合运动先验以视频观测引导生成，使相对关系更连续；依赖物体模板。", "https://openaccess.thecvf.com/content/CVPR2026F/html/Ye_WHOLE_World-Grounded_Hand-Object_Lifted_from_Egocentric_Videos_CVPRF_2026_paper.html"),
    (6, "DexMV", "ECCV 2022", "视频到机器人", "将人手视频转成灵巧手模仿学习示范。", "手物三维姿态估计、仿真重定向、机器人策略训练构成早期完整基线。", "https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136990562.pdf"),
    (7, "Learning to Transfer Human Hand Skills", "ICRA 2025", "学习式迁移", "解决形态差异下的动作映射。", "合成人手、物体、机械手轨迹三元组，学习三者联合运动流形。", "https://arxiv.org/abs/2501.04169"),
    (8, "Cross-Embodiment Dexterous Grasping", "ICLR 2025", "统一动作空间", "让一套抓取策略跨不同灵巧手使用。", "人手 eigengrasp 作共享动作表示，再映射到不同手型。", "https://proceedings.iclr.cc/paper_files/paper/2025/hash/ca8c6f28d8ba1e732e3f217ab05c4ec0-Abstract-Conference.html"),
    (19, "UniDex", "CVPR 2026", "跨手型策略", "从 Ego 视频构造多种灵巧手训练数据。", "有人参与的接触保持重定向、共享功能执行器空间与跨手型策略学习。", "https://openaccess.thecvf.com/content/CVPR2026/html/Zhang_UniDex_A_Robot_Foundation_Suite_for_Universal_Dexterous_Hand_Control_CVPR_2026_paper.html"),
    (9, "ManipTrans", "CVPR 2025", "双手物理迁移", "让双手重定向动作在接触中稳定执行。", "通用模仿器加残差策略，修正双手配合、物体跟踪与接触误差。", "https://openaccess.thecvf.com/content/CVPR2025/html/Li_ManipTrans_Efficient_Dexterous_Bimanual_Manipulation_Transfer_via_Residual_Learning_CVPR_2025_paper.html"),
    (10, "DexTrack", "ICLR 2025", "轨迹控制", "大量人手参考下训练可泛化灵巧控制器。", "成功轨迹、模仿学习、强化学习与逐轨迹同伦优化形成训练循环。", "https://proceedings.iclr.cc/paper_files/paper/2025/hash/d5a1f97d2b922da92e880d13b7d2bf02-Abstract-Conference.html"),
    (11, "Dexplore", "CoRL 2025", "参考约束控制", "降低重定向、跟踪、残差三阶段的误差累积。", "以时变空间范围替代硬轨迹约束，在单个 RL 循环中探索，再蒸馏视觉策略。", "https://proceedings.mlr.press/v305/xu25d.html"),
    (12, "DexMimicGen", "ICRA 2025", "仿真数据扩增", "从少量双臂示范生成大规模机器人演示。", "分段组合、轨迹变换和仿真筛选；60 条源演示扩增至 2 万余条。", "https://dexmimicgen.github.io/"),
    (13, "CyberDemo", "CVPR 2024", "仿真到真实", "用仿真示范训练实机灵巧操作。", "联合扩增视觉、物理和任务条件，提高示范覆盖面。", "https://openaccess.thecvf.com/content/CVPR2024/html/Wang_CyberDemo_Augmenting_Simulated_Human_Demonstration_for_Real-World_Dexterous_Manipulation_CVPR_2024_paper.html"),
    (14, "DexUMI", "CoRL 2025", "视觉与具身对齐", "缩小人手演示到机械手的运动及视觉差。", "外骨骼约束可执行运动并提供触觉反馈，视频补绘把人手换为机械手。", "https://proceedings.mlr.press/v305/xu25b.html"),
    (16, "RoboTwin", "CVPR 2025", "数字孪生与评测", "构建可扩展双臂仿真和实机基准。", "生成数字孪生场景、任务演示和多样化评测条件。", "https://openaccess.thecvf.com/content/CVPR2025/html/Mu_RoboTwin_Dual-Arm_Robot_Benchmark_with_Generative_Digital_Twins_CVPR_2025_paper.html"),
    (15, "Human2Sim2Robot", "CoRL 2025", "少演示实机学习", "仅用一次人类 RGB-D 演示训练机器人。", "物体轨迹构成具身无关奖励，演示前手姿态引导仿真 RL。", "https://proceedings.mlr.press/v305/lum25a.html"),
    (17, "ViViDex", "ICRA 2025", "视觉策略与验证", "从人类视频训练可执行视觉灵巧策略。", "先用轨迹奖励学习仿真状态策略，再采集视觉观测训练视觉策略。", "https://arxiv.org/abs/2404.15709"),
]

assert len(PAPERS) == 19
assert sorted(row[0] for row in PAPERS) == list(range(1, 20))


class BriefDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(str(filename), pagesize=A4, leftMargin=15*mm, rightMargin=15*mm,
                         topMargin=19*mm, bottomMargin=15*mm, title="跨具身双臂灵巧手：论文流程与创新点简报",
                         author="研究文献整理")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="brief", frames=[frame], onPage=self.decorate))

    def decorate(self, canv, doc):
        canv.saveState()
        w, h = A4
        canv.setFillColor(NAVY)
        canv.rect(0, h-9*mm, w, 9*mm, fill=1, stroke=0)
        canv.setFont("Hei", 7.4)
        canv.setFillColor(MUTED)
        canv.drawString(15*mm, 9*mm, "Ego-to-Dexterous Learning  |  研究简报  |  2026-10-24")
        canv.drawRightString(w-15*mm, 9*mm, f"{doc.page}")
        canv.restoreState()


story = []
story += [Spacer(1, 3*mm), P("跨具身双臂灵巧手动作迁移", title),
          P("19 篇论文在整体流程中的位置、已有创新与可借鉴方案", subtitle), Spacer(1, 5*mm)]

story.append(P("一、研究流程与论文分布", section))
steps = [
    ("① Ego 采集", "人手视频、相机位姿"),
    ("② 手物恢复", "双手/物体轨迹、接触候选"),
    ("③ 跨具身迁移", "双臂末端、灵巧手动作"),
    ("④ 物理执行", "接触、碰撞、稳定性"),
    ("⑤ 数据生成", "机器人视角、多模态标签"),
    ("⑥ 实机适配", "少量试验、失败修正"),
]
rows = [[P(f'<b>{a}</b><br/>{b}', small) for a, b in steps[:3]],
        [P(f'<b>{a}</b><br/>{b}', small) for a, b in steps[3:]]]
flow = Table(rows, colWidths=[60*mm]*3, hAlign="LEFT")
flow.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (2, 0), PALEBLUE),
    ("BACKGROUND", (0, 1), (2, 1), PALE),
    ("BOX", (0, 0), (-1, -1), .7, BORDER),
    ("INNERGRID", (0, 0), (-1, -1), .6, BORDER),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
]))
story += [flow, Spacer(1, 4*mm),
          block("<b>阅读方法：</b>每篇先看它解决哪个环节的问题，再看具体方法。论文中的“创新点”指相对该论文已有工作的贡献，不代表今天仍无人覆盖。标题可点击进入原始论文页面。", PALE, BORDER, 8),
          P("二、论文速览：感知、状态与任务语义", section)]
for row in PAPERS[:6]:
    story.append(paper_card(*row))

story += [PageBreak(), P("三、论文速览：动作迁移与物理执行", section),
          P("从人手参考到机器人可执行动作：这些论文主要在表示、接触约束和控制器训练上创新。", small), Spacer(1, 3*mm)]
for row in PAPERS[6:13]:
    story.append(paper_card(*row))
story += [Spacer(1, 2*mm), block("<b>边界：</b>把接触加到重定向、给轨迹加残差策略，已经有直接先例。进一步工作要说明接触事件如何被诊断、主动试验和跨任务复用。", AMBER_BG, colors.HexColor("#E9D4A7"), 8)]

story += [PageBreak(), P("四、论文速览：仿真数据与实机验证", section),
          P("该层把迁移动作变成可训练的数据，并检验仿真结果能否在实机复现。", small), Spacer(1, 3*mm)]
for row in PAPERS[13:]:
    story.append(paper_card(*row))
story += [Spacer(1, 2*mm), block("<b>与课题的关系：</b>DexMimicGen 提供数据扩增与筛选思路；DexUMI 解决视觉具身差；Human2Sim2Robot 与 ViViDex 提供少演示和视觉策略基线。现有工作并未自动回答“哪一次实机试验最值得做”。", PALE, BORDER, 8)]

story += [PageBreak(), P("五、之前预选的三个创新点", section)]
ideas = [
    ("方向 1｜机器人可行性驱动的双手接触事件重规划",
     "把人类动作表达为‘支撑、操作、交接、释放’等事件；在机械臂可达性、接触稳定和物体结果约束下，调整双手角色、接触位置与时序。",
     "接触结构优化已有 C2Dex、TopoRetarget、ObjRetarget 等先例；须证明事件级规划在完整双臂任务上的独立收益。"),
    ("方向 2｜将 Ego 感知不确定性传到重定向",
     "视频看不清指尖或物体时保留多个接触假设，在仿真中比较可行性，必要时由短时机器人探测消除歧义。",
     "难点是可校准的不确定度与可区分的动作后果；仅输出多条候选轨迹不构成充分贡献。"),
    ("方向 3｜固定实机预算下的接触事件主动校准  ★ 当前优先",
     "在少量实机尝试内，自动选最能区分失败原因的短操作片段；仅校准可辨识的参数，并把校准量复用到相似接触事件。",
     "已有 ReDex 用人工手指修正接触失败。新增量应由自动选段、失败诊断、跨任务复用及单位实机成本的收益共同支撑。"),
]
for i, (name, approach, boundary) in enumerate(ideas):
    color = PALE if i == 2 else PALEBLUE
    story += [block(f'<b>{escape(name)}</b><br/>{escape(approach)}<br/><font color="#536678">已有工作与验证门槛：{escape(boundary)}</font>', color, BORDER, 9), Spacer(1, 3*mm)]
story += [P("为何优先方向 3", subsection),
          P("你目前实机资源有限。方向 3 可先在仿真中注入几何偏差、闭合不足与双手启动时序误差，完成选段算法及消融；实机只承担少量关键验证。它的关键风险是：如果视觉和关节状态无法区分失败原因，就只能校准更低维、更可观测的量。", body),
          Spacer(1, 3*mm),
          block("<b>拟定研究问题：</b>给定一条由人类演示迁移得到的双臂灵巧操作策略，以及严格限定的实机试验时间，如何自动选择接触事件片段、判断可校准的误差，并使修正对未见任务有效？", AMBER_BG, colors.HexColor("#E9D4A7"), 9),
          Spacer(1, 3*mm),
          P("近期重叠工作（预印本）：" + linked("C2Dex", "https://arxiv.org/abs/2608.07045") + "、" + linked("TopoRetarget", "https://arxiv.org/abs/2606.16272") + "、" + linked("ObjRetarget", "https://arxiv.org/abs/2607.03828") + "、" + linked("EgoMatrix", "https://arxiv.org/abs/2610.18822") + "。", small)]

story += [PageBreak(), P("六、方向 3 可以借鉴哪些论文", section),
          P("按可直接拿来搭建模块的程度排序。下述‘借鉴’是方法启发，不等于原论文已完成你的目标。", small), Spacer(1, 3*mm)]

borrow = [
    ("ReDex", "实机接触故障的局部修正：保留原策略，只校正出问题的手指或动作段；借其失效类型、记录字段与比较协议。", "其修正由人选择并施加；拟研究自动选哪段、改哪个参数。", "https://arxiv.org/abs/2610.07525"),
    ("ManipTrans [09]", "残差修正与双手物体跟踪奖励，可作为待校准的仿真基策略。", "残差训练本身不是新点。", PAPERS[10][6]),
    ("OAKINK2 [04]", "基本任务和双手角色的层级，定义支撑、操作、交接、释放等事件边界。", "需要建立适用于机器人试验的可观测事件判据。", PAPERS[3][6]),
    ("DexMimicGen [12]", "分段示范、任务重置和可控仿真扩增，用来生成候选短片段及失败分布。", "主动选段需与随机片段、完整任务重跑比较。", PAPERS[13][6]),
    ("Human2Sim2Robot [15]", "用物体轨迹定义任务结果，降低对人体关节对齐的依赖。", "物体结果指标不能单独定位接触失败。", PAPERS[17][6]),
    ("DexSim2Real^2", "主动交互后更新物体模型，提示用短试验辨识环境误差。", "其目标是关节物体数字孪生；此处聚焦双手接触事件。", "https://arxiv.org/abs/2409.08750"),
    ("C2Dex", "接触一致性重建、重定向与残差优化，可作校准前端的近期强基线。", "这些模块已覆盖流程前段，拟研究从其输出之后开始。", "https://arxiv.org/abs/2608.07045"),
    ("EgoMatrix", "Ego 视频到双手机器人轨迹及配对机器人视角观测的数据引擎，可作完整前端基线。", "该预印本已覆盖数据生成；拟研究其实机接触校准。", "https://arxiv.org/abs/2610.18822"),
]

for name, take, limit, url in borrow:
    story.append(block(f'<b>{linked(name, url)}</b><br/>{escape(take)}<br/><font color="#536678">边界：{escape(limit)}</font>', PALEBLUE, BORDER, 6))
    story.append(Spacer(1, 2.5*mm))

story += [P("最小可行实验", subsection),
          P("<b>观测：</b>外部相机、机器人关节状态、物体位姿；若无触觉，先不宣称辨识接触力或摩擦系数。<br/><b>校准量：</b>支撑手闭合幅度、操作手启动时刻、双手相对位姿偏置。<br/><b>选段：</b>在仿真中对每类误差做扰动，选择预期能最大地区分误差且重置成本低的片段；仅更新可辨识量。<br/><b>对照：</b>无校准、随机选段、整任务示范微调、人工选段。固定总实机时间和重置次数。<br/><b>指标：</b>单位实机分钟成功率增益、校准后成功率、未见物体/任务的迁移增益，以及失败类型识别准确率。", body),
          Spacer(1, 3*mm),
          P("来源说明：论文 [01]–[19] 为本地已下载的正式会议论文，个别 PDF 使用公开作者版；WHOLE 为 CVPR Findings。ReDex、DexSim2Real²、C2Dex、TopoRetarget、ObjRetarget、EgoMatrix 是补充阅读，按 2026-10-24 可核查的公开页面标注，不把预印本写成正式会议成果。", small)]

doc = BriefDoc(OUTPUT)
doc.build(story)
print(OUTPUT)
