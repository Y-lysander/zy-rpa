"""虚拟 AI 中药大模型 —— 本地模拟实现。

本项目当前不接入任何真实云端模型。本模块以「关键词打分 + 经典方库」的
规则引擎模拟"模型依据患者输入开出药方"的回复内容，返回结构化的药方 JSON。

未来接入真实供应商时，只需将 :func:`mock_complete` 替换为对应的真实 API
调用即可，请求/响应 schema(pydantic) 不变。
"""
from __future__ import annotations

import random
import re
from typing import Any

MODEL_NAME = "mock-tcm-herbalist-v1"


def promt_quote_field(label: str, value: str) -> str:
    """把输入字段组装成提示词中的一段（缺省字段不写入提示词）。"""
    value = (value or "").strip()
    return f"{label}：{value}\n" if value else ""


def build_prompt(data: dict[str, Any]) -> str:
    """把结构化表单输入组装成一段"开方提示词"(单次对话，不询问、直接开方)。

    与真实模型交互时即把此提示词发送给模型；虚拟引擎仅解析其中的结构化
    字段用于开方，刻意忽略"不得询问"类指令以贴近真实模型行为。
    """
    fields = [
        ("患者主诉/症状", "symptoms"),
        ("现病史", "history"),
        ("当前用药", "current_meds"),
        ("年龄/性别", "age_gender"),
        ("体质", "constitution"),
        ("过敏史", "allergies"),
        ("舌象脉象", "tongue_pulse"),
        ("经带情况", "menstruation"),
        ("生活习惯", "lifestyle"),
    ]
    lines = ["# 任务：请对以下患者开出中药方", "# 要求：直接给出完整药方，不得反问提问。"]
    lines += [promt_quote_field(label, data.get(k)) for label, k in fields]
    if data.get("decoct"):
        lines.append("煎服提示：患者需代煎。\n")
    return "".join(lines)


