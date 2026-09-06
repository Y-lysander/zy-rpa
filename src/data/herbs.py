"""常用中药材名录（静态数据）。

供「药方识别」逐项录入时做中文/拼音模糊联想，覆盖常用中药约 340 味，
按使用频度大致排序（越常用越靠前），并包含本地识别引擎所收录的全部药材。

每个条目为 ``(名称, 拼音)``：拼音按字空格分隔（如 桂枝 -> "gui zhi"），
首字母索引由拼音自动推导，无需手工维护。
"""
from __future__ import annotations

# (药名, 全拼，按字空格分隔)
_HERB_ITEMS: list[tuple[str, str]] = [
    # ---- 解表药 ----
    ("桂枝", "gui zhi"), ("麻黄", "ma huang"), ("白芍", "bai shao"),
    ("生姜", "sheng jiang"), ("防风", "fang feng"), ("荆芥", "jing jie"),
    ("白芷", "bai zhi"), ("羌活", "qiang huo"), ("紫苏叶", "zi su ye"),
    ("细辛", "xi xin"), ("香薷", "xiang ru"), ("藁本", "gao ben"),
    ("苍耳子", "cang er zi"), ("辛夷", "xin yi"), ("薄荷", "bo he"),
    ("牛蒡子", "niu bang zi"), ("蝉蜕", "chan tui"), ("桑叶", "sang ye"),
    ("菊花", "ju hua"), ("蔓荆子", "man jing zi"), ("柴胡", "chai hu"),
    ("升麻", "sheng ma"), ("葛根", "ge gen"), ("淡豆豉", "dan dou chi"),
    ("浮萍", "fu ping"),
    # ---- 清热药 ----
    ("石膏", "shi gao"), ("知母", "zhi mu"), ("芦根", "lu gen"),
    ("天花粉", "tian hua fen"), ("竹叶", "zhu ye"), ("栀子", "zhi zi"),
    ("夏枯草", "xia ku cao"), ("决明子", "jue ming zi"), ("黄芩", "huang qin"),
    ("黄连", "huang lian"), ("黄柏", "huang bai"), ("龙胆草", "long dan cao"),
    ("秦皮", "qin pi"), ("苦参", "ku shen"), ("白鲜皮", "bai xian pi"),
    ("金银花", "jin yin hua"), ("连翘", "lian qiao"), ("蒲公英", "pu gong ying"),
    ("紫花地丁", "zi hua di ding"), ("野菊花", "ye ju hua"),
    ("穿心莲", "chuan xin lian"), ("大青叶", "da qing ye"),
    ("板蓝根", "ban lan gen"), ("青黛", "qing dai"), ("贯众", "guan zhong"),
    ("鱼腥草", "yu xing cao"), ("射干", "she gan"), ("白头翁", "bai tou weng"),
    ("马齿苋", "ma chi xian"), ("鸦胆子", "ya dan zi"),
    ("生地黄", "sheng di huang"), ("玄参", "xuan shen"), ("牡丹皮", "mu dan pi"),
    ("赤芍", "chi shao"), ("紫草", "zi cao"), ("水牛角", "shui niu jiao"),
    ("青蒿", "qing hao"), ("地骨皮", "di gu pi"), ("白薇", "bai wei"),
    ("银柴胡", "yin chai hu"), ("胡黄连", "hu huang lian"),
    # ---- 泻下药 ----
    ("大黄", "da huang"), ("芒硝", "mang xiao"), ("番泻叶", "fan xie ye"),
    ("芦荟", "lu hui"), ("火麻仁", "huo ma ren"), ("郁李仁", "yu li ren"),
    ("松子仁", "song zi ren"), ("甘遂", "gan sui"), ("大戟", "da ji"),
    ("芫花", "yuan hua"), ("牵牛子", "qian niu zi"), ("巴豆", "ba dou"),
    # ---- 祛风湿药 ----
    ("独活", "du huo"), ("威灵仙", "wei ling xian"), ("川乌", "chuan wu"),
    ("草乌", "cao wu"), ("蕲蛇", "qi she"), ("乌梢蛇", "wu shao she"),
    ("木瓜", "mu gua"), ("蚕沙", "can sha"), ("秦艽", "qin jiao"),
    ("防己", "fang ji"), ("桑枝", "sang zhi"), ("豨莶草", "xi xian cao"),
    ("臭梧桐", "chou wu tong"), ("海桐皮", "hai tong pi"),
    ("络石藤", "luo shi teng"), ("徐长卿", "xu chang qing"),
    ("桑寄生", "sang ji sheng"), ("五加皮", "wu jia pi"), ("狗脊", "gou ji"),
    # ---- 化湿药 ----
    ("藿香", "huo xiang"), ("佩兰", "pei lan"), ("苍术", "cang zhu"),
    ("厚朴", "hou po"), ("砂仁", "sha ren"), ("白豆蔻", "bai dou kou"),
    ("草豆蔻", "cao dou kou"), ("草果", "cao guo"),
    # ---- 利水渗湿药 ----
    ("茯苓", "fu ling"), ("猪苓", "zhu ling"), ("泽泻", "ze xie"),
    ("薏苡仁", "yi yi ren"), ("车前子", "che qian zi"), ("滑石", "hua shi"),
    ("木通", "mu tong"), ("通草", "tong cao"), ("瞿麦", "qu mai"),
    ("萹蓄", "bian xu"), ("地肤子", "di fu zi"), ("海金沙", "hai jin sha"),
    ("石韦", "shi wei"), ("冬葵子", "dong kui zi"), ("灯心草", "deng xin cao"),
    ("茵陈", "yin chen"), ("金钱草", "jin qian cao"), ("虎杖", "hu zhang"),
    ("垂盆草", "chui pen cao"),
    # ---- 温里药 ----
    ("附子", "fu zi"), ("干姜", "gan jiang"), ("肉桂", "rou gui"),
    ("吴茱萸", "wu zhu yu"), ("小茴香", "xiao hui xiang"), ("丁香", "ding xiang"),
    ("高良姜", "gao liang jiang"), ("花椒", "hua jiao"), ("胡椒", "hu jiao"),
    ("荜茇", "bi ba"), ("荜澄茄", "bi cheng qie"), ("炮姜", "pao jiang"),
    # ---- 理气药 ----
    ("陈皮", "chen pi"), ("青皮", "qing pi"), ("枳实", "zhi shi"),
    ("枳壳", "zhi ke"), ("木香", "mu xiang"), ("沉香", "chen xiang"),
    ("檀香", "tan xiang"), ("香附", "xiang fu"), ("川楝子", "chuan lian zi"),
    ("乌药", "wu yao"), ("荔枝核", "li zhi he"), ("佛手", "fo shou"),
    ("香橼", "xiang yuan"), ("玫瑰花", "mei gui hua"), ("绿萼梅", "lv e mei"),
    ("薤白", "xie bai"), ("青木香", "qing mu xiang"), ("大腹皮", "da fu pi"),
    ("柿蒂", "shi di"), ("刀豆", "dao dou"),
    # ---- 消食药 ----
    ("山楂", "shan zha"), ("神曲", "shen qu"), ("麦芽", "mai ya"),
    ("谷芽", "gu ya"), ("莱菔子", "lai fu zi"), ("鸡内金", "ji nei jin"),
    ("阿魏", "a wei"),
    # ---- 驱虫药 ----
    ("使君子", "shi jun zi"), ("苦楝皮", "ku lian pi"), ("槟榔", "bing lang"),
    ("南瓜子", "nan gua zi"), ("鹤草芽", "he cao ya"), ("雷丸", "lei wan"),
    ("鹤虱", "he shi"), ("榧子", "fei zi"),
    # ---- 止血药 ----
    ("大蓟", "da ji"), ("小蓟", "xiao ji"), ("地榆", "di yu"),
    ("槐花", "huai hua"), ("侧柏叶", "ce bai ye"), ("白茅根", "bai mao gen"),
    ("苎麻根", "zhu ma gen"), ("三七", "san qi"), ("茜草", "qian cao"),
    ("蒲黄", "pu huang"), ("花蕊石", "hua rui shi"), ("白及", "bai ji"),
    ("仙鹤草", "xian he cao"), ("紫珠", "zi zhu"), ("棕榈炭", "zong lv tan"),
    ("血余炭", "xue yu tan"), ("藕节", "ou jie"),
    # ---- 活血化瘀药 ----
    ("川芎", "chuan xiong"), ("延胡索", "yan hu suo"), ("郁金", "yu jin"),
    ("姜黄", "jiang huang"), ("乳香", "ru xiang"), ("没药", "mo yao"),
    ("五灵脂", "wu ling zhi"), ("丹参", "dan shen"), ("红花", "hong hua"),
    ("桃仁", "tao ren"), ("益母草", "yi mu cao"), ("泽兰", "ze lan"),
    ("牛膝", "niu xi"), ("鸡血藤", "ji xue teng"),
    ("王不留行", "wang bu liu xing"), ("月季花", "yue ji hua"),
    ("凌霄花", "ling xiao hua"), ("土鳖虫", "tu bie chong"),
    ("自然铜", "zi ran tong"), ("苏木", "su mu"), ("骨碎补", "gu sui bu"),
    ("血竭", "xue jie"), ("莪术", "e zhu"), ("三棱", "san leng"),
    ("水蛭", "shui zhi"), ("虻虫", "meng chong"), ("穿山甲", "chuan shan jia"),
    # ---- 化痰止咳平喘药 ----
    ("半夏", "ban xia"), ("天南星", "tian nan xing"), ("禹白附", "yu bai fu"),
    ("白芥子", "bai jie zi"), ("皂荚", "zao jia"), ("旋覆花", "xuan fu hua"),
    ("白前", "bai qian"), ("前胡", "qian hu"), ("桔梗", "jie geng"),
    ("川贝母", "chuan bei mu"), ("浙贝母", "zhe bei mu"), ("瓜蒌", "gua lou"),
    ("竹茹", "zhu ru"), ("竹沥", "zhu li"), ("天竺黄", "tian zhu huang"),
    ("海藻", "hai zao"), ("昆布", "kun bu"), ("黄药子", "huang yao zi"),
    ("海蛤壳", "hai ge ke"), ("胖大海", "pang da hai"),
    ("苦杏仁", "ku xing ren"), ("紫苏子", "zi su zi"), ("百部", "bai bu"),
    ("紫菀", "zi wan"), ("款冬花", "kuan dong hua"), ("马兜铃", "ma dou ling"),
    ("枇杷叶", "pi pa ye"), ("桑白皮", "sang bai pi"),
    ("葶苈子", "ting li zi"), ("白果", "bai guo"), ("洋金花", "yang jin hua"),
    # ---- 安神药 ----
    ("朱砂", "zhu sha"), ("磁石", "ci shi"), ("龙骨", "long gu"),
    ("琥珀", "hu po"), ("酸枣仁", "suan zao ren"), ("柏子仁", "bai zi ren"),
    ("灵芝", "ling zhi"), ("缬草", "xie cao"), ("首乌藤", "shou wu teng"),
    ("合欢皮", "he huan pi"), ("远志", "yuan zhi"),
    # ---- 平肝息风药 ----
    ("石决明", "shi jue ming"), ("珍珠母", "zhen zhu mu"), ("牡蛎", "mu li"),
    ("紫贝齿", "zi bei chi"), ("代赭石", "dai zhe shi"), ("刺蒺藜", "ci ji li"),
    ("罗布麻", "luo bu ma"), ("羚羊角", "ling yang jiao"), ("牛黄", "niu huang"),
    ("珍珠", "zhen zhu"), ("钩藤", "gou teng"), ("天麻", "tian ma"),
    ("地龙", "di long"), ("全蝎", "quan xie"), ("蜈蚣", "wu gong"),
    ("僵蚕", "jiang can"),
    # ---- 开窍药 ----
    ("麝香", "she xiang"), ("冰片", "bing pian"), ("苏合香", "su he xiang"),
    ("石菖蒲", "shi chang pu"),
    # ---- 补虚药 ----
    ("人参", "ren shen"), ("西洋参", "xi yang shen"), ("党参", "dang shen"),
    ("太子参", "tai zi shen"), ("黄芪", "huang qi"), ("白术", "bai zhu"),
    ("山药", "shan yao"), ("白扁豆", "bai bian dou"), ("甘草", "gan cao"),
    ("炙甘草", "zhi gan cao"), ("大枣", "da zao"), ("饴糖", "yi tang"),
    ("蜂蜜", "feng mi"), ("鹿茸", "lu rong"), ("巴戟天", "ba ji tian"),
    ("淫羊藿", "yin yang huo"), ("仙茅", "xian mao"), ("补骨脂", "bu gu zhi"),
    ("益智仁", "yi zhi ren"), ("肉苁蓉", "rou cong rong"), ("锁阳", "suo yang"),
    ("菟丝子", "tu si zi"), ("沙苑子", "sha yuan zi"), ("杜仲", "du zhong"),
    ("续断", "xu duan"), ("韭菜子", "jiu cai zi"), ("蛤蚧", "ge jie"),
    ("冬虫夏草", "dong chong xia cao"), ("核桃仁", "he tao ren"),
    ("紫河车", "zi he che"), ("当归", "dang gui"), ("熟地黄", "shu di huang"),
    ("何首乌", "he shou wu"), ("阿胶", "e jiao"), ("龙眼肉", "long yan rou"),
    ("北沙参", "bei sha shen"), ("南沙参", "nan sha shen"), ("百合", "bai he"),
    ("麦冬", "mai dong"), ("天冬", "tian dong"), ("石斛", "shi hu"),
    ("玉竹", "yu zhu"), ("黄精", "huang jing"), ("枸杞子", "gou qi zi"),
    ("墨旱莲", "mo han lian"), ("女贞子", "nv zhen zi"), ("桑椹", "sang shen"),
    ("黑芝麻", "hei zhi ma"), ("龟甲", "gui jia"), ("鳖甲", "bie jia"),
    # ---- 收涩药 ----
    ("麻黄根", "ma huang gen"), ("浮小麦", "fu xiao mai"),
    ("糯稻根", "nuo dao gen"), ("五味子", "wu wei zi"), ("乌梅", "wu mei"),
    ("五倍子", "wu bei zi"), ("罂粟壳", "ying su ke"), ("诃子", "he zi"),
    ("石榴皮", "shi liu pi"), ("肉豆蔻", "rou dou kou"),
    ("山茱萸", "shan zhu yu"), ("覆盆子", "fu pen zi"),
    ("桑螵蛸", "sang piao xiao"), ("金樱子", "jin ying zi"),
    ("海螵蛸", "hai piao xiao"), ("莲子", "lian zi"), ("芡实", "qian shi"),
    ("椿皮", "chun pi"), ("鸡冠花", "ji guan hua"),
    # ---- 涌吐药 ----
    ("常山", "chang shan"), ("瓜蒂", "gua di"), ("胆矾", "dan fan"),
    # ---- 攻毒杀虫止痒及其他常用药 ----
    ("硫黄", "liu huang"), ("雄黄", "xiong huang"), ("蛇床子", "she chuang zi"),
    ("土荆皮", "tu jing pi"), ("白矾", "bai fan"), ("大蒜", "da suan"),
    ("蟾酥", "chan su"), ("马钱子", "ma qian zi"), ("斑蝥", "ban mao"),
    ("炉甘石", "lu gan shi"), ("硼砂", "peng sha"), ("砒石", "pi shi"),
    ("木蝴蝶", "mu hu die"), ("紫石英", "zi shi ying"),
]


