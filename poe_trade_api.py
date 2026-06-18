"""
PoE2 官方市集 API 客户端
基于 pathofexile.com/api/trade2 接口
支持简体/繁体/英文三语搜索
"""
import io
import json
import os
import re
import time
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple

from PIL import Image, ImageDraw, ImageFont

CATEGORY_CN_MAP = {
    'currency': '通货',
    'fragments': '碎片/门票',
    'runes': '符文/镶嵌',
    'essences': '精华',
    'ultimatum': '终局/魂核',
    'expedition': '探险/通量',
    'ritual': '仪式/祭坛',
    'vaultkeys': '圣物钥匙',
    'breach': '裂隙/催化剂',
    'abyss': '深渊',
    'uncutgems': '未切割宝石',
    'lineagesupportgems': '血统辅助宝石/辅助宝石',
    'delirium': '谵妄/涂油',
    'incursion': '入侵/神庙',
    'idol': '神像',
    'verisium': '维里西姆/合金',
    'vaal': '瓦尔',
    'accessory': '饰品',
    'armour': '护甲',
    'flask': '药剂',
    'jewel': '珠宝',
    'map': '地图',
    'sanctum': '圣域研究',
    'talismans': '护身符',
    'waystones': '传送石',
    'weapon': '武器',
}

ITEM_ONLY_CATEGORIES = {
    'accessory', 'armour', 'flask', 'jewel',
    'map', 'sanctum', 'talismans', 'waystones', 'weapon',
}

# 导入翻译模块
import translations as trans


_mapping_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unique_items_trilingual.json')
_mods_cn_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mods_cn.json')
_pob2_uniques_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pob2_uniques.json')
_unique_weapons_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unique_weapons_cn.json')
_unique_body_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unique_body_cn.json')

WIKI_API_URL = "https://www.poe2wiki.net/api.php"

CURRENCY_MAP = {
    # 基础通货
    'wisdom': '智慧卷轴',
    'transmute': '蜕变石', 'transmutation': '蜕变石',
    'greater-orb-of-transmutation': '高级蜕变石',
    'perfect-orb-of-transmutation': '完美蜕变石',
    'aug': '增幅石', 'augmentation': '增幅石',
    'greater-orb-of-augmentation': '高级增幅石',
    'perfect-orb-of-augmentation': '完美增幅石',
    'chance': '机会石',
    'alch': '点金石', 'alchemy': '点金石',
    'chaos': '混沌石',
    'greater-chaos-orb': '高级混沌石',
    'perfect-chaos-orb': '完美混沌石',
    'vaal': '瓦尔宝珠',
    'regal': '富豪石',
    'greater-regal-orb': '高级富豪石',
    'perfect-regal-orb': '完美富豪石',
    'exalted': '崇高石',
    'greater-exalted-orb': '高级崇高石',
    'perfect-exalted-orb': '完美崇高石',
    'divine': '神圣石',
    'annul': '剥离石',
    'artificers': '巧匠石', 'artificer': '巧匠石',
    'fracturing-orb': '破溃宝珠', 'fracturing': '破溃宝珠',
    'mirror': '卡兰德的魔镜',
    'hinekoras-lock': '希奈柯拉之锁',
    'cryptic-key': '神秘钥匙',
    # 宝石匠通货
    'lesser-jewellers-orb': '初级宝石匠的棱镜',
    'jewellers': '宝石匠的棱镜', 'jeweller': '宝石匠的棱镜',
    'greater-jewellers-orb': '高级宝石匠的棱镜',
    'perfect-jewellers-orb': '完美宝石匠的棱镜',
    'gemcutters': '宝石匠的棱镜', 'gcp': '宝石匠的棱镜',
    # 磨砺通货
    'scrap': '护甲片', 'armourers': '护甲片',
    'whetstone': '磨刀石',
    'etcher': '奥术师的蚀刻器',
    'bauble': '玻璃弹珠', 'glassblower': '玻璃弹珠',
    # 碎片
    'transmutation-shard': '蜕变石碎片', 'transmutationshard': '蜕变石碎片',
    'chance-shard': '机会石碎片', 'chanceshard': '机会石碎片',
    'regal-shard': '富豪石碎片', 'regalshard': '富豪石碎片',
    'artificers-shard': '巧匠石碎片',
    'exalted-shard': '崇高石碎片', 'exaltedshard': '崇高石碎片',
    'chaos-shard': '混沌石碎片', 'chaosshard': '混沌石碎片',
    'annul-shard': '剥离石碎片', 'annulshard': '剥离石碎片',
}

CURRENCY_CN_FALLBACK = {
    'Divine Orb': '神圣石',
    'Exalted Orb': '崇高石',
    'Chaos Orb': '混沌石',
    'Regal Orb': '富豪石',
    'Orb of Annulment': '剥离石',
    'Vaal Orb': '瓦尔宝珠',
    'Orb of Alchemy': '点金石',
    'Orb of Chance': '机会石',
    'Orb of Transmutation': '蜕变石',
    'Orb of Augmentation': '增幅石',
    "Artificer's Orb": '巧匠石',
    'Fracturing Orb': '破溃宝珠',
    'Mirror of Kalandra': '卡兰德的魔镜',
    "Gemcutter's Prism": '宝石匠的棱镜',
    "Blacksmith's Whetstone": '磨刀石',
    "Armourer's Scrap": '护甲片',
    "Glassblower's Bauble": '玻璃弹珠',
    "Arcanist's Etcher": '奥术师的蚀刻器',
    "Hinekora's Lock": '辛格拉的发辫',
    'Cryptic Key': '神秘钥匙',
    'Architect Orb': '建筑师宝珠',
    'Greater Orb of Transmutation': '高级蜕变石',
    'Perfect Orb of Transmutation': '完美蜕变石',
    'Greater Orb of Augmentation': '高级增幅石',
    'Perfect Orb of Augmentation': '完美增幅石',
    'Greater Chaos Orb': '高级混沌石',
    'Perfect Chaos Orb': '完美混沌石',
    'Greater Regal Orb': '高级富豪石',
    'Perfect Regal Orb': '完美富豪石',
    'Greater Exalted Orb': '高级崇高石',
    'Perfect Exalted Orb': '完美崇高石',
    'Lesser Jeweller\'s Orb': '初级宝石匠的棱镜',
    'Jeweller\'s Orb': '宝石匠的棱镜',
    'Greater Jeweller\'s Orb': '高级宝石匠的棱镜',
    'Perfect Jeweller\'s Orb': '完美宝石匠的棱镜',
    'Breachstone': '裂隙石',
    'Breach Splinter': '裂隙碎片',
    'Adaptive Catalyst': '应变催化剂',
    'Carapace Catalyst': '甲壳催化剂',
    "Chayula's Catalyst": '夏乌拉催化剂',
    "Esh's Catalyst": '艾许催化剂',
    'Flesh Catalyst': '身躯催化剂',
    'Neural Catalyst': '神经催化剂',
    'Necrotic Catalyst': '死灵催化剂',
    'Reaver Catalyst': '袭击催化剂',
    'Sibilant Catalyst': '嘶语催化剂',
    'Skittering Catalyst': '飞掠催化剂',
    "Tul's Catalyst": '托沃催化剂',
    "Uul-Netol's Catalyst": '乌尔尼多催化剂',
    "Xoph's Catalyst": '索伏催化剂',
    'Refined Adaptive Catalyst': '精制适性催化剂',
    'Refined Carapace Catalyst': '精制甲壳催化剂',
    "Refined Chayula's Catalyst": '精制夏乌拉的催化剂',
    "Refined Esh's Catalyst": '精制艾许的催化剂',
    'Refined Flesh Catalyst': '精制血肉催化剂',
    'Refined Neural Catalyst': '精制神经催化剂',
    'Refined Necrotic Catalyst': '精炼死灵催化剂',
    'Refined Reaver Catalyst': '精制掠夺催化剂',
    'Refined Sibilant Catalyst': '精制嘶鸣催化剂',
    'Refined Skittering Catalyst': '精制飞掠催化剂',
    "Refined Tul's Catalyst": '精制托沃的催化剂',
    "Refined Uul-Netol's Catalyst": '精制乌尔尼多的催化剂',
    "Refined Xoph's Catalyst": '精制索伏的催化剂',
    'Diluted Liquid Ire': '稀释的液化愤怒',
    'Diluted Liquid Guilt': '稀释的液化内疚',
    'Diluted Liquid Greed': '稀释的液化贪婪',
    'Liquid Paranoia': '液化偏执',
    'Liquid Envy': '液化嫉妒',
    'Liquid Disgust': '液化憎恶',
    'Liquid Despair': '液化绝望',
    'Concentrated Liquid Fear': '浓缩的液化恐惧',
    'Concentrated Liquid Suffering': '浓缩的液化痛苦',
    'Concentrated Liquid Isolation': '浓缩的液化孤独',
    'Potent Liquid Melancholy': '液化忧郁',
    'Potent Liquid Ferocity': '液化凶猛',
    'Potent Liquid Contempt': '液化轻蔑',
    'Runic Alloy': '符文合金',
    'Adaptive Alloy': '适应合金',
    'Protective Alloy': '防护合金',
    'Expansive Alloy': '扩展合金',
    'Swift Alloy': '迅捷合金',
    'Cyclonic Alloy': '旋风合金',
    'Prismatic Alloy': '棱光合金',
    'Mystic Alloy': '神秘合金',
    'Sovereign Alloy': '至尊合金',
    'Celestial Alloy': '天界合金',
    'Transcendent Alloy': '超越合金',
    "The Runebinder's Alloy": '符文铸造者合金',
    "The Runefather's Alloy": '符文之父合金',
    'Blazing Flux': '炽热通量',
    'Chilling Flux': '冰寒通量',
    'Crackling Flux': '爆裂通量',
    'Void Flux': '虚空通量',
    'Perfect Flux': '完美通量',
    'Verisium': '维里西姆',
    'Exceptional Verisium': '卓越维里西姆',
    'Thaumaturgic Flux': '魔导通量',
}


def _translate_item_name(en_name: str, mapping: Dict = None) -> str:
    cn = trans.get_zh_cn(en_name)
    if cn != en_name:
        return cn
    if mapping:
        en_to_cn = mapping.get('en_to_cn', {})
        cn_name = en_to_cn.get(en_name)
        if cn_name:
            return cn_name
    return en_name


def _translate_currency(en_name: str) -> str:
    cn = trans.get_zh_cn(en_name)
    if cn != en_name:
        return cn
    fallback = CURRENCY_CN_FALLBACK.get(en_name)
    if fallback:
        return fallback
    return en_name


NINJA_TYPE_MAP = {
    'currency': 'Currency',
    'breach': 'Breach',
    'abyss': 'Abyss',
    'delirium': 'Delirium',
    'ritual': 'Ritual',
    'expedition': 'Expedition',
    'verisium': 'Verisium',
}

NINJA_CATEGORY_MAP = {
    'Currency': 'currency',
    'Breach': 'breach',
    'Abyss': 'abyss',
    'Delirium': 'delirium',
    'Ritual': 'ritual',
    'Expedition': 'expedition',
    'Verisium': 'verisium',
}

NINJA_API_BASE = 'https://poe.ninja/poe2/api/economy/exchange/current/overview'

NINJA_LEAGUE_MAP = {
    'runesofaldur': 'Runes of Aldur',
    'standard': 'Standard',
    'hardcore': 'Hardcore',
    'mirage': 'Runes of Aldur',
}


class RateLimitInfo:
    """频率限制信息"""
    def __init__(self):
        self.policy: str = ""
        self.ip_rules: List[Dict] = []
        self.ip_hits: int = 0
        self.retry_after: int = 0

    def is_limited(self) -> bool:
        return self.retry_after > 0

    def update_from_headers(self, headers):
        self.policy = headers.get('X-Rate-Limit-Policy', '')
        self.ip_hits = int(headers.get('X-Rate-Limit-Ip-Hits', 0))
        self.retry_after = int(headers.get('Retry-After', 0))

        rules_str = headers.get('X-Rate-Limit-Ip', '')
        self.ip_rules = []
        if rules_str:
            for rule in rules_str.split(','):
                parts = rule.strip().split(':')
                if len(parts) == 2:
                    self.ip_rules.append({
                        'hits': int(parts[0]),
                        'period': int(parts[1]),
                    })