# ---------------------------------------------------------------------------
# 经典方库（模拟用）：命中主治关键词加分，命中禁忌词扣分。
# 每个方：name 方名 | principle 辨证/治法 | keywords 主治词 | dirty 倾向词 |
#        avoid 禁忌词 | herbs 组成(药名, 剂量, 单位) | decoction 煎服法
# ---------------------------------------------------------------------------
_HERBS = [
    ("桂枝汤", "解肌发表，调和营卫",
     ["风寒", "恶风", "汗出", "发热", "头痛", "鼻塞", "脉浮缓", "怕风", "受凉感冒"],
     ["脉浮缓", "汗出"],
     ["高热", "咽痛剧烈", "口渴", "脉洪", "温病", "风热"],
     [("桂枝", "9", "g"), ("白芍", "9", "g"), ("生姜", "3", "g"),
      ("大枣", "4", "枚"), ("炙甘草", "6", "g")],
     "水煎服，温覆取微汗，忌生冷油腻。"),

    ("银翘散", "辛凉解表，清热解毒",
     ["风热", "咽痛", "口渴", "发热", "咳嗽", "黄痰", "舌红", "脉浮数", "热感冒"],
     ["咽痛", "口渴", "黄痰"],
     ["畏寒明显", "清涕", "便溏"],
     [("金银花", "15", "g"), ("连翘", "15", "g"), ("桔梗", "6", "g"),
      ("薄荷", "3", "g"), ("竹叶", "6", "g"), ("牛蒡子", "10", "g"),
      ("荆芥穗", "9", "g"), ("淡豆豉", "9", "g"), ("甘草", "5", "g")],
     "水煎服，宜凉服，勿久煎。"),

    ("小柴胡汤", "和解少阳，疏利枢机",
     ["往来寒热", "口苦", "咽干", "目眩", "胸胁苦满", "默默不欲饮食", "心烦喜呕"],
     ["口苦", "胸胁胀满"],
     ["胃寒明显", "便溏"],
     [("柴胡", "12", "g"), ("黄芩", "9", "g"), ("人参", "6", "g"),
      ("半夏", "9", "g"), ("炙甘草", "6", "g"), ("生姜", "3", "g"),
      ("大枣", "4", "枚")],
     "水煎服，早晚温服。"),

    ("逍遥散", "疏肝解郁，养血健脾",
     ["肝郁", "气滞", "情志不舒", "胁胀", "善太息", "月经不调", "乳房胀痛",
      "烦躁", "抑郁", "偏头痛"],
     ["胁胀", "太息", "郁"],
     None,
     [("柴胡", "9", "g"), ("当归", "9", "g"), ("白芍", "9", "g"),
      ("白术", "9", "g"), ("茯苓", "9", "g"), ("炙甘草", "6", "g"),
      ("薄荷", "3", "g"), ("生姜", "3", "g")],
     "水煎服，经前可连服。"),

    ("六君子汤", "益气健脾，燥湿化痰",
     ["脾虚", "气虚", "食少", "腹胀", "便溏", "倦怠", "乏力", "痰多",
      "面色萎黄", "咳嗽痰白"],
     ["乏力", "食少", "便溏"],
     ["咽燥口干", "舌红少苔"],
     [("党参", "15", "g"), ("白术", "12", "g"), ("茯苓", "12", "g"),
      ("炙甘草", "6", "g"), ("陈皮", "9", "g"), ("半夏", "9", "g")],
     "水煎服，忌滋腻碍胃之品。"),

    ("归脾汤", "益气补血，健脾养心",
     ["心脾两虚", "心悸", "失眠", "健忘", "多梦", "体倦", "食少", "便血",
      "月经量多", "崩漏", "面色无华"],
     ["心悸", "失眠", "健忘"],
     ["口苦咽干", "舌红"],
     [("党参", "15", "g"), ("白术", "12", "g"), ("黄芪", "15", "g"),
      ("当归", "9", "g"), ("茯神", "12", "g"), ("远志", "6", "g"),
      ("酸枣仁", "15", "g"), ("龙眼肉", "9", "g"), ("木香", "6", "g"),
      ("炙甘草", "6", "g"), ("大枣", "4", "枚"), ("生姜", "3", "g")],
     "水煎服，晚饭后温服。"),

    ("血府逐瘀汤", "活血化瘀，行气止痛",
     ["血瘀", "刺痛", "固定痛", "胸痛", "头痛日久", "舌紫暗", "瘀斑",
      "面色晦暗", "痛经有块", "外伤后遗"],
     ["刺痛", "舌紫暗"],
     ["出血倾向", "孕妇", "经期量多"],
     [("桃仁", "10", "g"), ("红花", "6", "g"), ("当归", "9", "g"),
      ("川芎", "6", "g"), ("赤芍", "9", "g"), ("生地", "9", "g"),
      ("牛膝", "9", "g"), ("柴胡", "6", "g"), ("桔梗", "6", "g"),
      ("枳壳", "9", "g"), ("甘草", "5", "g")],
     "水煎服，空腹温服，孕妇禁用。"),

    ("六味地黄丸", "滋补肝肾，填精益髓",
     ["肾阴虚", "腰膝酸软", "耳鸣", "盗汗", "骨蒸潮热", "遗精", "五心烦热",
      "头晕", "口燥咽干", "舌红少苔"],
     ["腰膝酸软", "盗汗", "五心烦热"],
     ["畏寒肢冷", "便溏", "脘腹胀满"],
     [("熟地黄", "20", "g"), ("山茱萸", "12", "g"), ("山药", "12", "g"),
      ("泽泻", "9", "g"), ("牡丹皮", "9", "g"), ("茯苓", "9", "g")],
     "水煎服或为丸，早晚各一次温服。"),

    ("温胆汤", "理气和胃，清胆和胃",
     ["痰热", "胆虚", "惊悸", "不寐", "多梦", "口苦", "恶心", "呕恶",
      "苔黄腻", "口黏", "心烦"],
     ["苔黄腻", "恶心", "惊悸"],
     ["畏寒便溏", "舌淡"],
     [("半夏", "9", "g"), ("竹茹", "9", "g"), ("枳实", "9", "g"),
      ("陈皮", "9", "g"), ("茯苓", "12", "g"), ("甘草", "5", "g"),
      ("生姜", "3", "g"), ("大枣", "4", "枚")],
     "水煎服，睡前温服。"),

    ("半夏泻心汤", "寒热平调，消痞散结",
     ["心下痞", "痞满", "呕吐", "肠鸣", "泄泻", "胃脘痞塞", "苔黄腻",
      "气痞"],
     ["心下痞", "肠鸣", "泄泻"],
     ["脾胃虚寒畏冷"],
     [("半夏", "12", "g"), ("黄芩", "9", "g"), ("干姜", "9", "g"),
      ("党参", "9", "g"), ("炙甘草", "6", "g"), ("黄连", "3", "g"),
      ("大枣", "4", "枚")],
     "水煎服，温凉适中。"),
]