def _to_initials(pinyin: str) -> str:
    """由全拼推导首字母，如 'gui zhi' -> 'gz'。"""
    return "".join(p[0] for p in pinyin.split() if p)


# 统一结构：name 名称 | pinyin 全拼（去空格） | initials 首字母
HERBS: list[dict[str, str]] = [
    {"name": name, "pinyin": pinyin.replace(" ", ""), "initials": _to_initials(pinyin)}
    for name, pinyin in _HERB_ITEMS
]

HERB_NAMES: list[str] = [h["name"] for h in HERBS]


def _rank(name: str, pinyin: str, initials: str, q: str) -> int:
    """匹配评分：数值越小越靠前；-1 表示不匹配。"""
    if name.startswith(q):
        return 0
    if q in name:
        return 1
    if initials.startswith(q):
        return 2
    if pinyin.startswith(q):
        return 3
    if q in initials:
        return 4
    if q in pinyin:
        return 5
    return -1


def search(query: str, limit: int = 8) -> list[str]:
    """按中文/全拼/首字母模糊匹配药材名，返回至多 limit 个，按匹配度排序。

    - 中文：子串匹配（前缀优先），如 "桂" -> 桂枝；
    - 拼音：全拼前缀/子串，如 "gui" -> 桂枝；
    - 首字母：如 "gz" -> 桂枝；
    - 复合串回退：整串不匹配时取首段再匹配，如 "人参 renshen rs" / "gui zhi"
      这类带空格/拼音/首字母的复合输入仍能命中对应药材。
    """
    q = "".join((query or "").lower().split())
    if not q:
        return []
    results = _match(q, limit)
    if results:
        return results
    tokens = (query or "").split()
    if len(tokens) > 1:
        return _match(tokens[0].lower(), limit)
    return []


def _match(q: str, limit: int) -> list[str]:
    scored = []
    for h in HERBS:
        score = _rank(h["name"], h["pinyin"], h["initials"], q)
        if score >= 0:
            scored.append((score, h["name"]))
    scored.sort(key=lambda x: (x[0], HERB_NAMES.index(x[1])))
    return [name for _, name in scored[:limit]]
