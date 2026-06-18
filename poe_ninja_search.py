"""
poe.ninja search API protobuf decoder for AstrBot plugin.
Extracts build data from the protobuf response.
Also supports the JSON build-index-state API for current league data.
"""
import json
import math
import struct
import urllib.request
import urllib.parse
import re
from typing import Dict, List, Optional, Tuple, Any


def _to_signed(val: int) -> int:
    """Convert unsigned protobuf varint to signed int64."""
    if val > 0x7FFFFFFFFFFFFFFF:
        val -= 0x10000000000000000
    return val


def _to_signed32(val: int) -> int:
    """Convert unsigned 32-bit value to signed int32."""
    if val > 0x7FFFFFFF:
        val -= 0x100000000
    return val


def _read_varint(data: bytes, pos: int) -> Tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            return result, pos
        shift += 7
    return result, pos


def _decode_protobuf(data: bytes, max_items: int = 500) -> Dict[int, List]:
    """Decode protobuf message into {field_num: [(wire_type_name, value), ...]}"""
    pos = 0
    fields: Dict[int, List] = {}
    count = 0
    while pos < len(data) and count < max_items:
        try:
            tag, pos = _read_varint(data, pos)
            field_num = tag >> 3
            wire_type = tag & 0x07
            if wire_type == 0:  # varint
                value, pos = _read_varint(data, pos)
                fields.setdefault(field_num, []).append(('varint', value))
            elif wire_type == 2:  # length-delimited
                length, pos = _read_varint(data, pos)
                if pos + length > len(data):
                    break
                value = data[pos:pos + length]
                pos += length
                fields.setdefault(field_num, []).append(('bytes', value))
            elif wire_type == 5:  # 32-bit fixed
                value = struct.unpack('<I', data[pos:pos + 4])[0]
                pos += 4
                fields.setdefault(field_num, []).append(('fixed32', value))
            elif wire_type == 1:  # 64-bit fixed
                value = struct.unpack('<Q', data[pos:pos + 8])[0]
                pos += 8
                fields.setdefault(field_num, []).append(('fixed64', value))
            else:
                break
            count += 1
        except Exception:
            break
    return fields


def _try_decode_string(data: bytes) -> Optional[str]:
    try:
        s = data.decode('utf-8')
        if all(32 <= ord(c) < 127 or c in '\n\r\t' for c in s):
            return s
    except Exception:
        pass
    return None


def _extract_strings_from_binary(data: bytes, min_len: int = 3) -> List[str]:
    """Extract all readable ASCII/UTF-8 strings from binary data."""
    return [m.decode('utf-8', 'ignore') for m in re.findall(rb'[\x20-\x7e]{%d,}' % min_len, data)]


def _decode_int_value(v: tuple) -> Any:
    """Decode a protobuf value as an integer (for dimension IDs and counts).
    Handles varint, fixed32, fixed64, and bytes (string or nested varint) wire types."""
    if v[0] == 'varint':
        return _to_signed(v[1])
    elif v[0] == 'fixed32':
        return _to_signed32(v[1])
    elif v[0] == 'fixed64':
        return _to_signed(v[1])
    elif v[0] == 'bytes':
        s = _try_decode_string(v[1])
        if s:
            return s
        # Bytes is not valid UTF-8 — try decoding as a nested varint
        if len(v[1]) > 0:
            try:
                val, _ = _read_varint(v[1], 0)
                return _to_signed(val)
            except Exception:
                pass
    return 0


def _safe_signed(val: Any) -> Any:
    """Convert unsigned 64-bit integers to signed, pass through other types."""
    if isinstance(val, int) and val > 0x7FFFFFFFFFFFFFFF:
        return val - 0x10000000000000000
    return val