# 通用加减模板：症状关键词 -> 加减药建议
_ADJUST = [
    (["失眠", "多梦", "惊悸", "易醒"], "加酸枣仁、柏子仁以宁心安神"),
    (["咳嗽", "痰多"], "加杏仁、前胡以宣肺化痰"),
    (["咽痛", "咽干"], "加桔梗、玄参以利咽"),
    (["痹痛", "关节痛", "肌肉酸痛"], "加秦艽、威灵仙以祛风通络"),
    (["腹泻", "便溏", "泄泻"], "加山药、白扁豆以健脾止泻"),
    (["便秘"], "加火麻仁、瓜蒌以润肠通便"),
    (["口渴", "口燥"], "加天花粉、麦冬以生津"),
    (["血瘀", "刺痛"], "加丹参、赤芍以活血"),
    (["浮肿", "水肿"], "加猪苓、泽泻以利水"),
    (["恶寒", "畏寒", "怕冷"], "加附子、干姜以温阳"),
    (["自汗", "汗出"], "加黄芪、浮小麦以固表止汗"),
    (["头晕", "眩晕"], "加天麻、钩藤以平肝熄风"),
    (["痞满", "胃胀", "腹胀"], "加砂仁、厚朴以行气消胀"),
    (["呕吐", "恶心"], "加生姜、半夏以和胃降逆"),
]


def _hit(keywords, text: str) -> bool:
    return any(k in text for k in keywords)


def score_herb(herb, text_symptoms: str, text_tongue: str) -> float:
    """给单个方打分：主治命中加分、禁忌命中扣大分、舌脉倾向词加权。"""
    score = 0.0
    sy, tongue = text_symptoms, (text_tongue or "")
    for k in herb[2] or []:
        if k in sy:
            score += 1.5
            if k in (herb[3] or []):
                score += 1.0       # 关键倾向词额外加权
    for k in herb[3] or []:
        if tongue and k in tongue:
            score += 2.0
    for k in herb[4] or []:
        if k in sy or (tongue and k in tongue):
            score -= 5.0           # 命中禁忌，显著降权
    return score


def _pick_primary(scores: dict) -> str:
    return max(scores, key=scores.get)


def generate_prescription(data: dict[str, Any]) -> dict[str, Any]:
    """核心开方逻辑：根据输入字段打分选出主方，并给出加减建议。"""
    symptoms = (data.get("symptoms") or "").strip()
    tongue = (data.get("tongue_pulse") or "").strip()
    if not symptoms:
        raise ValueError("symptoms 不能为空")

    scores = {h[0]: score_herb(h, symptoms, tongue) for h in _HERBS}
    best = _pick_primary({k: v for k, v in scores.items() if v > -3})
    # 无显著命中时兜底：选择负权分最高者(症状最少冲突)并标注"基础调理方"
    if not best:
        best = max(_HERBS, key=lambda h: score_herb(h, symptoms, tongue))[0]
        fallback_base = True
    else:
        fallback_base = False

    h = next(x for x in _HERBS if x[0] == best)
    _, principle, _, _, _, herbs, base_deco = h

    # 加减建议：取输入中命中的、且不在该方主治里的加减项
    adjust = []
    for pat, sug in _ADJUST:
        if any(p in symptoms for p in pat) and not _hit(h[2], "".join(pat)):
            adjust.append(sug)

    # 煎服
    if data.get("decoct"):
        deco = f"{base_deco} 遵医嘱代煎，分次温服。"
    else:
        deco = base_deco

    multi_kw = ["兼", "同见", "又有", "且见", "伴", "同时"]
    multi = any(k in symptoms for k in multi_kw)

    if not fallback_base and adjust:
        note = "；".join(adjust[:2])
        modifier = f"随证加减：{note}。"
    else:
        modifier = "本例以平正立法，暂不加减，随诊随调。"

    return {
        "prescription_name": best + ("合方" if multi else ""),
        "principle": principle + "，随证调理" if fallback_base else principle,
        "herbs": [{"name": n, "dose": d, "unit": u} for n, d, u in herbs],
        "dosage_count": str(random.randint(3, 7)),
        "decoction": deco,
        "contraindications": "忌生冷、油腻、辛辣；服药期间如感不适请停用并及时就医。",
        "modifications": modifier,
        "warnings": "以上为虚拟模型模拟生成的开方内容，仅供功能演示，不构成医疗建议。",
        "model": MODEL_NAME,
    }


def mock_complete(data: dict[str, Any]) -> dict[str, Any]:
    """模拟模型"单次对话开方"入口：忽略对话历史，仅按当前输入开方。"""
    build_prompt(data)            # 组装提示词(为真实模型预留)
    return generate_prescription(data)


