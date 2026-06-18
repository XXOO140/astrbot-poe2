"""
PoE2 中文翻译模块
数据来源: PoE2 说中文 Chrome 扩展
支持: 简体中文 / 繁体中文 / English
"""

import json
import os

# 翻译数据文件路径
_translations_file = os.path.join(os.path.dirname(__file__), 'translations_from_extension.json')

# 缓存翻译数据
_translations_cache = None

_TW_TO_CN_MAP = {
    '製': '制', '體': '体', '國': '国', '說': '说', '學': '学',
    '點': '点', '時': '时', '開': '开', '關': '关', '問': '问',
    '實': '实', '際': '际', '對': '对', '經': '经', '動': '动',
    '現': '现', '環': '环', '護': '护', '變': '变', '導': '导',
    '戰': '战', '歷': '历', '擊': '击', '續': '续', '質': '质',
    '機': '机', '壓': '压', '響': '响', '覺': '觉', '聯': '联',
    '節': '节', '層': '层', '還': '还', '區': '区', '驗': '验',
    '據': '据', '構': '构', '認': '认', '積': '积', '運': '运',
    '農': '农', '網': '网', '電': '电', '龍': '龙', '鳴': '鸣',
    '鐵': '铁', '鎖': '锁', '鏈': '链', '鑰': '钥', '門': '门',
    '關': '关', '闆': '板', '隱': '隐', '障': '障', '難': '难',
    '雲': '云', '靈': '灵', '韻': '韵', '響': '响', '預': '预',
    '額': '额', '顯': '显', '風': '风', '飛': '飞', '餘': '余',
    '養': '养', '駕': '驾', '驅': '驱', '騎': '骑', '驚': '惊',
    '驗': '验', '鱗': '鳞', '鳥': '鸟', '鶴': '鹤', '鷹': '鹰',
    '麗': '丽', '麥': '麦', '黃': '黄', '齒': '齿', '齡': '龄',
    '龜': '龟', '寶': '宝', '將': '将', '專': '专', '尋': '寻',
    '導': '导', '彈': '弹', '徹': '彻', '憶': '忆', '應': '恼',
    '戀': '恋', '懲': '惩', '懼': '惧', '戲': '戏', '戴': '戴',
    '擇': '择', '擬': '拟', '擁': '拥', '擊': '击', '操': '操',
    '擔': '担', '據': '据', '擴': '扩', '擲': '掷', '擷': '撷',
    '擺': '摆', '擻': '挬', '擾': '扰', '攝': '摄', '攜': '携',
    '攝': '摄', '攢': '攒', '支': '支', '收': '收', '改': '改',
    '攻': '攻', '放': '放', '政': '政', '故': '故', '效': '效',
    '敵': '敌', '數': '数', '整': '整', '敵': '敌', '敷': '敷',
    '文': '文', '斗': '斗', '料': '料', '斜': '斜', '斷': '断',
    '旁': '旁', '旅': '旅', '旋': '旋', '族': '族', '旌': '旌',
    '無': '无', '炬': '炬', '炎': '炎', '爐': '炉', '爭': '争',
    '爲': '为', '爵': '爵', '牌': '牌', '牒': '牒', '牙': '牙',
    '牛': '牛', '牢': '牢', '牧': '牧', '物': '物', '特': '特',
    '犧': '牺', '狀': '状', '獵': '猎', '獻': '献', '獸': '兽',
    '玄': '玄', '率': '率', '玉': '玉', '王': '王', '玩': '玩',
    '現': '现', '球': '球', '理': '理', '瓶': '瓶', '產': '产',
    '畫': '画', '異': '异', '當': '当', '發': '发', '盜': '盗',
    '盤': '盘', '盛': '盛', '盡': '尽', '監': '监', '目': '目',
    '直': '直', '相': '相', '盾': '盾', '省': '省', '看': '看',
    '真': '真', '眼': '眼', '著': '着', '睡': '睡', '督': '督',
    '睛': '睛', '瞭': '了', '知': '知', '石': '石', '碎': '碎',
    '磚': '砖', '礦': '矿', '禮': '礼', '禦': '御', '離': '离',
    '難': '难', '雙': '双', '雜': '杂', '靜': '静', '非': '非',
    '面': '面', '革': '革', '靴': '靴', '鞋': '鞋', '韓': '韩',
    '音': '音', '頁': '页', '頃': '顷', '項': '项', '順': '顺',
    '須': '须', '頌': '颂', '預': '预', '領': '领', '頭': '头',
    '頻': '频', '顆': '颗', '題': '题', '顏': '颜', '願': '愿',
    '顧': '顾', '類': '类', '顧': '顾', '風': '风', '飛': '飞',
    '食': '食', '飢': '饥', '飲': '饮', '飾': '饰', '餃': '饺',
    '餅': '饼', '餘': '余', '餐': '餐', '餵': '喂', '餿': '馊',
    '饅': '馒', '饑': '饥', '饒': '饶', '首': '首', '香': '香',
    '馬': '马', '馱': '驮', '馴': '驯', '駕': '驾', '駐': '驻',
    '駱': '骆', '駭': '骇', '騎': '骑', '騙': '骗', '騰': '腾',
    '驅': '驱', '驕': '骄', '驗': '验', '驚': '惊', '骯': '肮',
    '髏': '髅', '髒': '脏', '體': '体', '高': '高', '髮': '发',
    '鬥': '斗', '鬧': '闹', '鬱': '郁', '鬼': '鬼', '魁': '魁',
    '魂': '魂', '魄': '魄', '魚': '鱼', '魯': '鲁', '鮑': '鲍',
    '鮮': '鲜', '鯉': '鲤', '鯊': '鲨', '鯨': '鲸', '鳥': '鸟',
    '鳳': '凤', '鳴': '鸣', '鴉': '鸦', '鴻': '鸿', '鵑': '鹃',
    '鵝': '鹅', '鶴': '鹤', '鷗': '鸥', '鷹': '鹰', '鸚': '鹦',
    '鸞': '鸾', '黃': '黄', '黌': '黉', '黎': '黎', '黑': '黑',
    '點': '点', '黨': '党', '鼓': '鼓', '鼠': '鼠', '鼻': '鼻',
    '齊': '齐', '齋': '斋', '齒': '齿', '齡': '龄', '龍': '龙',
    '龐': '庞', '龜': '龟', '廳': '厅', '廢': '废', '廣': '广',
    '廟': '庙', '廠': '厂', '廚': '厨', '廝': '厮', '廬': '庐',
    '廳': '厅', '延': '延', '建': '建', '開': '开', '間': '间',
    '閉': '闭', '閉': '闭', '閃': '闪', '閉': '闭', '閏': '闰',
    '閑': '闲', '閒': '闲', '閘': '闸', '閙': '闹', '閡': '碍',
    '閣': '阁', '閥': '阀', '閨': '闺', '閩': '闽', '閪': '閪',
    '閬': '阆', '閭': '闾', '閱': '阅', '閲': '阅', '閶': '阊',
    '閹': '阉', '閻': '阎', '閼': '阏', '閽': '阍', '閾': '阈',
    '閿': '阌', '闃': '阒', '闆': '板', '闈': '闱', '闉': '闉',
    '闊': '阔', '闋': '阕', '闌': '阑', '闍': '阇', '闐': '阗',
    '闑': '闑', '闒': '闒', '闓': '闿', '闔': '阖', '闕': '阙',
    '闖': '闯', '闗': '关', '闘': '斗', '關': '关', '闚': '窥',
    '闛': '闛', '關': '关', '闞': '阚', '闟': '闟', '闠': '闠',
    '闡': '阐', '闢': '辟', '闤': '闤', '闥': '闼',
}