class TradeAPI:
    """PoE2 官方市集 API 客户端"""

    BASE_URL = "https://www.pathofexile.com/api/trade2"
    GAME = "poe2"

    APP_NAME = "PoE2NinjaBot"
    APP_VERSION = "4.1.0"
    CONTACT = "poe2ninja@example.com"

    CATEGORY_CN = {
        'amulet': '项链', 'belt': '腰带', 'body': '胸甲', 'boots': '鞋子',
        'bow': '弓', 'claw': '爪', 'crossbow': '弩', 'dagger': '匕首',
        'flail': '连枷', 'flask': '药剂', 'focus': '法器', 'gloves': '手套',
        'helmet': '头盔', 'jewel': '珠宝', 'mace': '锤', 'quiver': '箭袋',
        'ring': '戒指', 'sceptre': '权杖', 'shield': '盾牌', 'spear': '矛',
        'staff': '长杖', 'sword': '剑', 'wand': '法杖',
    }

    def __init__(self, poesessid: str = ""):
        self.poesessid = poesessid
        self._mapping: Optional[Dict] = None
        self._mods_cn: Optional[Dict] = None
        self._pob2_uniques: Optional[Dict] = None
        self._name_translations: Dict = {}
        self._last_request_time = 0
        self._request_delay = 1.5
        self.rate_limit = RateLimitInfo()

        self._stats_cache: Optional[Dict] = None
        self._items_cache: Optional[Dict] = None
        self._static_cache: Optional[Dict] = None
        self._leagues_cache: Optional[List[Dict]] = None
        self._filters_cache: Optional[Dict] = None

        self._last_search_items: List[Dict] = []
        self._local_unique_items: List[Dict] = []
        
        # Load name translations
        names_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unique_names_cn.json')
        if os.path.exists(names_file):
            try:
                with open(names_file, 'r', encoding='utf-8') as f:
                    self._name_translations = json.load(f)
            except:
                pass

    def _load_mapping(self) -> Dict:
        if self._mapping:
            return self._mapping
        try:
            if os.path.exists(_mapping_file):
                with open(_mapping_file, 'r', encoding='utf-8') as f:
                    self._mapping = json.load(f)
                    return self._mapping
        except Exception as e:
            print(f"[TradeAPI] Load mapping error: {e}")
        return {}

    def _get_exalted_per_divine(self, league: str) -> float:
        try:
            ninja_league = NINJA_LEAGUE_MAP.get(league.lower(), league)
            url = f"{NINJA_API_BASE}?league={urllib.parse.quote(ninja_league)}&type=Currency&language=en"
            headers = {'User-Agent': 'PoE2NinjaPlugin/1.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            core = data.get('core', {})
            rates = core.get('rates', {})
            return float(rates.get('exalted', 0))
        except Exception as e:
            print(f"[TradeAPI] _get_exalted_per_divine error: {e}")
            return 0

    def _load_mods_cn(self) -> Dict:
        if self._mods_cn:
            return self._mods_cn
        try:
            if os.path.exists(_mods_cn_file):
                with open(_mods_cn_file, 'r', encoding='utf-8') as f:
                    self._mods_cn = json.load(f)
                    return self._mods_cn
        except Exception as e:
            print(f"[TradeAPI] Load mods_cn error: {e}")
        return {}

    def _load_pob2_uniques(self) -> List[Dict]:
        if self._pob2_uniques:
            return self._pob2_uniques.get('items', [])
        try:
            if os.path.exists(_pob2_uniques_file):
                with open(_pob2_uniques_file, 'r', encoding='utf-8') as f:
                    self._pob2_uniques = json.load(f)
                    return self._pob2_uniques.get('items', [])
        except Exception as e:
            print(f"[TradeAPI] Load pob2_uniques error: {e}")
        return []

    def _load_local_uniques(self) -> List[Dict]:
        """Load all local unique item data"""
        if self._local_unique_items:
            return self._local_unique_items
        
        items = []
        
        # Load weapons
        try:
            if os.path.exists(_unique_weapons_file):
                with open(_unique_weapons_file, 'r', encoding='utf-8') as f:
                    weapons = json.load(f)
                    items.extend(weapons)
        except Exception as e:
            print(f"[TradeAPI] Load weapons error: {e}")
        
        # Load body armours
        try:
            if os.path.exists(_unique_body_file):
                with open(_unique_body_file, 'r', encoding='utf-8') as f:
                    body = json.load(f)
                    items.extend(body)
        except Exception as e:
            print(f"[TradeAPI] Load body error: {e}")
        
        self._local_unique_items = items
        return items

    def search_local_by_mod(self, keyword: str) -> List[Dict]:
        """Search local unique items by mod keyword(s)"""
        items = self._load_local_uniques()
        results = []
        
        # Split keyword by spaces for multi-keyword search
        keywords = keyword.strip().split()
        
        # Keyword mapping for fuzzy search (only for short, common keywords)
        keyword_map = {
            "力量": ["力量", "strength"],
            "敏捷": ["敏捷", "dexterity"],
            "智慧": ["智慧", "intelligence"],
            "生命": ["生命", "life"],
            "魔力": ["魔力", "mana"],
            "护甲": ["护甲", "armour"],
            "闪避": ["闪避", "evasion"],
            "能量护盾": ["能量护盾", "energy shield"],
            "攻击速度": ["攻击速度", "attack speed"],
            "施法速度": ["施法速度", "cast speed"],
            "移动速度": ["移动速度", "movement speed"],
            "荆棘": ["荆棘", "thorns"],
            "流血": ["流血", "bleed"],
            "中毒": ["中毒", "poison"],
            "点燃": ["点燃", "ignite"],
            "冰冻": ["冰冻", "freeze"],
            "感电": ["感电", "shock"],
            "格挡": ["格挡", "block"],
            "晕眩": ["晕眩", "stun"],
            "偷取": ["偷取", "leech"],
            "暴击": ["暴击", "critical"],
            "攻速": ["攻击速度", "attack speed"],
            "施速": ["施法速度", "cast speed"],
        }
        
        # Build search keywords for each keyword
        all_search_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            search_kws = [kw_lower]
            
            # Only add fuzzy matches if the keyword is a short, common term
            if kw_lower in keyword_map:
                search_kws.extend(keyword_map[kw_lower])
            
            all_search_keywords.append(search_kws)
        
        # Search for items that match ALL keywords
        for item in items:
            mods = item.get('mods', [])
            mods_text = ' '.join(mods).lower()
            
            # Check if ALL keyword groups match
            all_matched = True
            for search_kws in all_search_keywords:
                group_matched = False
                for kw in search_kws:
                    if kw in mods_text:
                        group_matched = True
                        break
                if not group_matched:
                    all_matched = False
                    break
            
            if all_matched:
                results.append(item)
        
        return results

    def search_local_by_name(self, name: str) -> List[Dict]:
        """Search local unique items by name"""
        items = self._load_local_uniques()
        results = []
        name_lower = name.lower()
        
        for item in items:
            item_name = item.get('name_cn', '').lower()
            item_id = item.get('id', '').lower()
            
            if name_lower in item_name or name_lower in item_id:
                results.append(item)
        
        return results

    def format_local_search(self, results: List[Dict], keyword: str, page: int = 1) -> str:
        """Format local search results with pagination"""
        if not results:
            return f"❌ 未找到包含 '{keyword}' 的传说装备"
        
        per_page = 20
        total = len(results)
        total_pages = (total + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        start = (page - 1) * per_page
        end = start + per_page
        page_items = results[start:end]
        
        lines = [f"🔍 包含 '{keyword}' 的传说装备 ({total} 个) [{page}/{total_pages}]:"]
        
        for i, item in enumerate(page_items, start + 1):
            name_cn = item.get('name_cn', item.get('id', ''))
            base_cn = item.get('base_cn', '')
            category = item.get('category', '')
            
            # Find matching mod
            matched_mod = ""
            for mod in item.get('mods', []):
                if keyword.lower() in mod.lower():
                    matched_mod = mod
                    break
            
            if matched_mod:
                lines.append(f"  {i}. 【{category}】{name_cn} - {base_cn}: {matched_mod}")
            else:
                lines.append(f"  {i}. 【{category}】{name_cn} - {base_cn}")
        
        if page < total_pages:
            lines.append(f"\n💡 输入 'poe2 属性 {keyword} {page + 1}' 查看下一页")
        
        return "\n".join(lines)

    def format_local_item_detail(self, item: Dict) -> str:
        """Format local item details"""
        if not item:
            return "❌ 未找到物品"
        
        name_cn = item.get('name_cn', item.get('id', ''))
        base_cn = item.get('base_cn', '')
        category = item.get('category', '')
        level = item.get('level', 0)
        
        lines = [f"📦 {name_cn}"]
        lines.append(f"📋 {base_cn}")
        lines.append("")
        
        if level:
            lines.append(f"📌 需求:")
            lines.append(f"  Level: {level}")
            lines.append("")
        
        mods = item.get('mods', [])
        if mods:
            lines.append("🔶 词缀:")
            for mod in mods:
                lines.append(f"  • {mod}")
        
        return "\n".join(lines)

    def search_uniques_by_mod(self, keyword: str) -> List[Dict]:
        """Search unique items by mod keyword"""
        items = self._load_pob2_uniques()
        results = []
        keyword_lower = keyword.lower()
        
        for item in items:
            for mod in item.get('mods', []):
                if keyword_lower in mod.lower():
                    results.append(item)
                    break
        
        return results

    def format_unique_search(self, results: List[Dict], keyword: str) -> str:
        """Format unique item search results"""
        if not results:
            return f"❌ 未找到包含 '{keyword}' 的传说装备"
        
        lines = [f"🔍 包含 '{keyword}' 的传说装备 ({len(results)} 个):"]
        
        for item in results[:15]:
            cat_cn = self.CATEGORY_CN.get(item['category'], item['category'])
            name = item['name']
            name_cn = item.get('name_cn', name)
            base = item['base']
            
            matched_mod = ""
            for mod in item.get('mods', []):
                if keyword.lower() in mod.lower():
                    clean_mod = re.sub(r'\{[^}]+\}', '', mod).strip()
                    matched_mod = clean_mod
                    break
            
            if name_cn and name_cn != name:
                display_name = f"{name_cn} ({name})"
            else:
                display_name = name
            
            if matched_mod:
                lines.append(f"  【{cat_cn}】{display_name}: {matched_mod}")
            else:
                lines.append(f"  【{cat_cn}】{display_name}")
        
        if len(results) > 15:
            lines.append(f"  ... 还有 {len(results) - 15} 个")
        
        return "\n".join(lines)

    def search_wiki_by_mod(self, keyword: str) -> List[Dict]:
        """Search items by mod keyword from wiki API (supports fuzzy matching)"""
        url = f"{WIKI_API_URL}?action=cargoquery&tables=items&fields=_pageName=name,base_item,class,explicit_stat_text,implicit_stat_text,required_level&where=rarity=%27Unique%27&limit=500&format=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = [i["title"] for i in data.get("cargoquery", [])]
        except Exception as e:
            print(f"[TradeAPI] Wiki API error: {e}")
            return []
        
        keyword_lower = keyword.lower()
        fuzzy_keywords = [keyword_lower]
        
        keyword_map = {
            # 属性
            "力量": ["strength", "str"],
            "敏捷": ["dexterity", "dex"],
            "智慧": ["intelligence", "int"],
            "生命": ["life", "maximum life"],
            "魔力": ["mana", "maximum mana"],
            "能量护盾": ["energy shield"],
            "护甲": ["armour", "armor"],
            "闪避": ["evasion"],
            "命中值": ["accuracy rating"],
            "精魂": ["spirit"],
            "偏转": ["deflection"],
            
            # 抗性
            "火焰抗性": ["fire resistance", "fire res"],
            "冰霜抗性": ["cold resistance", "cold res"],
            "闪电抗性": ["lightning resistance", "lightning res"],
            "混沌抗性": ["chaos resistance", "chaos res"],
            "抗性": ["resistance", "resist"],
            
            # 伤害
            "物理伤害": ["physical damage"],
            "火焰伤害": ["fire damage"],
            "冰霜伤害": ["cold damage"],
            "闪电伤害": ["lightning damage"],
            "混沌伤害": ["chaos damage"],
            "元素伤害": ["elemental damage"],
            "持续伤害": ["damage over time"],
            "荆棘伤害": ["thorns damage"],
            "荆棘": ["thorns"],
            "伤害": ["damage"],
            
            # 速度
            "攻击速度": ["attack speed"],
            "施法速度": ["cast speed"],
            "移动速度": ["movement speed"],
            "投射物速度": ["projectile speed"],
            "装填速度": ["reload speed"],
            "速度": ["speed"],
            
            # 暴击
            "暴击几率": ["critical strike chance", "critical hit chance"],
            "暴击伤害": ["critical damage bonus", "critical strike multiplier"],
            "暴击": ["critical strike", "critical hit", "crit"],
            
            # 防御
            "格挡": ["block"],
            "晕眩": ["stun"],
            "偷取": ["leech", "leeching"],
            "再生": ["regeneration", "regenerate"],
            "回复": ["recovery", "recover"],
            
            # 异常状态
            "点燃": ["ignite"],
            "冰冻": ["freeze"],
            "冰缓": ["chill"],
            "感电": ["shock"],
            "流血": ["bleed"],
            "中毒": ["poison"],
            "致盲": ["blind"],
            "威吓": ["intimidate"],
            "瘫痪": ["paralysis"],
            
            # 范围
            "范围效果": ["area of effect"],
            "范围": ["area"],
            "在场范围": ["presence area"],
            "在场": ["presence"],
            
            # 技能相关
            "召唤物": ["minion", "minions"],
            "图腾": ["totem"],
            "陷阱": ["trap"],
            "地雷": ["mine"],
            "光环": ["aura"],
            "诅咒": ["curse"],
            "药剂": ["flask"],
            "护符": ["charm"],
            "技能": ["skill"],
            "法术": ["spell"],
            "攻击": ["attack"],
            "近战": ["melee"],
            "投射物": ["projectile"],
            
            # 其他
            "穿透": ["penetration"],
            "曝露": ["exposure"],
            "凋零": ["wither"],
            "猛攻": ["onslaught"],
            "恍惚": ["stun"],
            "稀有度": ["rarity"],
            "照亮范围": ["light radius"],
            "魔力消耗": ["mana cost"],
            "生命消耗": ["life cost"],
            "保留": ["reservation"],
            "神圣": ["sacred", "divine"],
            "碎片": ["fragment", "shard"],
            "能量球": ["power charge"],
            "狂怒球": ["frenzy charge"],
            "耐力球": ["endurance charge"],
            "偷取": ["leech"],
            "生命偷取": ["life leech"],
            "魔力偷取": ["mana leech"],
            "生命回复": ["life regeneration", "life recovery"],
            "魔力回复": ["mana regeneration", "mana recovery"],
            "能量护盾回复": ["energy shield recovery", "energy shield recharge"],
        }
        
        for cn, en_list in keyword_map.items():
            if cn in keyword_lower:
                fuzzy_keywords.extend(en_list)
            for en in en_list:
                if en in keyword_lower:
                    fuzzy_keywords.append(cn)
                    break
        
        fuzzy_keywords = list(set(fuzzy_keywords))
        
        results = []
        for item in items:
            explicit = item.get("explicit stat text", "") or ""
            implicit = item.get("implicit stat text", "") or ""
            all_mods = (explicit + " " + implicit).lower()
            
            matched = False
            for kw in fuzzy_keywords:
                if kw in all_mods:
                    matched = True
                    break
            
            if matched:
                results.append(item)
        
        return results

    def format_wiki_search(self, results: List[Dict], keyword: str, page: int = 1) -> str:
        """Format wiki search results with pagination"""
        if not results:
            return f"❌ 未找到包含 '{keyword}' 的传说装备"
        
        per_page = 10
        total = len(results)
        total_pages = (total + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        start = (page - 1) * per_page
        end = start + per_page
        page_items = results[start:end]
        
        lines = [f"🔍 包含 '{keyword}' 的传说装备 ({total} 个) [{page}/{total_pages}]:"]
        
        for i, item in enumerate(page_items, start + 1):
            name = item.get("name", "")
            name_cn = self._name_translations.get(name, "")
            base = item.get("base item", "")
            item_class = item.get("class", "")
            
            # 底材翻译
            from unique_translations import BASE_TYPE_CN
            base_cn = BASE_TYPE_CN.get(base, base)
            
            if name_cn:
                display_name = f"{name_cn} ({name})"
            else:
                display_name = name
            
            lines.append(f"  {i}. 【{item_class}】{display_name} - {base_cn}")
        
        if page < total_pages:
            lines.append(f"\n💡 输入 'poe2 属性 {keyword} {page + 1}' 查看下一页")
        
        return "\n".join(lines)

    def search_wiki_by_name(self, name: str) -> List[Dict]:
        """Search items by name from wiki API (supports fuzzy matching)"""
        url = f"{WIKI_API_URL}?action=cargoquery&tables=items&fields=_pageName=name,base_item,class,explicit_stat_text,implicit_stat_text,required_level&where=rarity=%27Unique%27&limit=500&format=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = [i["title"] for i in data.get("cargoquery", [])]
        except Exception as e:
            print(f"[TradeAPI] Wiki API error: {e}")
            return []
        
        cn_to_en = {v: k for k, v in self._name_translations.items()}
        
        name_lower = name.lower()
        results = []
        
        for item in items:
            item_name = item.get("name", "")
            item_name_lower = item_name.lower()
            name_cn = self._name_translations.get(item_name, "")
            name_cn_lower = name_cn.lower()
            base = item.get("base item", "").lower()
            
            if (name_lower == item_name_lower or 
                name_lower == name_cn_lower):
                results.insert(0, item)
                continue
            
            if name in cn_to_en:
                en_name = cn_to_en[name].lower()
                if en_name == item_name_lower:
                    results.insert(0, item)
                    continue
            
            if (name_lower in item_name_lower and len(name_lower) > 3):
                results.append(item)
                continue
            
            if name_cn and name in name_cn:
                results.append(item)
        
        return results

    def format_wiki_name_search(self, results: List[Dict], keyword: str) -> str:
        """Format wiki name search results with detailed mod display"""
        if not results:
            return f"❌ 未找到包含 '{keyword}' 的传说装备"
        
        if len(results) > 1:
            lines = [f"🔍 找到 {len(results)} 个装备:"]
            for i, item in enumerate(results[:10], 1):
                name = item.get("name", "")
                name_cn = self._name_translations.get(name, "")
                base = item.get("base item", "")
                
                # 底材翻译
                from unique_translations import BASE_TYPE_CN
                base_cn = BASE_TYPE_CN.get(base, base)
                
                if name_cn:
                    lines.append(f"  {i}. {name_cn} ({name}) - {base_cn}")
                else:
                    lines.append(f"  {i}. {name} - {base_cn}")
            lines.append(f"\n💡 输入 'poe2 装备 <序号>' 查看详情")
            return "\n".join(lines)
        
        return self.format_wiki_item_detail(results[0])

    def format_wiki_item_detail(self, item: Dict) -> str:
        """Format single item details"""
        name = item.get("name", "")
        name_cn = self._name_translations.get(name, "")
        base = item.get("base item", "")
        item_class = item.get("class", "")
        level = item.get("required level", "")
        
        # 使用中文名
        if name_cn:
            display_name = f"{name_cn} ({name})"
        else:
            display_name = name
        
        # 底材翻译
        from unique_translations import BASE_TYPE_CN
        base_cn = BASE_TYPE_CN.get(base, base)
        
        lines = [f"📦 {display_name}"]
        lines.append(f"📋 {base_cn}")
        lines.append("")
        
        if level:
            lines.append(f"📌 需求:")
            lines.append(f"  Level: {level}")
            lines.append("")
        
        implicit = item.get("implicit stat text", "") or ""
        if implicit:
            implicit = implicit.replace("&lt;br&gt;", "<br>").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            implicit_mods = [m.strip() for m in implicit.split("<br>") if m.strip()]
            lines.append("🔷 隐式词缀:")
            for mod in implicit_mods:
                translated = self._translate_wiki_mod(mod)
                lines.append(f"  • {translated}")
            lines.append("")
        
        explicit = item.get("explicit stat text", "") or ""
        if explicit:
            explicit = explicit.replace("&lt;br&gt;", "<br>").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            explicit_mods = [m.strip() for m in explicit.split("<br>") if m.strip()]
            lines.append("🔶 显式词缀:")
            for mod in explicit_mods:
                translated = self._translate_wiki_mod(mod)
                lines.append(f"  • {translated}")
        
        return "\n".join(lines)

    def _translate_wiki_mod(self, text: str) -> str:
        """Translate wiki mod text to Chinese based on poe2db standards"""
        if not text:
            return text
        
        # Remove wiki markup
        text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', text)
        text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
        text = text.replace('<br>', '\n')
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        
        # 完整短语翻译 (来自 poe2db)
        phrase_translations = [
            # 特殊完整短语 (优先处理)
            ("of Melee Physical Damage taken reflected to Attacker", "受到的近战物理伤害会反射给攻击者"),
            ("taken reflected to Attacker", "承受的伤害反射给攻击者"),
            ("reflected to Attacker", "反射给攻击者"),
            ("Cannot Evade Enemy Attacks", "无法闪避敌人攻击"),
            ("you gain its Modifiers for 60 seconds", "你获得它的词缀，持续60秒"),
            ("When you kill a Rare monster", "当你击败稀有怪物时"),
            ("Skills gain a Base Life Cost equal to", "技能获得相当于"),
            ("of Base Mana Cost", "基础魔力消耗的额外生命消耗"),
            ("Deal your Thorns Damage to Enemies you Stun with Melee Attacks", "近战攻击击中时对敌人造成荆棘伤害"),
            ("Enemies in your Presence", "在场的敌人"),
            ("Allies in your Presence", "在场的友军"),
            ("while Surrounded", "被包围时"),
            ("Regenerate", "再生"),
            ("maximum Life", "生命上限"),
            ("maximum Mana", "魔力上限"),
            ("maximum Energy Shield", "能量护盾上限"),
            
            # 武器相关
            ("Adds", "附加"),
            ("to Attacks", "攻击伤害"),
            ("Physical Damage", "物理伤害"),
            ("Fire Damage", "火焰伤害"),
            ("Cold Damage", "冰霜伤害"),
            ("Lightning Damage", "闪电伤害"),
            ("Chaos Damage", "混沌伤害"),
            ("Elemental Damage", "元素伤害"),
            ("Damage over Time", "持续伤害"),
            ("Damage taken", "承受伤害"),
            ("Thorns Damage", "荆棘伤害"),
            ("Base Chaos Damage", "基础混沌伤害"),
            ("to maximum Life", "至生命上限"),
            ("to maximum Mana", "至魔力上限"),
            ("to maximum Energy Shield", "至能量护盾上限"),
            ("to all Elemental Resistances", "至所有元素抗性"),
            ("to Fire Resistance", "至火焰抗性"),
            ("to Cold Resistance", "至冰霜抗性"),
            ("to Lightning Resistance", "至闪电抗性"),
            ("to Chaos Resistance", "至混沌抗性"),
            ("to Strength", "至力量"),
            ("to Dexterity", "至敏捷"),
            ("to Intelligence", "至智慧"),
            ("to all Attributes", "至全属性"),
            ("to Accuracy Rating", "至命中值"),
            ("to Stun Threshold", "至晕眩阈值"),
            
            # 速度相关
            ("Attack Speed", "攻击速度"),
            ("Cast Speed", "施法速度"),
            ("Movement Speed", "移动速度"),
            ("Projectile Speed", "投射物速度"),
            ("Reload Speed", "装填速度"),
            
            # 暴击相关
            ("Critical Strike Chance", "暴击几率"),
            ("Critical Hit Chance", "暴击几率"),
            ("Critical Damage Bonus", "暴击伤害加成"),
            
            # 防御相关
            ("Life Regeneration", "生命回复"),
            ("Mana Regeneration Rate", "魔力再生率"),
            ("Energy Shield Recharge Rate", "能量护盾充能率"),
            ("Stun Threshold", "晕眩阈值"),
            ("Stun Duration", "晕眩持续时间"),
            ("Stun Buildup", "晕眩积蓄"),
            ("Block Chance", "格挡几率"),
            ("Evasion Rating", "闪避值"),
            
            # 词缀类型
            ("increased", "提高"),
            ("reduced", "降低"),
            ("more", "更多"),
            ("less", "更少"),
            
            # 其他
            ("per second", "每秒"),
            ("Rarity of Items found", "物品稀有度"),
            ("Light Radius", "照亮范围"),
            ("Area of Effect", "范围效果"),
            ("Melee Strike Range", "近战打击范围"),
            ("Charm Slot", "护符栏位"),
            ("Charm Slots", "护符栏位"),
            ("Charm Charges", "护符充能"),
            ("Flask Recovery", "药剂回复"),
            ("Flask Charges", "药剂充能"),
            ("Life Cost", "生命消耗"),
            ("Mana Cost", "魔力消耗"),
            ("Endurance Charge", "耐力球"),
            ("Frenzy Charge", "狂怒球"),
            ("Power Charge", "暴击球"),
            ("Life Leech", "生命偷取"),
            ("Mana Leech", "魔力偷取"),
            ("Culling Strike", "终结效果"),
            ("Paralysis", "瘫痪"),
            ("Bleeding on Hit", "击中造成流血"),
            ("Poison on Hit", "击中造成中毒"),
            ("Ignite", "点燃"),
            ("Freeze", "冰冻"),
            ("Shock", "感电"),
            ("Chill", "冰缓"),
            ("Blind", "致盲"),
            ("Intimidate", "威吓"),
            
            # 技能相关
            ("Skills", "技能"),
            ("Skill", "技能"),
            ("Spell", "法术"),
            ("Attack", "攻击"),
            ("Melee", "近战"),
            ("Projectile", "投射物"),
            ("Minion", "召唤物"),
            ("Totem", "图腾"),
            ("Trap", "陷阱"),
            ("Mine", "地雷"),
            ("Brand", "烙印"),
            ("Curse", "诅咒"),
            ("Mark", "印记"),
            ("Aura", "光环"),
            ("Herald", "使者"),
            ("Banner", "旗帜"),
            
            # 属性
            ("Strength", "力量"),
            ("Dexterity", "敏捷"),
            ("Intelligence", "智慧"),
            ("Life", "生命"),
            ("Mana", "魔力"),
            ("Spirit", "精魂"),
            ("Armour", "护甲"),
            ("Evasion", "闪避"),
            ("Energy Shield", "能量护盾"),
            ("Level", "等级"),
            ("Chance", "几率"),
            ("Damage", "伤害"),
            ("Hit", "击中"),
            ("Kill", "击败"),
            ("Enemy", "敌人"),
            ("Enemies", "敌人"),
            ("Allies", "友军"),
            ("Presence", "在场"),
            ("Gain", "获得"),
            ("Leech", "偷取"),
            ("to", "至"),
            ("of", "的"),
            ("and", "和"),
            ("with", "拥有"),
            ("per", "每"),
            ("for", "持续"),
            ("seconds", "秒"),
            ("Causes", "造成"),
            ("Double", "双倍"),
            ("Cannot", "无法"),
            ("Grants", "给予"),
            ("when", "当"),
            ("while", "当"),
            ("if", "如果"),
            ("you", "你"),
            ("your", "你的"),
        ]
        
        result = text
        for en, cn in phrase_translations:
            if len(en.split()) >= 2:
                result = result.replace(en, cn)
            else:
                result = re.sub(r'\b' + re.escape(en) + r'\b', cn, result, flags=re.IGNORECASE)
        
        # 清理多余的空格
        result = re.sub(r'\s+', ' ', result)
        result = result.strip()
        
        return result

    # ============ 市集 API 方法 ============

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            'User-Agent': f'{self.APP_NAME}/{self.APP_VERSION} ({self.CONTACT})',
            'Accept': 'application/json',
        }
        if self.poesessid:
            headers['Cookie'] = f'POESESSID={self.poesessid}'
        return headers

    def _fetch_json(self, url: str, data: bytes = None, method: str = 'GET',
                    silent: bool = False, max_retries: int = 2) -> Optional[Dict]:
        for attempt in range(max_retries + 1):
            try:
                if self.rate_limit.is_limited():
                    wait = self.rate_limit.retry_after
                    if not silent:
                        print(f"[TradeAPI] Rate limited, waiting {wait}s...")
                    time.sleep(wait)

                elapsed = time.time() - self._last_request_time
                if elapsed < self._request_delay:
                    time.sleep(self._request_delay - elapsed)

                headers = self._get_headers()
                if data:
                    headers['Content-Type'] = 'application/json'

                req = urllib.request.Request(url, data=data, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    self._last_request_time = time.time()
                    self.rate_limit.update_from_headers(resp.headers)
                    return json.loads(resp.read().decode('utf-8'))

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    self.rate_limit.retry_after = int(e.headers.get('Retry-After', 10))
                    if attempt < max_retries:
                        continue
                if e.code == 403:
                    if not silent:
                        print(f"[TradeAPI] 403 Forbidden - 检查 User-Agent 和请求频率")
                    return None
                if not silent:
                    print(f"[TradeAPI] HTTP {e.code}: {e.reason}")
                return None
            except Exception as e:
                if not silent:
                    print(f"[TradeAPI] Request error: {e}")
                return None
        return None

    def get_leagues(self) -> List[Dict]:
        if self._leagues_cache:
            return self._leagues_cache
        url = f"{self.BASE_URL}/data/leagues"
        data = self._fetch_json(url)
        if data and 'result' in data:
            self._leagues_cache = data['result']
            return data['result']
        return []

    def translate_name(self, name: str) -> Tuple[str, List[str]]:
        mapping = self._load_mapping()
        if not mapping:
            return name, []

        cn_to_en = mapping.get('cn_to_en', {})
        tw_to_en = mapping.get('tw_to_en', {})
        en_to_cn = mapping.get('en_to_cn', {})

        if name in cn_to_en:
            return cn_to_en[name], [name]
        if name in tw_to_en:
            en_name = tw_to_en[name]
            return en_name, [en_to_cn.get(en_name, name)]
        if name in en_to_cn:
            return name, [en_to_cn[name]]

        name_lower = name.lower()
        matched_cn = []
        for cn in cn_to_en:
            if name_lower in cn.lower():
                matched_cn.append(cn)
        if not matched_cn:
            for tw, en in tw_to_en.items():
                if name_lower in tw.lower():
                    cn_name = en_to_cn.get(en, tw)
                    if cn_name not in matched_cn:
                        matched_cn.append(cn_name)
        if not matched_cn:
            for en, cn in en_to_cn.items():
                if name_lower in en.lower():
                    if cn not in matched_cn:
                        matched_cn.append(cn)

        if len(matched_cn) == 1:
            return cn_to_en.get(matched_cn[0], matched_cn[0]), matched_cn
        if len(matched_cn) > 1:
            return "", matched_cn

        return name, []

    def _build_search_query(self, en_name: str, query_type: str = 'name',
                            online_only: bool = False,
                            max_price: Optional[int] = None,
                            price_currency: str = 'chaos',
                            stat_filters: Optional[List[Dict]] = None) -> Dict:
        query = {
            'query': {
                'stats': [{'type': 'and', 'filters': []}],
                'filters': {
                    'trade_filters': {
                        'filters': {
                            'sale_type': {'option': 'priced'}
                        }
                    }
                }
            },
            'sort': {'price': 'asc'}
        }

        if online_only:
            query['query']['status'] = {'option': 'online'}

        if query_type == 'name':
            query['query']['name'] = en_name
        else:
            query['query']['type'] = en_name

        if max_price is not None:
            query['query']['filters']['trade_filters']['filters']['price'] = {
                'max': max_price,
                'option': price_currency,
            }

        if stat_filters:
            for sf in stat_filters:
                stat_entry = {
                    'id': sf.get('id', ''),
                    'disabled': False,
                    'filters': {},
                }
                if 'min' in sf:
                    stat_entry['filters']['min'] = {'value': sf['min']}
                if 'max' in sf:
                    stat_entry['filters']['max'] = {'value': sf['max']}
                query['query']['stats'][0]['filters'].append(stat_entry)

        return query

    def search_items(self, league: str, en_name: str, query_type: str = 'name',
                     online_only: bool = False,
                     max_price: Optional[int] = None,
                     price_currency: str = 'chaos',
                     stat_filters: Optional[List[Dict]] = None) -> Optional[Dict]:
        search_url = f"{self.BASE_URL}/search/{self.GAME}/{urllib.parse.quote(league)}"
        query = self._build_search_query(en_name, query_type, online_only, max_price, price_currency, stat_filters)
        return self._fetch_json(search_url, json.dumps(query).encode('utf-8'), 'POST')

    def fetch_items(self, item_ids: List[str], query_id: str) -> Optional[Dict]:
        if not item_ids or not query_id:
            return None
        # Fetch up to 20 items (2 batches of 10)
        all_results = []
        for i in range(0, min(len(item_ids), 20), 10):
            batch_ids = item_ids[i:i+10]
            ids = ','.join(batch_ids)
            fetch_url = f"{self.BASE_URL}/fetch/{ids}?query={query_id}"
            result = self._fetch_json(fetch_url)
            if result and 'result' in result:
                all_results.extend(result['result'])
            if i + 10 < len(item_ids):
                time.sleep(0.5)  # Rate limit between batches
        return {'result': all_results}

    def search_with_mods(self, league: str, item_name: str,
                         mod_filters: Optional[List[Dict]] = None,
                         online_only: bool = False,
                         max_price: Optional[int] = None,
                         price_currency: str = 'chaos') -> Optional[Dict]:
        en_name, cn_matches = self.translate_name(item_name)

        if len(cn_matches) > 1:
            return {'total': 0, 'min_price': None, 'matches': cn_matches, 'multiple': True}

        cn_name = cn_matches[0] if cn_matches else item_name

        search_result = self.search_items(league, en_name, 'name', online_only, max_price, price_currency, mod_filters)

        if not search_result or not search_result.get('result'):
            search_result = self.search_items(league, en_name, 'type', online_only, max_price, price_currency, mod_filters)

        if not search_result or 'result' not in search_result:
            return {'total': 0, 'min_price': None, 'en_name': en_name, 'cn_name': cn_name}

        total = search_result.get('total', 0)
        item_ids = search_result.get('result', [])
        query_id = search_result.get('id', '')

        if not item_ids:
            return {'total': 0, 'min_price': None, 'en_name': en_name, 'cn_name': cn_name}

        fetch_result = self.fetch_items(item_ids, query_id)

        if not fetch_result or 'result' not in fetch_result:
            return {'total': total, 'min_price': None, 'en_name': en_name, 'cn_name': cn_name}

        items = fetch_result['result']
        if not items:
            return {'total': total, 'min_price': None, 'en_name': en_name, 'cn_name': cn_name}

        prices = []
        item_details = []
        for item in items:
            listing = item.get('listing', {})
            price = listing.get('price', {})
            account = listing.get('account', {})
            seller = account.get('name', '')

            item_data = item.get('item', {})

            if price and price.get('amount'):
                entry = {
                    'amount': price.get('amount', 0),
                    'currency': price.get('currency', 'unknown'),
                    'seller': seller,
                }
                prices.append(entry)
                item_details.append({
                    'id': item.get('id', ''),
                    'name': item_data.get('name', ''),
                    'type': item_data.get('typeLine', ''),
                    'ilvl': item_data.get('ilvl', 0),
                    'sockets': item_data.get('sockets', []),
                    'price': entry,
                    'seller': seller,
                    'explicitMods': item_data.get('explicitMods', []),
                    'implicitMods': item_data.get('implicitMods', []),
                    'runeMods': item_data.get('runeMods', []),
                    'requirements': item_data.get('requirements', []),
                    'properties': item_data.get('properties', []),
                    'corrupted': item_data.get('corrupted', False),
                    'frameType': item_data.get('frameType', 0),
                })

        self._last_search_items = item_details

        if not prices:
            return {'total': total, 'min_price': None, 'en_name': en_name, 'cn_name': cn_name}

        min_p = min(prices, key=lambda x: x['amount'])

        return {
            'total': total,
            'min_price': min_p,
            'prices': prices,
            'items': item_details,
            'en_name': en_name,
            'cn_name': cn_name,
            'rate_limit': {
                'ip_hits': self.rate_limit.ip_hits,
                'policy': self.rate_limit.policy,
            },
        }

    def get_item_price(self, league: str, item_name: str) -> Optional[Dict]:
        return self.search_with_mods(league, item_name)

    def get_all_item_prices(self, league: str, category: str, top_n: int = 20) -> Optional[Dict]:
        """Fetch item prices from poe2scout Items API."""
        try:
            url = f"https://api.poe2scout.com/poe2/Leagues/{urllib.parse.quote(league)}/Items"
            headers = {'User-Agent': 'PoE2NinjaPlugin/1.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            results = []
            for item in data:
                cat = item.get('CategoryApiId', '')
                if cat != category:
                    continue
                price = float(item.get('CurrentPrice', 0))
                if price <= 0:
                    continue
                name = item.get('Text', '')
                cn_name = _translate_item_name(name, self._load_mapping())
                results.append({
                    'name_en': name,
                    'name_cn': cn_name,
                    'rate_exalt': price,
                    'category': cat,
                    'category_cn': CATEGORY_CN_MAP.get(cat, cat),
                    'icon_url': item.get('IconUrl', ''),
                })

            results.sort(key=lambda x: -x['rate_exalt'])
            results = results[:top_n]

            ex_per_div = self._get_exalted_per_divine(league)
            if ex_per_div > 0:
                for r in results:
                    r['rate_exalt'] = r['rate_exalt'] / ex_per_div
                results.sort(key=lambda x: -x['rate_exalt'])

            return {
                'items': results,
                'categories': [category],
                'unit': 'D',
                'rates': {'exalted': ex_per_div} if ex_per_div > 0 else {},
            }
        except Exception as e:
            print(f"[TradeAPI] get_all_item_prices error: {e}")
            return None

    def get_all_currency_rates(self, league: str, category: str = None, top_n: int = 20) -> Optional[Dict]:
        """Fetch all currency rates from poe.ninja with category support."""
        try:
            ninja_type = NINJA_TYPE_MAP.get(category) if category else None
            if category and not ninja_type:
                return self._get_all_currency_rates_scout(league, category, top_n)

            ninja_league = NINJA_LEAGUE_MAP.get(league.lower(), league)
            headers = {'User-Agent': 'PoE2NinjaPlugin/1.0'}
            results = []
            categories_found = set()

            if ninja_type:
                types_to_fetch = [ninja_type]
            else:
                types_to_fetch = list(NINJA_TYPE_MAP.values())

            primary_unit = None
            first_rates = None
            for ninja_t in types_to_fetch:
                url = f"{NINJA_API_BASE}?league={urllib.parse.quote(ninja_league)}&type={ninja_t}&language=en"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode('utf-8'))

                core = data.get('core', {})
                if primary_unit is None:
                    primary_unit = core.get('primary', 'divine')
                    first_rates = core.get('rates', {})
                cat_id = NINJA_CATEGORY_MAP.get(ninja_t, ninja_t.lower())
                categories_found.add(cat_id)

                lines = data.get('lines', [])
                items_info = data.get('items', [])
                items_map = {}
                for item in items_info:
                    items_map[item.get('id', '')] = item

                for line in lines:
                    item_id = line.get('id', '')
                    pv = float(line.get('primaryValue', 0))
                    if pv <= 0 or not item_id:
                        continue
                    item_detail = items_map.get(item_id, {})
                    en_name = item_detail.get('name', item_id)
                    icon_path = item_detail.get('image', '')
                    icon_url = f"https://poe.ninja{icon_path}" if icon_path else ''
                    cn_name = _translate_currency(en_name)
                    results.append({
                        'name_en': en_name,
                        'name_cn': cn_name,
                        'rate_exalt': pv,
                        'category': cat_id,
                        'category_cn': CATEGORY_CN_MAP.get(cat_id, cat_id),
                        'icon_url': icon_url,
                    })

            unit_letter = {'divine': 'D', 'exalted': 'E', 'chaos': 'C'}.get(primary_unit, 'D')
            skip_names = {'Exalted Orb'}
            results = [r for r in results if r['name_en'] not in skip_names]
            results.sort(key=lambda x: -x['rate_exalt'])
            results = results[:top_n]

            rates_info = {}
            if primary_unit == 'divine' and first_rates:
                rates_info = {
                    'exalted': float(first_rates.get('exalted', 0)),
                    'chaos': float(first_rates.get('chaos', 0)),
                }

            return {
                'items': results,
                'categories': sorted(categories_found),
                'unit': unit_letter,
                'rates': rates_info,
            }
        except Exception as e:
            print(f"[TradeAPI] get_all_currency_rates error: {e}")
            return None

    def _get_all_currency_rates_scout(self, league: str, category: str = None, top_n: int = 20) -> Optional[Dict]:
        """Fallback: Fetch currency rates from poe2scout for categories not in poe.ninja."""
        try:
            url = f"https://api.poe2scout.com/poe2/Leagues/{urllib.parse.quote(league)}/SnapshotPairs"
            headers = {'User-Agent': 'PoE2NinjaPlugin/1.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            best_price = {}
            categories_found = set()
            for pair in data:
                vol = int(pair.get('CurrencyOneData', {}).get('VolumeTraded', 0)) + \
                      int(pair.get('CurrencyTwoData', {}).get('VolumeTraded', 0))
                for side in ('CurrencyOne', 'CurrencyTwo'):
                    c = pair.get(side, {})
                    c_data = pair.get(f'{side}Data', {})
                    name = c.get('Text', '')
                    price = float(c_data.get('RelativePrice', 0))
                    cat = c.get('CategoryApiId', '')
                    icon = c.get('IconUrl', '')
                    api_id = c.get('ApiId', '')
                    if not name or price <= 0:
                        continue
                    if cat:
                        categories_found.add(cat)
                    if name not in best_price or vol > best_price[name]['vol']:
                        best_price[name] = {
                            'price': price,
                            'category': cat,
                            'icon_url': icon,
                            'api_id': api_id,
                            'vol': vol,
                        }

            skip_names = {'Exalted Orb'}
            results = []
            for en_name, info in sorted(best_price.items(), key=lambda x: -x[1]['price']):
                if en_name in skip_names:
                    continue
                if category and info['category'] != category:
                    continue
                cn_name = _translate_currency(en_name)
                results.append({
                    'name_en': en_name,
                    'name_cn': cn_name,
                    'rate_exalt': info['price'],
                    'category': info['category'],
                    'category_cn': CATEGORY_CN_MAP.get(info['category'], info['category']),
                    'icon_url': info['icon_url'],
                })
                if len(results) >= top_n:
                    break

            ex_per_div = self._get_exalted_per_divine(league)
            if ex_per_div > 0:
                for r in results:
                    r['rate_exalt'] = r['rate_exalt'] / ex_per_div
                results.sort(key=lambda x: -x['rate_exalt'])

            return {
                'items': results,
                'categories': sorted(categories_found),
                'unit': 'D',
                'rates': {'exalted': ex_per_div} if ex_per_div > 0 else {},
            }
        except Exception as e:
            print(f"[TradeAPI] _get_all_currency_rates_scout error: {e}")
            return None

    def render_currency_image(self, league: str, data: Dict, category: str = None) -> Optional[bytes]:
        """Render currency rates or item prices as an image and return PNG bytes."""
        try:
            items = data.get('items', [])
            if not items:
                return None

            is_item = category in ITEM_ONLY_CATEGORIES if category else False

            font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
            font_path = None
            for name in ['NotoSansSC-Regular.ttf', 'NotoSansSC[wght].ttf']:
                candidate = os.path.join(font_dir, name)
                if os.path.exists(candidate):
                    font_path = candidate
                    break

            if not font_path:
                for sys_font in [
                    'C:/Windows/Fonts/msyh.ttc',
                    'C:/Windows/Fonts/msyhbd.ttc',
                    'C:/Windows/Fonts/simhei.ttf',
                    'C:/Windows/Fonts/simsun.ttc',
                    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
                    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
                    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                    '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                    '/usr/share/fonts/noto-cjk/NotoSansSC-Regular.otf',
                ]:
                    if os.path.exists(sys_font):
                        font_path = sys_font
                        break

            if font_path:
                font_title = ImageFont.truetype(font_path, 26)
                font_body = ImageFont.truetype(font_path, 18)
                font_small = ImageFont.truetype(font_path, 14)
                font_cat = ImageFont.truetype(font_path, 13)
                for f in [font_title, font_body, font_small, font_cat]:
                    try:
                        f.set_variation_by_name('Regular')
                    except Exception:
                        pass
            else:
                font_title = ImageFont.load_default()
                font_body = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_cat = ImageFont.load_default()

            row_h = 36
            header_h = 65
            footer_h = 36
            padding_x = 20
            padding_y = 12
            bar_max_w = 140
            name_max_w = 220
            img_w = 720
            img_h = header_h + row_h * len(items) + footer_h + padding_y * 2

            img = Image.new('RGB', (img_w, img_h), '#1a1a2e')
            draw = ImageDraw.Draw(img)

            draw.rectangle([0, 0, img_w, header_h], fill='#16213e')
            cat_label = CATEGORY_CN_MAP.get(category, '全部') if category else '全部'
            draw.text((padding_x, padding_y + 6), f"{league} · {cat_label} TOP {len(items)}",
                      fill='#e94560', font=font_title)

            max_rate = max((d['rate_exalt'] for d in items), default=1)
            if max_rate <= 0:
                max_rate = 1

            unit = data.get('unit', 'E')

            name_x = padding_x + 30
            bar_x_start = img_w - padding_x - bar_max_w - 80

            y = header_h + padding_y
            for i, item in enumerate(items):
                if i % 2 == 0:
                    draw.rectangle([0, y, img_w, y + row_h], fill='#1f2940')

                rank_text = f"{i + 1:>2}"
                draw.text((padding_x, y + 7), rank_text, fill='#8b8b8b', font=font_small)

                name_cn = item.get('name_cn', '')
                name_en = item.get('name_en', '')
                if name_cn and name_cn != name_en:
                    name_text = name_cn
                elif name_en:
                    name_text = name_en
                else:
                    name_text = '???'

                while draw.textlength(name_text, font=font_body) > name_max_w and len(name_text) > 1:
                    name_text = name_text[:-1]
                if name_text != (name_cn if name_cn and name_cn != name_en else name_en):
                    name_text = name_text.rstrip('…') + '…'

                draw.text((name_x, y + 6), name_text, fill='#e0e0e0', font=font_body)

                name_end_x = name_x + draw.textlength(name_text, font=font_body) + 6
                cat_cn = item.get('category_cn', '')
                if cat_cn and not category:
                    cat_text_w = draw.textlength(cat_cn, font=font_cat)
                    if name_end_x + cat_text_w < bar_x_start - 10:
                        draw.text((name_end_x, y + 9), cat_cn, fill='#5a5a7a', font=font_cat)

                rate = item['rate_exalt']
                if rate >= 1000:
                    rate_text = f"{rate:,.0f}{unit}"
                elif rate >= 1:
                    rate_text = f"{rate:.1f}{unit}"
                else:
                    rate_text = f"{rate:.2f}{unit}"

                bar_w = int((rate / max_rate) * bar_max_w)
                bar_w = max(bar_w, 4)
                draw.rounded_rectangle(
                    [bar_x_start, y + 9, bar_x_start + bar_w, y + row_h - 9],
                    radius=3, fill='#e94560'
                )

                rate_x = bar_x_start + bar_w + 6
                draw.text((rate_x, y + 6), rate_text, fill='#f0f0f0', font=font_body)

                y += row_h

            draw.rectangle([0, img_h - footer_h, img_w, img_h], fill='#16213e')
            rates_info = data.get('rates', {})
            footer_left = "数据来源: poe.ninja"
            if rates_info:
                ex_rate = rates_info.get('exalted', 0)
                c_rate = rates_info.get('chaos', 0)
                parts = []
                if ex_rate > 0:
                    parts.append(f"1D={ex_rate:.0f}E")
                if c_rate > 0:
                    parts.append(f"1D={c_rate:.1f}C")
                footer_right = "  ".join(parts)
            else:
                footer_right = ""
            draw.text((padding_x, img_h - footer_h + 8),
                      footer_left,
                      fill='#6b6b8b', font=font_small)
            if footer_right:
                fr_w = draw.textlength(footer_right, font=font_small)
                draw.text((img_w - padding_x - fr_w, img_h - footer_h + 8),
                          footer_right,
                          fill='#8b8bab', font=font_small)

            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return buf.getvalue()
        except Exception as e:
            print(f"[TradeAPI] render_currency_image error: {e}")
            return None

    def format_currency_text(self, league: str, data: Dict, category: str = None) -> str:
        """Format currency rates as text with Chinese names (fallback for image rendering)"""
        try:
            items = data.get('items', [])
            if not items:
                return "❌ 无数据"

            unit = data.get('unit', 'E')
            cat_label = CATEGORY_CN_MAP.get(category, '全部') if category else '全部'

            lines = [f"💱 {league} · {cat_label} TOP {len(items)}", ""]

            for i, item in enumerate(items, 1):
                name_cn = item.get('name_cn', '')
                name_en = item.get('name_en', '')
                if name_cn and name_cn != name_en:
                    display_name = f"{name_cn}({name_en})"
                elif name_en:
                    display_name = name_en
                else:
                    display_name = '???'

                rate = item['rate_exalt']
                if rate >= 1000:
                    rate_text = f"{rate:,.0f}{unit}"
                elif rate >= 1:
                    rate_text = f"{rate:.1f}{unit}"
                else:
                    rate_text = f"{rate:.2f}{unit}"

                cat_cn = item.get('category_cn', '')
                cat_suffix = f" [{cat_cn}]" if cat_cn and not category else ""

                lines.append(f"  {i}. {display_name}{cat_suffix}: {rate_text}")

            lines.append("")
            lines.append("📊 数据来源: poe.ninja")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 格式化失败: {str(e)}"

    def get_currency_rates(self, league: str) -> str:
        """Query currency exchange rates overview from poe.ninja"""
        try:
            ninja_league = NINJA_LEAGUE_MAP.get(league.lower(), league)
            url = f"{NINJA_API_BASE}?league={urllib.parse.quote(ninja_league)}&type=Currency&language=en"
            headers = {'User-Agent': 'PoE2NinjaPlugin/1.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            core = data.get('core', {})
            primary = core.get('primary', 'divine')
            unit = {'divine': 'D', 'exalted': 'E', 'chaos': 'C'}.get(primary, 'D')

            lines = [f"💱 通货比例 (赛季: {league})", ""]

            lines.append(f"📌 以{unit}为基准:")
            show_currencies = [
                'Divine Orb',
                'Regal Orb',
                'Orb of Annulment',
                'Vaal Orb',
                'Orb of Alchemy',
                'Fracturing Orb',
            ]
            items_info = {item.get('id', ''): item for item in data.get('items', [])}
            for line_data in data.get('lines', []):
                item_id = line_data.get('id', '')
                if item_id in items_info:
                    en_name = items_info[item_id].get('name', item_id)
                    if en_name in show_currencies:
                        pv = float(line_data.get('primaryValue', 0))
                        cn_name = _translate_currency(en_name)
                        if pv >= 1000:
                            lines.append(f"  1 {cn_name} = {pv:,.0f}{unit}")
                        elif pv >= 1:
                            lines.append(f"  1 {cn_name} = {pv:.1f}{unit}")
                        else:
                            lines.append(f"  1 {cn_name} = {pv:.2f}{unit}")

            lines.append("")
            lines.append("💡 用法: poe2 通货 <通货A> [通货B]")
            lines.append("  poe2 通货 d c → 神圣比混沌")
            lines.append("  poe2 通货 e → 崇高比神圣 (默认)")
            lines.append("")
            lines.append("📊 数据来源: poe.ninja")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ 获取通货比例失败: {str(e)}"

    def get_currency_rate(self, league: str, from_name: str, to_name: str) -> str:
        """Query specific currency exchange rate from poe.ninja"""
        # Main dictionary: English API name -> [Chinese name, ...aliases]
        CURRENCIES = {
            # === 基础通货 ===
            'Divine Orb': ['神圣石', 'd', '神圣', 'divine'],
            'Exalted Orb': ['崇高石', 'e', '崇高', 'exalted'],
            'Chaos Orb': ['混沌石', 'c', '混沌', 'chaos'],
            'Regal Orb': ['富豪石', 'r', '富豪', 'regal'],
            'Orb of Annulment': ['剥离石', 'a', '剥离', 'annul'],
            'Vaal Orb': ['瓦尔宝珠', 'v', '瓦尔', 'vaal'],
            'Orb of Alchemy': ['点金石', '点金', 'alch'],
            'Orb of Chance': ['机会石', '机会', 'chance'],
            'Orb of Transmutation': ['蜕变石', '蜕变', 'transmute'],
            'Orb of Augmentation': ['增幅石', '增幅', 'augment'],
            "Artificer's Orb": ['巧匠石', '巧匠', 'artificer'],
            'Fracturing Orb': ['破溃宝珠', 'f', '破溃', 'fracture'],
            'Mirror of Kalandra': ['卡兰德的魔镜', 'm', '镜子', '魔镜', 'mirror'],
            "Gemcutter's Prism": ['宝石匠的棱镜', 'g', '宝石匠', 'gcp'],
            "Blacksmith's Whetstone": ['磨刀石', 'whetstone'],
            "Armourer's Scrap": ['护甲片', 'scrap'],
            "Glassblower's Bauble": ['玻璃弹珠', 'bauble'],
            "Arcanist's Etcher": ['奥术师的蚀刻器', '奥术', 'etcher'],
            
            # === 催化剂 (12种) ===
            'Adaptive Catalyst': ['适应催化剂', '催化剂', 'catalyst', 'adaptive'],
            'Carapace Catalyst': ['甲壳催化剂', 'carapace'],
            "Chayula's Catalyst": ['夏乌拉催化剂', 'chayula'],
            "Esh's Catalyst": ['艾什催化剂', 'esh'],
            'Flesh Catalyst': ['肉体催化剂', 'flesh'],
            'Neural Catalyst': ['神经催化剂', 'neural'],
            'Reaver Catalyst': ['掠夺者催化剂', 'reaver'],
            'Sibilant Catalyst': ['嘶声催化剂', 'sibilant'],
            'Skittering Catalyst': ['掠行催化剂', 'skittering'],
            "Tul's Catalyst": ['图拉催化剂', 'tul'],
            "Uul-Netol's Catalyst": ['乌尔催化剂', 'uul'],
            "Xoph's Catalyst": ['索普催化剂', 'xoph'],
            
            # === 精制催化剂 (12种) ===
            'Refined Adaptive Catalyst': ['精制适应催化剂', '精制催化剂', 'refined adaptive', 'refined catalyst'],
            'Refined Carapace Catalyst': ['精制甲壳催化剂', 'refined carapace'],
            "Refined Chayula's Catalyst": ['精制夏乌拉催化剂', 'refined chayula'],
            "Refined Esh's Catalyst": ['精制艾什催化剂', 'refined esh'],
            'Refined Flesh Catalyst': ['精制肉体催化剂', 'refined flesh'],
            'Refined Neural Catalyst': ['精制神经催化剂', 'refined neural'],
            'Refined Necrotic Catalyst': ['精制死灵催化剂', 'refined necrotic'],
            'Refined Reaver Catalyst': ['精制掠夺催化剂', '精制掠夺者催化剂', 'refined reaver'],
            'Refined Sibilant Catalyst': ['精制嘶鸣催化剂', 'refined sibilant'],
            'Refined Skittering Catalyst': ['精制飞掠催化剂', 'refined skittering'],
            "Refined Tul's Catalyst": ['精制图拉催化剂', 'refined tul'],
            "Refined Uul-Netol's Catalyst": ['精制乌尔催化剂', 'refined uul'],
            "Refined Xoph's Catalyst": ['精制索普催化剂', 'refined xoph'],
            
            # === 涂油/液化 (13种) ===
            'Diluted Liquid Ire': ['稀释的液化愤怒', '愤怒', '稀释愤怒', '液化愤怒', 'ire'],
            'Diluted Liquid Guilt': ['稀释的液化内疚', '内疚', '稀释内疚', '液化内疚', 'guilt'],
            'Diluted Liquid Greed': ['稀释的液化贪婪', '贪婪', '稀释贪婪', '液化贪婪', 'greed'],
            'Liquid Paranoia': ['液化偏执', '偏执', 'paranoia'],
            'Liquid Envy': ['液化嫉妒', '嫉妒', 'envy'],
            'Liquid Disgust': ['液化憎恶', '憎恶', 'disgust'],
            'Liquid Despair': ['液化绝望', '绝望', 'despair'],
            'Concentrated Liquid Fear': ['浓缩的液化恐惧', '恐惧', '浓缩恐惧', '液化恐惧', 'fear'],
            'Concentrated Liquid Suffering': ['浓缩的液化痛苦', '痛苦', '浓缩痛苦', '液化痛苦', 'suffering'],
            'Concentrated Liquid Isolation': ['浓缩的液化孤独', '孤独', '浓缩孤独', '液化孤独', 'isolation'],
            'Potent Liquid Melancholy': ['液化忧郁', '忧郁', 'melancholy'],
            'Potent Liquid Ferocity': ['液化凶猛', '凶猛', 'ferocity'],
            'Potent Liquid Contempt': ['液化轻蔑', '轻蔑', 'contempt'],
            
            # === 精华 (API格式: Essence of X) ===
            # 磨蚀精华 (Physical) - Lesser=次级, 无前缀=普通, Greater=强效, Perfect=完美
            'Lesser Essence of Abrasion': ['次级磨蚀精华', '磨蚀精华', '物理精华', 'physical essence', 'abrasion'],
            'Essence of Abrasion': ['磨蚀精华', 'physical essence', 'abrasion'],
            'Greater Essence of Abrasion': ['强效磨蚀精华', 'greater abrasion'],
            'Perfect Essence of Abrasion': ['完美磨蚀精华', 'perfect abrasion'],
            # 迅捷精华 (Speed)
            'Lesser Essence of Alacrity': ['次级迅捷精华', '迅捷精华', '速度精华', 'speed essence', 'alacrity'],
            'Essence of Alacrity': ['迅捷精华', 'alacrity'],
            'Greater Essence of Alacrity': ['强效迅捷精华', 'greater alacrity'],
            'Perfect Essence of Alacrity': ['完美迅捷精华', 'perfect alacrity'],
            # 战斗精华 (Attack)
            'Lesser Essence of Battle': ['次级战斗精华', '战斗精华', '攻击精华', 'attack essence', 'battle'],
            'Essence of Battle': ['战斗精华', 'battle'],
            'Greater Essence of Battle': ['强效战斗精华', 'greater battle'],
            'Perfect Essence of Battle': ['完美战斗精华', 'perfect battle'],
            # 命令精华 (Ally)
            'Lesser Essence of Command': ['次级命令精华', '命令精华', 'ally essence', 'command'],
            'Essence of Command': ['命令精华', 'command'],
            'Greater Essence of Command': ['强效命令精华', 'greater command'],
            'Perfect Essence of Command': ['完美命令精华', 'perfect command'],
            # 闪电精华 (Lightning)
            'Lesser Essence of Electricity': ['次级闪电精华', '闪电精华', 'lightning essence', 'electricity'],
            'Essence of Electricity': ['闪电精华', 'electricity'],
            'Greater Essence of Electricity': ['强效闪电精华', 'greater electricity'],
            'Perfect Essence of Electricity': ['完美闪电精华', 'perfect electricity'],
            # 强化精华 (Defences)
            'Lesser Essence of Enhancement': ['次级强化精华', '强化精华', '防御精华', 'defence essence', 'enhancement'],
            'Essence of Enhancement': ['强化精华', 'enhancement'],
            'Greater Essence of Enhancement': ['强效强化精华', 'greater enhancement'],
            'Perfect Essence of Enhancement': ['完美强化精华', 'perfect enhancement'],
            # 烈焰精华 (Fire)
            'Lesser Essence of Flames': ['次级烈焰精华', '烈焰精华', '火焰精华', 'fire essence', 'flames'],
            'Essence of Flames': ['烈焰精华', 'flames'],
            'Greater Essence of Flames': ['强效烈焰精华', 'greater flames'],
            'Perfect Essence of Flames': ['完美烈焰精华', 'perfect flames'],
            # 接地精华 (Lightning Resistance)
            'Lesser Essence of Grounding': ['次级接地精华', '接地精华', 'lightning resistance essence', 'grounding'],
            'Essence of Grounding': ['接地精华', 'grounding'],
            'Greater Essence of Grounding': ['强效接地精华', 'greater grounding'],
            'Perfect Essence of Grounding': ['完美接地精华', 'perfect grounding'],
            # 急速精华 (Haste)
            'Lesser Essence of Haste': ['次级急速精华', '急速精华', 'haste'],
            'Essence of Haste': ['急速精华', 'haste'],
            'Greater Essence of Haste': ['强效急速精华', 'greater haste'],
            'Perfect Essence of Haste': ['完美急速精华', 'perfect haste'],
            # 冰霜精华 (Cold)
            'Lesser Essence of Ice': ['次级冰霜精华', '冰霜精华', 'cold essence', 'ice'],
            'Essence of Ice': ['冰霜精华', 'ice'],
            'Greater Essence of Ice': ['强效冰霜精华', 'greater ice'],
            'Perfect Essence of Ice': ['完美冰霜精华', 'perfect ice'],
            # 绝缘精华 (Fire Resistance)
            'Lesser Essence of Insulation': ['次级绝缘精华', '绝缘精华', 'fire resistance essence', 'insulation'],
            'Essence of Insulation': ['绝缘精华', 'insulation'],
            'Greater Essence of Insulation': ['强效绝缘精华', 'greater insulation'],
            'Perfect Essence of Insulation': ['完美绝缘精华', 'perfect insulation'],
            # 富贵精华 (Rarity)
            'Lesser Essence of Opulence': ['次级富贵精华', '富贵精华', '稀有度精华', 'rarity essence', 'opulence'],
            'Essence of Opulence': ['富贵精华', 'opulence'],
            'Greater Essence of Opulence': ['强效富贵精华', 'greater opulence'],
            'Perfect Essence of Opulence': ['完美富贵精华', 'perfect opulence'],
            # 毁灭精华 (Chaos)
            'Lesser Essence of Ruin': ['次级毁灭精华', '毁灭精华', '混沌精华', 'chaos essence', 'ruin'],
            'Essence of Ruin': ['毁灭精华', 'ruin'],
            'Greater Essence of Ruin': ['强效毁灭精华', 'greater ruin'],
            'Perfect Essence of Ruin': ['完美毁灭精华', 'perfect ruin'],
            # 寻觅精华 (Critical)
            'Lesser Essence of Seeking': ['次级寻觅精华', '寻觅精华', '暴击精华', 'critical essence', 'seeking'],
            'Essence of Seeking': ['寻觅精华', 'seeking'],
            'Greater Essence of Seeking': ['强效寻觅精华', 'greater seeking'],
            'Perfect Essence of Seeking': ['完美寻觅精华', 'perfect seeking'],
            # 魔法精华 (Caster)
            'Lesser Essence of Sorcery': ['次级魔法精华', '魔法精华', '施法精华', 'caster essence', 'sorcery'],
            'Essence of Sorcery': ['魔法精华', 'sorcery'],
            'Greater Essence of Sorcery': ['强效魔法精华', 'greater sorcery'],
            'Perfect Essence of Sorcery': ['完美魔法精华', 'perfect sorcery'],
            # 熔解精华 (Cold Resistance)
            'Lesser Essence of Thawing': ['次级熔解精华', '熔解精华', '冰抗精华', 'cold resistance essence', 'thawing'],
            'Essence of Thawing': ['熔解精华', 'thawing'],
            'Greater Essence of Thawing': ['强效熔解精华', 'greater thawing'],
            'Perfect Essence of Thawing': ['完美熔解精华', 'perfect thawing'],
            # 身躯精华 (Life)
            'Lesser Essence of the Body': ['次级身躯精华', '身躯精华', '生命精华', 'life essence', 'body'],
            'Essence of the Body': ['身躯精华', 'body'],
            'Greater Essence of the Body': ['强效身躯精华', 'greater body'],
            'Perfect Essence of the Body': ['完美身躯精华', 'perfect body'],
            # 永恒精华 (Attribute)
            'Lesser Essence of the Infinite': ['次级永恒精华', '永恒精华', '属性精华', 'attribute essence', 'infinite'],
            'Essence of the Infinite': ['永恒精华', 'infinite'],
            'Greater Essence of the Infinite': ['强效永恒精华', 'greater infinite'],
            'Perfect Essence of the Infinite': ['完美永恒精华', 'perfect infinite'],
            # 心灵精华 (Mana)
            'Lesser Essence of the Mind': ['次级心灵精华', '心灵精华', '魔力精华', 'mana essence', 'mind'],
            'Essence of the Mind': ['心灵精华', 'mind'],
            'Greater Essence of the Mind': ['强效心灵精华', 'greater mind'],
            'Perfect Essence of the Mind': ['完美心灵精华', 'perfect mind'],
            # 特殊精华
            'Essence of Hysteria': ['浮夸精华', 'hysteria'],
            'Essence of Delirium': ['谵妄精华', 'delirium'],
            'Essence of Horror': ['极恐精华', 'horror'],
            'Essence of Insanity': ['错乱精华', 'insanity'],
            'Essence of the Abyss': ['深渊精华', 'abyss'],
            'Essence of the Breach': ['裂隙精华', 'breach'],
            
            # === 合金 (Alloy) ===
            'Runic Alloy': ['符文合金', 'runic alloy'],
            'Adaptive Alloy': ['适应合金', 'adaptive alloy'],
            'Protective Alloy': ['防护合金', 'protective alloy'],
            'Expansive Alloy': ['扩展合金', 'expansive alloy'],
            'Swift Alloy': ['迅捷合金', 'swift alloy'],
            'Cyclonic Alloy': ['旋风合金', 'cyclonic alloy'],
            'Prismatic Alloy': ['棱光合金', 'prismatic alloy'],
            'Mystic Alloy': ['神秘合金', 'mystic alloy'],
            'Sovereign Alloy': ['至尊合金', 'sovereign alloy'],
            'Celestial Alloy': ['天界合金', 'celestial alloy'],
            'Transcendent Alloy': ['超越合金', 'transcendent alloy'],
            "The Runebinder's Alloy": ['符文铸造者合金', 'runebinder alloy'],
            "The Runefather's Alloy": ['符文之父合金', 'runefather alloy'],
            
            # === 通量 (Flux) ===
            'Blazing Flux': ['炽热通量', '火抗转换', 'blazing flux'],
            'Chilling Flux': ['冰寒通量', '冰抗转换', 'chilling flux'],
            'Crackling Flux': ['爆裂通量', '雷抗转换', 'crackling flux'],
            'Void Flux': ['虚空通量', '混沌抗转换', 'void flux'],
            'Perfect Flux': ['完美通量', 'perfect flux'],
            
            # === 其他常用通货 ===
            'Mirror of Kalandra': ['卡兰德的魔镜', 'm', '镜子', '魔镜', 'mirror'],
            "Hinekora's Lock": ['辛格拉的发辫', 'hinekora', 'lock'],
            'Fracturing Orb': ['破溃宝珠', 'f', '破溃', 'fracture'],
            'Orb of Annulment': ['剥离石', 'a', '剥离', 'annul'],
            "Artificer's Orb": ['巧匠石', '巧匠', 'artificer'],
            'Orb of Alchemy': ['点金石', '点金', 'alch'],
            'Orb of Chance': ['机会石', '机会', 'chance'],
            'Orb of Transmutation': ['蜕变石', '蜕变', 'transmute'],
            'Orb of Augmentation': ['增幅石', '增幅', 'augment'],
            "Gemcutter's Prism": ['宝石匠的棱镜', 'g', '宝石匠', 'gcp'],
            "Blacksmith's Whetstone": ['磨刀石', 'whetstone'],
            "Armourer's Scrap": ['护甲片', 'scrap'],
            "Glassblower's Bauble": ['玻璃弹珠', 'bauble'],
            "Arcanist's Etcher": ['奥术师的蚀刻器', '奥术', 'etcher'],
            'Vaal Orb': ['瓦尔宝珠', 'v', '瓦尔', 'vaal'],
            'Architect Orb': ['建筑师宝珠', '建筑师', 'architect'],
            'Cryptic Key': ['神秘钥匙', 'cryptic key'],
            'Verisium': ['维里西姆', 'verisium'],
            'Exceptional Verisium': ['卓越维里西姆', 'exceptional verisium'],
            'Thaumaturgic Flux': ['魔导通量', 'thaumaturgic flux'],
        }
        
        # Build lookup map: alias -> API name
        alias_map = {}
        for api_name, aliases in CURRENCIES.items():
            alias_map[api_name.lower()] = api_name
            for alias in aliases:
                alias_map[alias.lower()] = api_name
        
        # Find from currency (exact match first, then fuzzy match)
        from_en = alias_map.get(from_name.lower())
        if not from_en:
            # Fuzzy match: check if input is a substring of any alias or API name
            for api_name, aliases in CURRENCIES.items():
                if from_name.lower() in api_name.lower():
                    from_en = api_name
                    break
                for alias in aliases:
                    if from_name.lower() in alias.lower():
                        from_en = api_name
                        break
                if from_en:
                    break
        
        if not from_en:
            return f"❌ 未找到通货 '{from_name}'\n💡 可用: D/E/C/R/A/V/M 或 神圣/崇高/混沌/催化剂/愤怒等"

        # Find to currency (exact match first, then fuzzy match)
        to_en = alias_map.get(to_name.lower())
        if not to_en:
            # Fuzzy match: check if input is a substring of any alias or API name
            for api_name, aliases in CURRENCIES.items():
                if to_name.lower() in api_name.lower():
                    to_en = api_name
                    break
                for alias in aliases:
                    if to_name.lower() in alias.lower():
                        to_en = api_name
                        break
                if to_en:
                    break
        
        if not to_en:
            return f"❌ 未找到通货 '{to_name}'\n💡 可用: D/E/C/R/A/V/M 或 神圣/崇高/混沌/催化剂/愤怒等"

        # Get Chinese names from translations module
        from_cn = trans.get_zh_cn(from_en)
        to_cn = trans.get_zh_cn(to_en)

        try:
            ninja_league = NINJA_LEAGUE_MAP.get(league.lower(), league)
            headers = {'User-Agent': 'PoE2NinjaPlugin/1.0'}
            price_map = {}
            primary_unit = None

            for ninja_t in NINJA_TYPE_MAP.values():
                url = f"{NINJA_API_BASE}?league={urllib.parse.quote(ninja_league)}&type={ninja_t}&language=en"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode('utf-8'))

                core = data.get('core', {})
                if primary_unit is None:
                    primary_unit = core.get('primary', 'divine')

                lines_data = data.get('lines', [])
                items_info = {item.get('id', ''): item for item in data.get('items', [])}

                for line in lines_data:
                    item_id = line.get('id', '')
                    pv = float(line.get('primaryValue', 0))
                    if pv <= 0 or not item_id:
                        continue
                    item_detail = items_info.get(item_id, {})
                    en_name = item_detail.get('name', item_id)
                    if en_name not in price_map:
                        price_map[en_name] = pv

            from_price = price_map.get(from_en)
            to_price = price_map.get(to_en)

            if from_price and to_price and to_price > 0:
                rate = from_price / to_price
                if rate >= 1000:
                    rate_str = f"{rate:,.0f}"
                elif rate >= 1:
                    rate_str = f"{rate:.2f}"
                else:
                    rate_str = f"{rate:.4f}"
                return f"💱 {from_cn} → {to_cn}\n\n  1 {from_cn} = {rate_str} {to_cn}\n\n📊 数据来源: poe.ninja"

            return f"❌ 暂无 {from_cn} → {to_cn} 的在售数据"
        except Exception as e:
            return f"❌ 获取通货比例失败: {str(e)}"

    def _get_single_rate(self, league: str, item_name: str, price_currency: str) -> Optional[float]:
        """Get the lowest price of an item in a specific currency using exchange endpoint"""
        try:
            # Use the exchange endpoint for currency exchange rates
            exchange_url = f"{self.BASE_URL}/exchange/{self.GAME}/{urllib.parse.quote(league)}"
            
            # Map currency names to API IDs
            currency_id_map = {
                'Divine Orb': 'divine',
                'Exalted Orb': 'exalted',
                'Chaos Orb': 'chaos',
                'Regal Orb': 'regal',
                'Orb of Annulment': 'annul',
                'Vaal Orb': 'vaal',
                'Orb of Alchemy': 'alch',
                'Orb of Chance': 'chance',
                'Orb of Transmutation': 'transmute',
                'Orb of Augmentation': 'aug',
                "Artificer's Orb": 'artificers',
                'Fracturing Orb': 'fracturing-orb',
                'Mirror of Kalandra': 'mirror',
            }
            
            want_id = currency_id_map.get(item_name, item_name.lower())
            have_id = currency_id_map.get(price_currency, price_currency.lower())
            
            query = {
                'exchange': {
                    'want': [want_id],
                    'have': [have_id],
                    'status': {'option': 'online'}
                }
            }
            
            result = self._fetch_json(exchange_url, json.dumps(query).encode('utf-8'), 'POST')
            
            if not result or not result.get('result'):
                return None
            
            # Parse exchange results
            prices = []
            for item_id, item_data in result['result'].items():
                listing = item_data.get('listing', {})
                offers = listing.get('offers', [])
                for offer in offers:
                    exchange = offer.get('exchange', {})
                    item = offer.get('item', {})
                    if exchange.get('amount') and item.get('amount'):
                        # Calculate rate: exchange.amount / item.amount
                        rate = exchange['amount'] / item['amount']
                        prices.append(rate)
            
            if not prices:
                return None
            
            # Return the median price (skip outliers)
            sorted_prices = sorted(prices)
            if len(sorted_prices) >= 3:
                return sorted_prices[len(sorted_prices) // 2]  # Median
            elif len(sorted_prices) >= 2:
                return sorted_prices[1]  # Skip lowest
            return sorted_prices[0]
        except Exception as e:
            print(f"[TradeAPI] _get_single_rate error: {e}")
            return None

    def _get_multiple_rates(self, league: str, item_name: str, price_currency: str) -> List[float]:
        """Get multiple prices of an item in a specific currency using exchange endpoint"""
        try:
            # Use the exchange endpoint for currency exchange rates
            exchange_url = f"{self.BASE_URL}/exchange/{self.GAME}/{urllib.parse.quote(league)}"
            
            # Map currency names to API IDs
            currency_id_map = {
                'Divine Orb': 'divine',
                'Exalted Orb': 'exalted',
                'Chaos Orb': 'chaos',
                'Regal Orb': 'regal',
                'Orb of Annulment': 'annul',
                'Vaal Orb': 'vaal',
                'Orb of Alchemy': 'alch',
                'Orb of Chance': 'chance',
                'Orb of Transmutation': 'transmute',
                'Orb of Augmentation': 'aug',
                "Artificer's Orb": 'artificers',
                'Fracturing Orb': 'fracturing-orb',
                'Mirror of Kalandra': 'mirror',
            }
            
            want_id = currency_id_map.get(item_name, item_name.lower())
            have_id = currency_id_map.get(price_currency, price_currency.lower())
            
            query = {
                'exchange': {
                    'want': [want_id],
                    'have': [have_id],
                    'status': {'option': 'online'}
                }
            }
            
            result = self._fetch_json(exchange_url, json.dumps(query).encode('utf-8'), 'POST')
            
            if not result or not result.get('result'):
                return []
            
            # Parse exchange results
            prices = []
            for item_id, item_data in result['result'].items():
                listing = item_data.get('listing', {})
                offers = listing.get('offers', [])
                for offer in offers:
                    exchange = offer.get('exchange', {})
                    item = offer.get('item', {})
                    if exchange.get('amount') and item.get('amount'):
                        # Calculate rate: exchange.amount / item.amount
                        rate = exchange['amount'] / item['amount']
                        prices.append(rate)
            
            if not prices:
                return []
            
            # Filter outliers: remove prices that are more than 1.5x or less than 0.67x the median
            sorted_prices = sorted(prices)
            median = sorted_prices[len(sorted_prices) // 2]
            filtered = [p for p in sorted_prices if 0.67 * median <= p <= 1.5 * median]
            
            return filtered if filtered else sorted_prices[:5]  # Return top 5 if no valid prices
        except Exception as e:
            print(f"[TradeAPI] _get_multiple_rates error: {e}")
            return []

    def format_price(self, price_data: Dict) -> str:
        """Format price information with pagination"""
        if not price_data:
            return "❌ 无法获取价格"

        if price_data.get('multiple'):
            matches = price_data.get('matches', [])
            lines = ["🔍 找到多个物品，请选择:"]
            for i, name in enumerate(matches[:10], 1):
                lines.append(f"  {i}. {name}")
            if len(matches) > 10:
                lines.append(f"  ... 还有 {len(matches) - 10} 个")
            lines.append("")
            lines.append("💡 请输入更精确的名称")
            return "\n".join(lines)

        total = price_data.get('total', 0)
        min_price = price_data.get('min_price')
        cn_name = price_data.get('cn_name', '')
        en_name = price_data.get('en_name', '')

        name_str = f"{cn_name}" if cn_name == en_name else f"{cn_name} ({en_name})"

        if not min_price:
            return f"🔍 {name_str}\n📊 在售: {total} 件\n❌ 暂无有标价的在售物品"

        amount = min_price.get('amount', 0)
        currency = min_price.get('currency', 'unknown')
        currency_cn = CURRENCY_MAP.get(currency.lower().replace(' ', ''), currency)

        lines = [f"🔍 {name_str}", f"📊 在售: {total} 件", f"💰 最低价: {amount} {currency_cn}"]

        prices = price_data.get('prices', [])
        if len(prices) > 0:
            lines.append(f"📈 价格分布 (前{len(prices)}个):")
            for p in prices:
                cur = CURRENCY_MAP.get(p['currency'].lower(), p['currency'])
                seller = f" (卖家: {p['seller']})" if p.get('seller') else ""
                lines.append(f"  • {p['amount']} {cur}{seller}")

        return "\n".join(lines)

    def get_item_by_seller(self, seller_name: str) -> Optional[Dict]:
        for item in self._last_search_items:
            if item.get('seller', '').lower() == seller_name.lower():
                return item
        return None

    def get_item_by_index(self, index: int) -> Optional[Dict]:
        if 1 <= index <= len(self._last_search_items):
            return self._last_search_items[index - 1]
        return None

    def format_item_detail(self, item: Dict) -> str:
        if not item:
            return "❌ 未找到物品"

        name = item.get('name', '')
        item_type = item.get('type', '')
        ilvl = item.get('ilvl', 0)
        corrupted = item.get('corrupted', False)

        name_str = f"{name} ({item_type})" if name else item_type
        lines = [f"📦 {name_str}", f"📏 物品等级: {ilvl}"]

        price = item.get('price', {})
        if price:
            cur = CURRENCY_MAP.get(price['currency'].lower(), price['currency'])
            lines.append(f"💰 价格: {price['amount']} {cur}")
            lines.append(f"👤 卖家: {price.get('seller', '未知')}")

        sockets = item.get('sockets', [])
        if sockets:
            socket_strs = [s.get('type', '?') for s in sockets]
            lines.append(f"🔗 插槽: {' '.join(socket_strs)}")

        if corrupted:
            lines.append("⚠️ 已腐化")

        properties = item.get('properties', [])
        if properties:
            lines.append("\n📋 属性:")
            for prop in properties:
                prop_name = prop.get('name', '')
                values = prop.get('values', [])
                if values:
                    val = values[0][0] if values[0] else ''
                    lines.append(f"  {prop_name}: {val}")

        requirements = item.get('requirements', [])
        if requirements:
            lines.append("\n📌 需求:")
            for req in requirements:
                req_name = req.get('name', '')
                values = req.get('values', [])
                if values:
                    val = values[0][0] if values[0] else ''
                    lines.append(f"  {req_name}: {val}")

        implicit_mods = item.get('implicitMods', [])
        if implicit_mods:
            lines.append("\n🔷 隐式词缀:")
            for mod in implicit_mods:
                lines.append(f"  • {self.translate_mod(mod)}")

        explicit_mods = item.get('explicitMods', [])
        if explicit_mods:
            lines.append("\n🔶 显式词缀:")
            for mod in explicit_mods:
                lines.append(f"  • {self.translate_mod(mod)}")

        rune_mods = item.get('runeMods', [])
        if rune_mods:
            lines.append("\n💎 符文词缀:")
            for mod in rune_mods:
                lines.append(f"  • {self.translate_mod(mod)}")

        return "\n".join(lines)

    def translate_mod(self, mod_text: str) -> str:
        mods_cn = self._load_mods_cn()
        if not mods_cn:
            return mod_text

        mods_map = mods_cn.get('mods', {})
        
        # Direct match
        if mod_text in mods_map:
            return mods_map[mod_text]

        result = mod_text
        
        import re
        
        # First, clean up bracket notation like [Charm], [Flask|Flask], Attack|Attack Lightning
        def clean_bracket(match):
            content = match.group(1)
            if '|' in content:
                parts = content.split('|', 1)
                return parts[1] if len(parts) > 1 else parts[0]
            return content
        
        result = re.sub(r'\[([^\]]+)\]', clean_bracket, result)
        
        # Clean up pipe notation like "Attack|Attack Lightning" -> "Attack Lightning"
        result = re.sub(r'(\w+)\|\1', r'\1', result)
        
        # Sort translations by length (longest first) for better matching
        sorted_mods = sorted(mods_map.items(), key=lambda x: -len(x[0]))
        
        # Apply translations multiple times for nested phrases
        for _ in range(3):  # Apply 3 times to catch nested translations
            for en, cn in sorted_mods:
                # Case-insensitive replacement
                result = re.sub(re.escape(en), cn, result, flags=re.IGNORECASE)
        
        # Clean up any remaining English words that have Chinese translations
        def replace_word(match):
            word = match.group(1)
            # Check if this word has a translation
            if word in mods_map:
                return mods_map[word]
            # Check lowercase version
            if word.lower() in mods_map:
                return mods_map[word.lower()]
            return word
        
        result = re.sub(r'\b([A-Za-z]+)\b', replace_word, result)
        
        # Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result

        return result