# ---------------------------------------------------------------------------
# 药方识别（模拟）：本地药材知识库 + 整方文本提取。
# 每味药：nature 性味 | meridian 归经 | effects 功效 | notes 使用注意
# ---------------------------------------------------------------------------
_HERB_INFO: dict[str, dict[str, str]] = {
    "桂枝": {"nature": "辛、甘，温", "meridian": "心、肺、膀胱经",
             "effects": "发汗解肌，温通经脉，助阳化气。",
             "notes": "温热病及阴虚阳盛者忌用，孕妇慎用。"},
    "白芍": {"nature": "苦、酸，微寒", "meridian": "肝、脾经",
             "effects": "养血调经，敛阴止汗，柔肝止痛，平抑肝阳。",
             "notes": "虚寒性腹痛泄泻者慎用；反藜芦。"},
    "生姜": {"nature": "辛，微温", "meridian": "肺、脾、胃经",
             "effects": "解表散寒，温中止呕，化痰止咳，解鱼蟹毒。",
             "notes": "阴虚内热者忌用。"},
    "大枣": {"nature": "甘，温", "meridian": "脾、胃、心经",
             "effects": "补中益气，养血安神。",
             "notes": "湿盛脘腹胀满者慎用。"},
    "甘草": {"nature": "甘，平", "meridian": "心、肺、脾、胃经",
             "effects": "补脾益气，清热解毒，祛痰止咳，缓急止痛，调和诸药。",
             "notes": "反海藻、大戟、甘遂、芫花；久服大剂量可致浮肿。"},
    "炙甘草": {"nature": "甘，平", "meridian": "心、肺、脾、胃经",
               "effects": "补脾和胃，益气复脉。",
               "notes": "同甘草，反海藻、大戟、甘遂、芫花。"},
    "金银花": {"nature": "甘，寒", "meridian": "肺、心、胃经",
               "effects": "清热解毒，疏散风热。",
               "notes": "脾胃虚寒者慎用。"},
    "连翘": {"nature": "苦，微寒", "meridian": "肺、心、小肠经",
              "effects": "清热解毒，消肿散结，疏散风热。",
              "notes": "脾胃虚寒及气虚脓清者不宜。"},
    "桔梗": {"nature": "苦、辛，平", "meridian": "肺经",
             "effects": "宣肺，祛痰，利咽，排脓。",
             "notes": "阴虚久嗽及咯血者忌用。"},
    "薄荷": {"nature": "辛，凉", "meridian": "肺、肝经",
             "effects": "疏散风热，清利头目，利咽透疹，疏肝行气。",
             "notes": "体虚多汗者不宜。"},
    "竹叶": {"nature": "甘、淡，寒", "meridian": "心、肺、胃经",
             "effects": "清热泻火，除烦生津，利尿。",
             "notes": "阴虚火旺者不宜久用。"},
    "牛蒡子": {"nature": "辛、苦，寒", "meridian": "肺、胃经",
               "effects": "疏散风热，宣肺透疹，解毒利咽。",
               "notes": "气虚便溏者慎用。"},
    "荆芥穗": {"nature": "辛，微温", "meridian": "肺、肝经",
               "effects": "解表散风，透疹，消疮。",
               "notes": "表虚自汗者慎用。"},
    "淡豆豉": {"nature": "苦、辛，凉", "meridian": "肺、胃经",
               "effects": "解表，除烦，宣发郁热。",
               "notes": "无郁热者慎用。"},
    "柴胡": {"nature": "苦、辛，微寒", "meridian": "肝、胆经",
             "effects": "解表退热，疏肝解郁，升举阳气。",
             "notes": "肝阳上亢、阴虚火旺者忌用。"},
    "黄芩": {"nature": "苦，寒", "meridian": "肺、胆、脾、大肠、小肠经",
             "effects": "清热燥湿，泻火解毒，止血，安胎。",
             "notes": "脾胃虚寒者不宜。"},
    "人参": {"nature": "甘、微苦，微温", "meridian": "脾、肺、心、肾经",
             "effects": "大补元气，复脉固脱，补脾益肺，生津养血，安神益智。",
             "notes": "实证、热证忌用；反藜芦。"},
    "半夏": {"nature": "辛，温，有毒", "meridian": "脾、胃、肺经",
             "effects": "燥湿化痰，降逆止呕，消痞散结。",
             "notes": "阴虚燥咳、血证、热痰者忌用；反乌头。"},
    "当归": {"nature": "甘、辛，温", "meridian": "肝、心、脾经",
             "effects": "补血活血，调经止痛，润肠通便。",
             "notes": "湿盛中满、大便溏泄者慎用。"},
    "白术": {"nature": "甘、苦，温", "meridian": "脾、胃经",
             "effects": "健脾益气，燥湿利水，止汗，安胎。",
             "notes": "阴虚内热、津液亏耗者慎用。"},
    "茯苓": {"nature": "甘、淡，平", "meridian": "心、肺、脾、肾经",
             "effects": "利水渗湿，健脾，宁心。",
             "notes": "虚寒精滑者忌服。"},
    "陈皮": {"nature": "苦、辛，温", "meridian": "肺、脾经",
             "effects": "理气健脾，燥湿化痰。",
             "notes": "气虚及阴虚燥咳者慎用。"},
    "党参": {"nature": "甘，平", "meridian": "脾、肺经",
             "effects": "补脾肺气，补血，生津。",
             "notes": "实证、热证者慎用；反藜芦。"},
    "黄芪": {"nature": "甘，微温", "meridian": "脾、肺经",
             "effects": "补气升阳，固表止汗，利水消肿，生津养血，托毒排脓。",
             "notes": "表实邪盛、气滞湿阻、阴虚阳亢者不宜。"},
    "茯神": {"nature": "甘、淡，平", "meridian": "心、脾经",
             "effects": "宁心安神，利水渗湿。",
             "notes": "同茯苓，虚寒精滑者忌服。"},
    "远志": {"nature": "苦、辛，温", "meridian": "心、肾、肺经",
             "effects": "安神益智，交通心肾，祛痰，消肿。",
             "notes": "有胃炎及胃溃疡者慎用。"},
    "酸枣仁": {"nature": "甘、酸，平", "meridian": "心、肝、胆经",
               "effects": "养心补肝，宁心安神，敛汗，生津。",
               "notes": "有实邪郁火者慎用。"},
    "龙眼肉": {"nature": "甘，温", "meridian": "心、脾经",
               "effects": "补益心脾，养血安神。",
               "notes": "湿盛中满、痰火者慎用。"},
    "木香": {"nature": "辛、苦，温", "meridian": "脾、胃、大肠、胆经",
             "effects": "行气止痛，健脾消食。",
             "notes": "阴虚津亏者慎用。"},
    "桃仁": {"nature": "苦、甘，平，有小毒", "meridian": "心、肝、大肠经",
             "effects": "活血祛瘀，润肠通便，止咳平喘。",
             "notes": "孕妇忌用，便溏者慎用。"},
    "红花": {"nature": "辛，温", "meridian": "心、肝经",
             "effects": "活血通经，散瘀止痛。",
             "notes": "孕妇忌用，有出血倾向者慎用。"},
    "川芎": {"nature": "辛，温", "meridian": "肝、胆、心包经",
             "effects": "活血行气，祛风止痛。",
             "notes": "阴虚火旺、月经过多者慎用，孕妇慎用。"},
    "赤芍": {"nature": "苦，微寒", "meridian": "肝经",
             "effects": "清热凉血，散瘀止痛。",
             "notes": "血虚者慎用；反藜芦。"},
    "生地": {"nature": "甘、苦，寒", "meridian": "心、肝、肾经",
             "effects": "清热凉血，养阴生津。",
             "notes": "脾虚湿滞、腹满便溏者不宜。"},
    "牛膝": {"nature": "苦、甘、酸，平", "meridian": "肝、肾经",
             "effects": "逐瘀通经，补肝肾，强筋骨，引血下行。",
             "notes": "孕妇及月经过多者忌用。"},
    "熟地黄": {"nature": "甘，微温", "meridian": "肝、肾经",
               "effects": "补血滋阴，益精填髓。",
               "notes": "脾胃虚弱、气滞痰多、腹满便溏者忌用。"},
    "山茱萸": {"nature": "酸、涩，微温", "meridian": "肝、肾经",
               "effects": "补益肝肾，收涩固脱。",
               "notes": "命门火炽、素有湿热及小便不利者不宜。"},
    "山药": {"nature": "甘，平", "meridian": "脾、肺、肾经",
             "effects": "补脾养胃，生津益肺，补肾涩精。",
             "notes": "湿盛中满或有积滞者不宜。"},
    "泽泻": {"nature": "甘、淡，寒", "meridian": "肾、膀胱经",
             "effects": "利水渗湿，泄热，化浊降脂。",
             "notes": "肾虚精滑无湿热者忌用。"},
    "牡丹皮": {"nature": "苦、辛，微寒", "meridian": "心、肝、肾经",
               "effects": "清热凉血，活血化瘀。",
               "notes": "血虚有寒、月经过多及孕妇不宜。"},
    "黄连": {"nature": "苦，寒", "meridian": "心、脾、胃、肝、胆、大肠经",
             "effects": "清热燥湿，泻火解毒。",
             "notes": "脾胃虚寒者忌用；苦燥易伤阴津。"},
    "干姜": {"nature": "辛，热", "meridian": "脾、胃、肾、心、肺经",
             "effects": "温中散寒，回阳通脉，温肺化饮。",
             "notes": "阴虚内热、血热妄行者忌用。"},
    "玄参": {"nature": "甘、苦、咸，微寒", "meridian": "肺、胃、肾经",
             "effects": "清热凉血，滋阴降火，解毒散结。",
             "notes": "脾胃虚寒、便溏者忌用；反藜芦。"},
    "麦冬": {"nature": "甘、微苦，微寒", "meridian": "心、肺、胃经",
             "effects": "养阴生津，润肺清心。",
             "notes": "风寒感冒、痰湿咳嗽者忌用。"},
    "天花粉": {"nature": "甘、微苦，微寒", "meridian": "肺、胃经",
               "effects": "清热泻火，生津止渴，消肿排脓。",
               "notes": "孕妇忌用。"},
    "丹参": {"nature": "苦，微寒", "meridian": "心、肝经",
             "effects": "活血祛瘀，通经止痛，清心除烦，凉血消痈。",
             "notes": "无瘀血者慎用；反藜芦。"},
    "砂仁": {"nature": "辛，温", "meridian": "脾、胃、肾经",
             "effects": "化湿开胃，温脾止泻，理气安胎。",
             "notes": "阴虚有热者慎用。"},
    "厚朴": {"nature": "苦、辛，温", "meridian": "脾、胃、肺、大肠经",
             "effects": "燥湿消痰，下气除满。",
             "notes": "气虚津亏者慎用，孕妇慎用。"},
    "火麻仁": {"nature": "甘，平", "meridian": "脾、胃、大肠经",
               "effects": "润肠通便。",
               "notes": "大量服用可引起中毒，孕妇慎用。"},
    "瓜蒌": {"nature": "甘、微苦，寒", "meridian": "肺、胃、大肠经",
             "effects": "清热涤痰，宽胸散结，润燥滑肠。",
             "notes": "反乌头；脾虚便溏者慎用。"},
    "杏仁": {"nature": "苦，微温，有小毒", "meridian": "肺、大肠经",
             "effects": "降气止咳平喘，润肠通便。",
             "notes": "有小毒，不宜过量；阴虚咳嗽者慎用。"},
    "前胡": {"nature": "苦、辛，微寒", "meridian": "肺经",
             "effects": "降气化痰，散风清热。",
             "notes": "阴虚气弱、无外感痰热者慎用。"},
    "秦艽": {"nature": "苦、辛，平", "meridian": "胃、肝、胆经",
             "effects": "祛风湿，清湿热，止痹痛，退虚热。",
             "notes": "久痛虚羸、溲多便溏者慎用。"},
    "威灵仙": {"nature": "辛、咸，温", "meridian": "膀胱经",
               "effects": "祛风除湿，通络止痛。",
               "notes": "气血虚弱者慎用，忌茶。"},
    "附子": {"nature": "辛、甘，大热，有毒", "meridian": "心、肾、脾经",
             "effects": "回阳救逆，补火助阳，散寒止痛。",
             "notes": "有毒，须炮制并先煎；孕妇忌用；反半夏、瓜蒌、贝母、白蔹、白及。"},
    "浮小麦": {"nature": "甘，凉", "meridian": "心经",
               "effects": "固表止汗，益气，除热。",
               "notes": "无虚汗者慎用。"},
    "天麻": {"nature": "甘，平", "meridian": "肝经",
             "effects": "息风止痉，平抑肝阳，祛风通络。",
             "notes": "气血虚甚者慎用。"},
    "钩藤": {"nature": "甘，凉", "meridian": "肝、心包经",
             "effects": "息风定惊，清热平肝。",
             "notes": "无风热及实热者慎用。"},
    "柏子仁": {"nature": "甘，平", "meridian": "心、肾、大肠经",
               "effects": "养心安神，润肠通便，止汗。",
               "notes": "便溏多痰者慎用。"},
    "猪苓": {"nature": "甘、淡，平", "meridian": "肾、膀胱经",
             "effects": "利水渗湿。",
             "notes": "无水湿者不宜久用。"},
    "白扁豆": {"nature": "甘，微温", "meridian": "脾、胃经",
               "effects": "健脾化湿，和中消暑。",
               "notes": "外感寒邪及疟疾者不宜。"},
}