def _parse_dimension_block(block_data: bytes) -> Tuple[str, List[Tuple[Any, int]]]:
    """Parse a dimension/filter block: {name, label, entries: [{id, count}]}"""
    fields = _decode_protobuf(block_data, max_items=50)
    name = ""
    entries = []
    
    name_field = fields.get(1, [])
    label_field = fields.get(2, [])
    
    if name_field and name_field[0][0] == 'bytes':
        s = _try_decode_string(name_field[0][1])
        if s: name = s
    
    if label_field and label_field[0][0] == 'bytes':
        s = _try_decode_string(label_field[0][1])
        if s and not name: name = s
    
    for entry_field in fields.get(3, []):
        if entry_field[0] == 'bytes':
            entry_fields = _decode_protobuf(entry_field[1], max_items=10)
            entry_id = 0
            entry_count = 0
            for ef_id, ef_vals in entry_fields.items():
                if ef_id == 1 and ef_vals:
                    entry_id = _decode_int_value(ef_vals[0])
                elif ef_id == 2 and ef_vals:
                    entry_count = _decode_int_value(ef_vals[0])
            entries.append((entry_id, entry_count))
    
    return name, entries


def _parse_stat_block(block_data: bytes) -> Tuple[str, Any]:
    """Parse a stat block like {name, min, max}"""
    fields = _decode_protobuf(block_data, max_items=10)
    name = ""
    min_val = 0
    max_val = 0
    
    name_field = fields.get(1, [])
    if name_field and name_field[0][0] == 'bytes':
        s = _try_decode_string(name_field[0][1])
        if s: name = s
        
    def parse_val(v):
        if v[0] == 'varint':
            # All stats (resistances, life, level, etc.) are varint
            # Large unsigned values are negative numbers in signed int64
            return _to_signed(v[1])
        elif v[0] == 'fixed32':
            # Fixed32 could be float (IEEE 754) or int32
            # For stats, check if it's a reasonable float first
            try:
                f_val = struct.unpack('<f', struct.pack('<I', v[1]))[0]
                if not math.isnan(f_val) and not math.isinf(f_val) and abs(f_val) < 1e5:
                    return int(f_val) if f_val.is_integer() else round(f_val, 1)
            except Exception:
                pass
            return _to_signed32(v[1])
        elif v[0] == 'fixed64':
            # Fixed64 could be double (IEEE 754) or int64
            try:
                d_val = struct.unpack('<d', struct.pack('<Q', v[1]))[0]
                if not math.isnan(d_val) and not math.isinf(d_val) and abs(d_val) < 1e5:
                    return int(d_val) if d_val.is_integer() else round(d_val, 1)
            except Exception:
                pass
            return _to_signed(v[1])
        return 0

    for f_id, f_vals in fields.items():
        if f_id in (2, 3) and f_vals:
            val = parse_val(f_vals[0])
            if f_id == 2:
                min_val = val
            else:
                max_val = val
                
    return name, (min_val, max_val)