def _tw_to_cn(text: str) -> str:
    """将繁体中文转换为简体中文"""
    result = []
    for ch in text:
        result.append(_TW_TO_CN_MAP.get(ch, ch))
    return ''.join(result)


def _load_translations():
    """加载翻译数据"""
    global _translations_cache
    if _translations_cache is not None:
        return _translations_cache
    
    try:
        with open(_translations_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _translations_cache = data.get('translations', {})
            return _translations_cache
    except Exception as e:
        print(f"[Translations] Load error: {e}")
        _translations_cache = {}
        return _translations_cache


def get_zh_cn(english_name: str) -> str:
    """获取简体中文翻译，zh_cn为空时回退到zh_tw"""
    translations = _load_translations()
    entry = translations.get(english_name, {})
    zh_cn = entry.get('zh_cn', '')
    if zh_cn:
        return zh_cn
    zh_tw = entry.get('zh_tw', '')
    if zh_tw:
        return _tw_to_cn(zh_tw)
    return english_name


def get_zh_tw(english_name: str) -> str:
    """获取繁体中文翻译"""
    translations = _load_translations()
    entry = translations.get(english_name, {})
    return entry.get('zh_tw', english_name)


def get_translation(english_name: str, lang: str = 'zh_cn') -> str:
    """获取翻译 (支持 zh_cn / zh_tw)"""
    translations = _load_translations()
    entry = translations.get(english_name, {})
    return entry.get(lang, entry.get('zh_cn', english_name))


def find_by_zh_cn(chinese_name: str) -> str:
    """通过简体中文查找英文名"""
    translations = _load_translations()
    for en, entry in translations.items():
        if entry.get('zh_cn') == chinese_name:
            return en
    return chinese_name


def find_by_zh_tw(chinese_name: str) -> str:
    """通过繁体中文查找英文名"""
    translations = _load_translations()
    for en, entry in translations.items():
        if entry.get('zh_tw') == chinese_name:
            return en
    return chinese_name


def fuzzy_search(keyword: str) -> list:
    """模糊搜索翻译"""
    translations = _load_translations()
    results = []
    keyword_lower = keyword.lower()
    
    for en, entry in translations.items():
        zh_cn = entry.get('zh_cn', '')
        zh_tw = entry.get('zh_tw', '')
        
        if (keyword_lower in en.lower() or 
            keyword in zh_cn or 
            keyword in zh_tw):
            results.append({
                'en': en,
                'zh_cn': zh_cn,
                'zh_tw': zh_tw,
                'type': entry.get('type', '')
            })
    
    return results


def get_all_currencies() -> dict:
    """获取所有通货翻译"""
    translations = _load_translations()
    return {k: v for k, v in translations.items() if v.get('type') == 'currency'}


def get_all_items() -> dict:
    """获取所有物品翻译"""
    translations = _load_translations()
    return {k: v for k, v in translations.items() if v.get('type') == 'item'}


def get_stats() -> dict:
    """获取翻译统计"""
    translations = _load_translations()
    types = {}
    for k, v in translations.items():
        t = v.get('type', 'unknown')
        types[t] = types.get(t, 0) + 1
    return types


# 测试
if __name__ == '__main__':
    print(f"翻译统计: {get_stats()}")
    print()
    print("通货翻译示例:")
    currencies = get_all_currencies()
    for en, entry in list(currencies.items())[:5]:
        print(f"  {en}: {entry['zh_cn']} / {entry['zh_tw']}")
    print()
    print("模糊搜索 '混沌':")
    results = fuzzy_search('混沌')
    for r in results[:5]:
        print(f"  {r['en']}: {r['zh_cn']}")