# 十八反/十九畏（简化）：识别到下列组合时在配伍解析中给出禁忌提示
_CONFLICTS = [
    (("甘草", "炙甘草"), ("海藻", "大戟", "甘遂", "芫花")),
    (("附子", "川乌", "草乌"), ("半夏", "瓜蒌", "贝母", "白蔹", "白及")),
    (("藜芦",), ("人参", "党参", "玄参", "丹参", "沙参", "白芍", "赤芍", "细辛")),
]

_TOXIC_HERBS = {name for name, info in _HERB_INFO.items() if "有毒" in info["nature"]}


def build_recognize_prompt(data: dict[str, Any]) -> str:
    """把待识别药材组装成一段"识别提示词"（为真实模型预留，本地引擎忽略指令）。"""
    herbs = [h for h in (data.get("herbs") or []) if str(h.get("name") or "").strip()]
    lines = ["# 任务：请分析下列药材的性味归经、功效主治与配伍禁忌",
             "# 要求：逐味返回结构化结果，另附配伍解析与煎服建议。"]
    if herbs:
        rows = ["；".join(f"{h.get('name')} {h.get('dose') or ''}{h.get('unit') or ''}"
                         for h in herbs if str(h.get("name") or "").strip())]
        lines.append("药材清单：" + rows[0])
    if (data.get("full_text") or "").strip():
        lines.append("整方原文：\n" + data["full_text"].strip())
    return "\n".join(lines)