class NinjaBuildSearch:
    """Fetches and parses poe.ninja build search data via protobuf API and JSON API."""

    BASE_URL = "https://poe.ninja/poe2/api/builds"
    INDEX_API_URL = "https://poe.ninja/poe2/api/data/build-index-state"

    # Dimension name to Chinese mapping
    DIMENSION_NAMES = {
        'class': '职业',
        'weaponmode': '武器类型',
        'items': '装备',
        'skill': '技能',
        'skills': '技能宝石',
        'skillmodes': '技能模式',
        'keypassive': '关键天赋',
        'keypassives': '关键天赋',
        'anointed': '附魔',
        'allskills': '所有技能',
    }
    
    # PoE2 ascendancy class ID mapping (from poe.ninja protobuf data, 0-based)
    # Note: IDs may change between league patches
    # 来源: https://poe2db.tw/cn/Ascendancy_class
    CLASS_ID_MAP = {
        0: '锐眼', 1: '塑时术师', 2: '泰坦',
        3: '命源法师', 4: '驱炎使', 5: '追猎者',
        6: '神谕者', 7: '古灵使徒斗士', 8: '仪祭师',
        9: '亚马逊', 10: '猎巫人', 11: '深渊巫妖',
        12: '风暴编织者', 13: '祈求者', 14: '夏乌拉追随者',
        15: '萨满', 16: '巫妖', 17: '德鲁伊',
        18: '战术家', 19: '战争使者', 20: '奇塔弗匠师',
        21: '女猎手', 22: '行者', 23: '女巫',
        24: '佣兵', 25: '游侠', 26: '魔巫',
        27: '战士',
    }

    # English class name mapping (extracted from poe.ninja binary data)
    # 来源: https://poe2db.tw/cn/Ascendancy_class
    STRING_CLASS_MAP = {
        # 基础职业
        'Warrior': '战士', 'Ranger': '游侠', 'Sorceress': '魔巫',
        'Monk': '行者', 'Witch': '女巫', 'Mercenary': '佣兵',
        'Huntress': '女猎手', 'Druid': '德鲁伊',
        # 战士升华
        'Titan': '泰坦', 'Warbringer': '战争使者',
        'Smith of Kitava': '奇塔弗匠师',
        # 游侠升华
        'Deadeye': '锐眼', 'Pathfinder': '追猎者',
        # 魔巫升华
        'Stormweaver': '风暴编织者', 'Chronomancer': '塑时术师',
        # 行者升华
        'Invoker': '祈求者', 'Acolyte of Chayula': '夏乌拉追随者',
        # 女巫升华
        'Infernalist': '驱炎使', 'Blood Mage': '命源法师',
        'Lich': '巫妖', 'Abyssal Lich': '深渊巫妖',
        # 佣兵升华
        'Tactician': '战术家', 'Witchhunter': '猎巫人',
        # 女猎手升华
        'Amazon': '亚马逊', 'Ritualist': '仪祭师',
        # 德鲁伊升华
        'Oracle': '神谕者', 'Shaman': '萨满',
        # 其他
        'Gemling Legionnaire': '古灵使徒斗士',
        # PoE1 兼容
        'Duelist': '决斗者', 'Shadow': '暗影',
        'Templar': '圣堂武僧', 'Scion': '贵族',
    }
    
    STAT_NAMES = {
        'level': '等级',
        'life': '生命',
        'energyshield': '能量护盾',
        'mana': '魔力',
        'spirit': '灵力',
        'ehp': '有效生命',
        'movementspeed': '移动速度',
        'liferegen': '生命回复',
        'itemrarity': '物品稀有度',
        'fireres': '火抗',
        'coldres': '冰抗',
        'lightningres': '雷抗',
        'chaosres': '混沌抗',
        'armour': '护甲',
        'evasion': '闪避',
        'block': '格挡',
        'echarges': '球上限',
        'pcharges': '球上限',
        'fcharges': '球上限',
    }
    
    # PoE2 class name mapping (English -> Chinese) for build-index-state API
    # 来源: https://poe2db.tw/cn/Ascendancy_class
    CLASS_NAME_MAP = {
        # 基础职业
        'Warrior': '战士', 'Ranger': '游侠', 'Sorceress': '魔巫',
        'Monk': '行者', 'Witch': '女巫', 'Mercenary': '佣兵',
        'Huntress': '女猎手', 'Druid': '德鲁伊',
        # 战士升华
        'Titan': '泰坦', 'Warbringer': '战争使者',
        'Smith of Kitava': '奇塔弗匠师',
        # 游侠升华
        'Deadeye': '锐眼', 'Pathfinder': '追猎者',
        # 魔巫升华
        'Stormweaver': '风暴编织者', 'Chronomancer': '塑时术师',
        # 行者升华
        'Invoker': '祈求者', 'Acolyte of Chayula': '夏乌拉追随者',
        # 女巫升华
        'Infernalist': '驱炎使', 'Blood Mage': '命源法师',
        'Lich': '巫妖', 'Abyssal Lich': '深渊巫妖',
        # 佣兵升华
        'Tactician': '战术家', 'Witchhunter': '猎巫人',
        # 女猎手升华
        'Amazon': '亚马逊', 'Ritualist': '仪祭师',
        # 德鲁伊升华
        'Oracle': '神谕者', 'Shaman': '萨满',
        # 其他
        'Gemling Legionnaire': '古灵使徒斗士',
        # Runes of Aldur 新职业
        'Martial Artist': '武圣', 'Spirit Walker': '灵魂行者',
        'Disciple of Varashta': '瓦拉煞的门徒',
    }

    def __init__(self):
        self._session_id: Optional[str] = None
        self._index_cache: Optional[Dict] = None

    def _fetch_json(self, url: str) -> Optional[dict]:
        """Fetch JSON data from poe.ninja API."""
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Accept': 'application/json',
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"[poe.ninja] JSON fetch error: {e}")
            return None

    def fetch_build_index(self) -> Optional[Dict]:
        """Fetch build index state from the JSON API (all leagues overview)."""
        if self._index_cache:
            return self._index_cache
        data = self._fetch_json(self.INDEX_API_URL)
        if data and 'leagueBuilds' in data:
            self._index_cache = data
        return data

    def get_league_builds(self, league_url: str = "") -> Optional[Dict]:
        """Get build data for a specific league from the index API.
        If league_url is empty, returns the first (current) league."""
        data = self.fetch_build_index()
        if not data:
            return None
        leagues = data.get('leagueBuilds', [])
        if not leagues:
            return None
        if league_url:
            for league in leagues:
                if league.get('leagueUrl', '').lower() == league_url.lower():
                    return league
            return None
        return leagues[0]

    def list_leagues(self) -> List[Dict]:
        """List all available leagues with build data."""
        data = self.fetch_build_index()
        if not data:
            return []
        return data.get('leagueBuilds', [])

    def search_builds_index(self, query: str = "", league_url: str = "") -> Dict[str, Any]:
        """Search builds using the JSON index API (supports all leagues)."""
        league = self.get_league_builds(league_url)
        if not league:
            return {"error": "无法获取构筑数据"}

        total = league.get('total', 0)
        stats = league.get('statistics', [])
        league_name = league.get('leagueName', league_url)

        # Filter by query if provided
        if query:
            q = query.lower()
            matched = [s for s in stats if q in s.get('class', '').lower()]
            if not matched:
                # Try Chinese name mapping
                matched = []
                for s in stats:
                    cn_name = self.CLASS_NAME_MAP.get(s.get('class', ''), '')
                    if q in cn_name.lower():
                        matched.append(s)
            if not matched:
                return {"error": f"未找到匹配 '{query}' 的职业", "query": query}
            stats = matched

        return {
            "total_builds": total,
            "league_name": league_name,
            "league_url": league.get('leagueUrl', ''),
            "statistics": stats,
        }

    def _get_session_id(self) -> Optional[str]:
        """从 builds 页面动态获取当前 session ID"""
        if self._session_id:
            return self._session_id
        try:
            req = urllib.request.Request(
                "https://poe.ninja/poe2/builds/standard",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            # 从 HTML 中提取 session ID 模式: 数字-日期-数字
            match = re.search(r'(\d{4}-\d{8}-\d+)', html)
            if match:
                self._session_id = match.group(1)
                return self._session_id
            return None
        except Exception:
            return None
    
    def _fetch_protobuf(self, endpoint: str) -> Optional[bytes]:
        """Fetch raw protobuf data from poe.ninja API."""
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity',
                'Referer': 'https://poe.ninja/poe2/builds/standard',
            })
            resp = urllib.request.urlopen(req, timeout=30)
            return resp.read()
        except Exception as e:
            print(f"[poe.ninja] Fetch error: {e}")
            return None
    
    def search_builds(self, query: str = "", league: str = "standard") -> Dict[str, Any]:
        """Search builds on poe.ninja and return parsed data."""
        session_id = self._get_session_id()
        if not session_id:
            return {"error": "无法获取会话ID"}

        endpoint = f"{session_id}/search?overview={league}"
        data = self._fetch_protobuf(endpoint)
        if not data:
            return {"error": "无法获取数据"}

        return self._parse_search_response(data, query)
    
    def _parse_search_response(self, data: bytes, query: str = "") -> Dict[str, Any]:
        """Parse the search protobuf response."""
        result = {
            "total_builds": 0,
            "dimensions": {},
            "stats": {},
            "players": [],
        }
        
        # Extract all readable strings for player/account names
        all_strings = _extract_strings_from_binary(data, min_len=3)
        
        # Parse the protobuf structure
        top_fields = _decode_protobuf(data, max_items=200)
        
        # Field 1 contains the main data structure
        for f1_val in top_fields.get(1, []):
            if f1_val[0] == 'bytes':
                inner = _decode_protobuf(f1_val[1], max_items=200)
                
                # Inner field 1 = total count
                for cf in inner.get(1, []):
                    if cf[0] == 'varint':
                        result["total_builds"] = cf[1]
                
                # Inner field 2 = dimension blocks
                for dim_val in inner.get(2, []):
                    if dim_val[0] == 'bytes':
                        dim_name, entries = _parse_dimension_block(dim_val[1])
                        if dim_name:
                            result["dimensions"][dim_name] = entries
                
                # Inner field 3 = stat blocks
                for stat_val in inner.get(3, []):
                    if stat_val[0] == 'bytes':
                        stat_name, (min_v, max_v) = _parse_stat_block(stat_val[1])
                        if stat_name:
                            result["stats"][stat_name] = {"min": min_v, "max": max_v}
        
        # Extract player names from strings
        # Player names appear after known keywords
        player_names = []
        account_names = []
        
        skip_keywords = {
            'class', 'weaponmode', 'items', 'item', 'skills', 'gem', 
            'skillmodes', 'skillmode', 'keypassives', 'keypassive',
            'anointed', 'allskills', 'level', 'life', 'energyshield',
            'ehp', 'mana', 'spirit', 'movementspeed', 'liferegen',
            'itemrarity', 'fireres', 'coldres', 'lightningres', 'chaosres',
            'echarges', 'fcharges', 'pcharges', 'armour', 'evasion',
            'block', 'Start Search', 'ApplyFilters', 'ApplyIntegerFilters',
            'ApplyFloatFilters', 'ApplySearchFilters', 'SelectTopK',
            'PopulateValues', 'PopulateDimensionCounts',
            'PopulateIntegerDimensionMetadata', 'PopulateFloatDimensionMetadata',
            'BuildResult', 'End Search', 'phystakenas', 'uequip', 'mequip',
            'mweapons', 'marmours', 'physicalmax', 'firemax', 'coldmax',
            'lightningmax', 'chaosmax', 'lowestmax',
        }
        
        # Find the player/account section
        found_account = False
        for s in all_strings:
            if s == 'account':
                found_account = True
                continue
            if found_account and re.match(r'^[A-Za-z0-9_-]+-\d+$', s):
                account_names.append(s)
            elif not found_account and s not in skip_keywords and not s.startswith('Populate') and not s.startswith('Apply') and not s.startswith('Select') and not s.startswith('Build') and not s.startswith('End') and not s.startswith('Start'):
                # Heuristic: player names are usually alphanumeric with underscores
                if re.match(r'^[A-Za-z0-9_]+$', s) and len(s) > 2 and len(s) < 40:
                    player_names.append(s)
        
        # Build player list
        for i, name in enumerate(player_names[:100]):
            account = account_names[i] if i < len(account_names) else ""
            result["players"].append({
                "name": name,
                "account": account,
                "rank": i + 1,
            })
        
        # Filter by query if provided
        if query:
            q = query.lower()
            result["players"] = [
                p for p in result["players"]
                if q in p["name"].lower() or q in p.get("account", "").lower()
            ]
        
        return result
    
    def format_search_result(self, data: Dict[str, Any], query: str = "", league: str = "standard") -> str:
        """Format search result as readable text.
        Supports both protobuf search data and JSON index data."""
        if "error" in data:
            return f"❌ {data['error']}"

        # Check if this is index API data (has 'statistics' key)
        if "statistics" in data:
            return self._format_index_result(data, query)

        # Protobuf search data format
        league_names = {
            "standard": "标准模式",
            "hardcore": "专家模式",
            "mirage": "幻境",
            "miragehc": "专家-幻境",
            "miragessf": "SSF-幻境",
            "miragehcssf": "专家SSF-幻境",
            "mirager": "无情-幻境",
            "miragehcr": "专家无情-幻境",
            "keepers": "守望者",
            "keepershc": "专家-守望者",
            "phrecia2.0": "弗雷西亚2.0",
            "phrecia2.0hc": "专家-弗雷西亚2.0",
            "runesofaldur": "奥杜尔符文",
            "runesofaldurhc": "专家-奥杜尔符文",
        }
        league_display = league_names.get(league, league)

        lines = [f"📊 poe.ninja {league_display} 构筑统计"]

        if query:
            lines.append(f"🔍 搜索: {query}")

        total = data.get("total_builds", 0)
        lines.append(f"总构筑数: {total}")
        lines.append("")

        # Class distribution
        class_dim = data.get("dimensions", {}).get("class", [])
        if class_dim:
            lines.append("📋 职业分布:")

            for cid, count in sorted(class_dim, key=lambda x: -x[1])[:8]:
                if isinstance(cid, str):
                    class_name = self.STRING_CLASS_MAP.get(cid, cid)
                else:
                    class_name = self.CLASS_ID_MAP.get(cid, f"未知(#{cid})")

                pct = (count / total * 100) if total else 0
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                lines.append(f"  {class_name}: {count:>6} ({pct:>5.1f}%) {bar}")
            lines.append("")

        # Stats
        stats = data.get("stats", {})
        if stats:
            lines.append("📈 数值范围:")
            stat_display = [
                ("level", "等级"), ("life", "生命"), ("energyshield", "能量护盾"),
                ("mana", "魔力"), ("fireres", "火抗"), ("coldres", "冰抗"),
                ("lightningres", "雷抗"), ("chaosres", "混沌抗"),
            ]
            for key, label in stat_display:
                if key in stats:
                    s = stats[key]
                    min_v = _safe_signed(s['min'])
                    max_v = _safe_signed(s['max'])
                    lines.append(f"  {label}: {min_v} ~ {max_v}")
            lines.append("")

        # Players
        players = data.get("players", [])
        if players:
            lines.append(f"👥 玩家列表 (前{min(10, len(players))}名):")
            for p in players[:10]:
                acc = f" ({p['account']})" if p.get("account") else ""
                lines.append(f"  #{p['rank']} {p['name']}{acc}")

        return "\n".join(lines)

    def _format_index_result(self, data: Dict[str, Any], query: str = "") -> str:
        """Format result from the build-index-state JSON API."""
        league_name = data.get("league_name", "未知")
        total = data.get("total_builds", 0)
        stats = data.get("statistics", [])

        lines = [f"📊 poe.ninja {league_name} 构筑统计"]

        if query:
            lines.append(f"🔍 搜索: {query}")

        lines.append(f"总构筑数: {total:,}")
        lines.append("")

        if stats:
            lines.append("📋 职业分布:")
            for s in stats[:10]:
                class_en = s.get('class', '')
                class_cn = self.CLASS_NAME_MAP.get(class_en, class_en)
                pct = s.get('percentage', 0)
                trend = s.get('trend', 0)
                trend_icon = '↑' if trend > 0 else '↓' if trend < 0 else '→'
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                lines.append(f"  {class_cn}: {pct:>5.1f}% {trend_icon} {bar}")
            lines.append("")

        return "\n".join(lines)