def _extract_herbs_from_text(text: str) -> list[dict]:
    """从整方文本中按已知药名（长名优先）提取药材与剂量，返回 [{name, dose, unit}]。"""
    if not text:
        return []
    names = sorted(_HERB_INFO, key=len, reverse=True)
    pat = re.compile("|".join(re.escape(n) for n in names))
    found = []
    for m in pat.finditer(text):
        tail = text[m.end():m.end() + 14]
        dm = re.match(r"\s*(\d+(?:\.\d+)?)\s*(克|g|G|毫克|毫升|ml|枚|片|包|剂|钱)?", tail)
        if dm:
            dose, unit = dm.group(1), (dm.group(2) or "g")
        else:
            dose, unit = "", ""
        found.append({"name": m.group(0), "dose": dose, "unit": unit})
    return found


def _conflict_hints(names: list[str]) -> list[str]:
    hints = []
    for group_a, group_b in _CONFLICTS:
        hits_a = [n for n in names if n in group_a]
        hits_b = [n for n in names if n in group_b]
        if hits_a and hits_b:
            hints.append(f"“{hits_a[0]}”与“{hits_b[0]}”属配伍禁忌（十八反/十九畏），请务必复核。")
    return hints


def mock_recognize(data: dict[str, Any]) -> dict[str, Any]:
    """模拟"药方识别"入口：逐味分析药效，附配伍解析与煎服建议。"""
    build_recognize_prompt(data)          # 组装提示词（为真实模型预留）
    herbs: list[dict] = []
    for h in data.get("herbs") or []:
        if str(h.get("name") or "").strip():
            herbs.append(h)
    if (data.get("full_text") or "").strip():
        herbs += _extract_herbs_from_text(data["full_text"])

    # 去重（保留首次出现，保持录入顺序）
    seen: set[str] = set()
    merged: list[dict] = []
    for h in herbs:
        name = str(h.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        merged.append({"name": name,
                       "dose": str(h.get("dose") or "").strip(),
                       "unit": str(h.get("unit") or "g").strip()})
    if not merged:
        raise ValueError("未识别到任何药材，请检查输入。")

    entries = []
    for h in merged:
        info = _HERB_INFO.get(h["name"])
        entries.append({
            **h,
            "nature_flavor": info["nature"] if info else "",
            "meridian": info["meridian"] if info else "",
            "effects": (info["effects"] if info
                        else "（本地库暂未收录该药材，接入真实模型后可查询药效）"),
            "notes": info["notes"] if info else "",
        })

    names = [e["name"] for e in entries]
    conflicts = _conflict_hints(names)

    # 配伍解析：按药性寒温做粗略归纳 + 禁忌提示
    warm = sum(1 for e in entries if any(k in e["nature_flavor"] for k in ("温", "热")))
    cool = sum(1 for e in entries if any(k in e["nature_flavor"] for k in ("寒", "凉")))
    if warm and not cool:
        tendency = f"{warm} 味偏温/热，全方以温补散寒为总体倾向"
    elif cool and not warm:
        tendency = f"{cool} 味偏寒/凉，全方以清热泻火为总体倾向"
    elif warm and cool:
        tendency = f"温药 {warm} 味、寒凉药 {cool} 味兼见，寒热并用，需注意相互制约"
    else:
        tendency = "药性以平和为主，未呈现明显寒热偏倾"
    interaction_parts = [f"本方共 {len(entries)} 味药，{tendency}。"]
    if conflicts:
        interaction_parts.append("配伍禁忌提醒：" + "".join(conflicts))
    else:
        interaction_parts.append("未检出十八反/十九畏等明显配伍禁忌，但用药仍应结合辨证审慎。")
    interaction = "".join(interaction_parts)

    # 煎服确认
    toxic = [e["name"] for e in entries if e["name"] in _TOXIC_HERBS]
    if toxic:
        decoction = (f"建议水煎服，一日一剂，分早晚两次温服。"
                     f"注意：含毒性药材（{'、'.join(toxic)}），须遵医嘱炮制、先煎并严格控制用量。")
    else:
        decoction = "建议水煎服，一日一剂，分早晚两次温服，饭后半小时服用，忌生冷油腻。"

    return {
        "herbs": entries,
        "interaction": interaction,
        "decoction": decoction,
        "warnings": "以上为虚拟模型模拟生成的识别内容，仅供功能演示，不构成医疗建议。",
        "model": MODEL_NAME,
    }


# ---------------------------------------------------------------------------
# AI 助手对话（模拟）：系统提示词 + 规则引擎回复。
# 接入真实模型时，把 CHAT_SYSTEM_PROMPT 作为 system 消息拼接在对话最前，
# 将整个消息列表交给模型即可，返回 schema 不变。
# ---------------------------------------------------------------------------
CHAT_SYSTEM_PROMPT = (
    "# 角色\n"
    "你是一位经验丰富的中医师，是「智能中药开方系统」的 AI 助手，"
    "精通中医基础理论、中药学、方剂学与辨证论治。\n"
    "# 职责\n"
    "1. 解答用户关于中药、方剂、症状调理、养生保健等中医相关问题；\n"
    "2. 解释开方/识别结果中的疑问，说明药性、配伍、煎服方法与注意事项；\n"
    "3. 涉及用药的建议须审慎，明确提示需由执业中医师辨证审核。\n"
    "# 要求\n"
    "- 回答精炼准确，先给结论再展开；\n"
    "- 涉及剂量与配伍时给出安全提示；\n"
    "- 不夸大疗效、不承诺治愈；\n"
    "- 无法判断或超出中医范围时如实说明。"
)


def _chat_reply(question: str) -> str:
    """规则引擎回复：按「药材 → 方剂 → 症状辨证 → 问候 → 兜底」依次匹配。"""
    q = (question or "").strip()

    # 1) 药材问答：命中本地知识库中的药名
    for name, info in _HERB_INFO.items():
        if name in q:
            return (f"关于「{name}」：\n"
                    f"· 性味：{info['nature']}\n"
                    f"· 归经：{info['meridian']}\n"
                    f"· 功效：{info['effects']}\n"
                    f"· 注意：{info['notes']}\n\n"
                    "提示：以上为中药学知识介绍，具体用药请由执业中医师辨证后决定。")

    # 2) 方剂问答：命中经典方库中的方名
    for h in _HERBS:
        if h[0] in q:
            herbs = "、".join(f"{n}{d}{u}" for n, d, u in h[5])
            return (f"「{h[0]}」为经典方剂，主要思路是「{h[1]}」。\n"
                    f"组成：{herbs}。\n"
                    f"煎服：{h[6]}\n\n"
                    "提示：方剂需在辨证准确的前提下使用，建议由中医师审定。")

    # 3) 症状辨证：按主治关键词推荐可能合适的经典方剂
    hits = [h[0] for h in _HERBS if any(k in q for k in (h[2] or []))]
    if hits:
        return (f"根据您描述的症状，可参考以下经典方剂：{'、'.join(hits[:3])}。\n"
                "各方的适应证与禁忌不同，建议补充体质、舌脉等信息后由中医师辨证选方。")

    # 4) 问候语
    if any(w in q for w in ("你好", "您好", "在吗", "嗨", "hello", "hi")):
        return ("你好，我是中药 AI 助手，可以为您解答中药、方剂、症状调理等方面的问题。"
                "请描述您的情况或直接提问。")

    # 5) 兜底引导
    return ("这个问题需要中医辨证后回答，我可以从以下方面帮助您：\n"
            "· 查询药材性味归经与功效（如：桂枝有什么功效？）\n"
            "· 了解经典方剂（如：逍遥散适合什么证？）\n"
            "· 根据症状提示调理方向（如：失眠多梦怎么办？）\n\n"
            "请换个更具体的问题，或前往「药方开方」填写病情信息，由 AI 为您开方。")


def mock_chat(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """模拟 AI 助手对话：取最近一条用户消息做规则回复（为真实模型预留对话格式）。"""
    user_msgs = [m for m in (messages or [])
                 if isinstance(m, dict) and m.get("role") == "user"
                 and str(m.get("content") or "").strip()]
    question = user_msgs[-1].get("content", "") if user_msgs else ""
    return {
        "reply": _chat_reply(question),
        "model": MODEL_NAME,
    }