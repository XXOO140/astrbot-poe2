"""
poe.ninja API 客户端 - 纯 stdlib 实现，无外部依赖
提供物品价格查询功能，带本地文件缓存
"""
import json
import time
import os
import re
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List


# ──────────────── 常量 ────────────────

# 价格数据 API 基址
NINJA_API_BASE = "https://poe.ninja/api/data"

# 赛季映射
SEASON_MAP = {
    "standard": "Standard",
    "hardcore": "Hardcore",
}

# 构建 API URL
def build_api_url(league: str, game: str = "poe2", item_type: str = "Currency") -> str:
    """构建 poe.ninja API URL（使用 itemoverview 端点，兼容 PoE2）"""
    league_name = SEASON_MAP.get(league, league)
    return f"{NINJA_API_BASE}/itemoverview?league={urllib.parse.quote(league_name)}&game={game}&type={item_type}"


# ──────────────── 价格 API ────────────────

class NinjaPriceAPI:
    """poe.ninja 价格查询 API 封装"""
    
    CACHE_TTL = 300  # 5分钟缓存
    
    # 支持的物品类型
    CATEGORIES = {
        "currency": ("CurrencyOverview", "Currency"),
        "fragment": ("CurrencyOverview", "Fragment"),
        "oil": ("ItemOverview", "Oil"),
        "incubator": ("ItemOverview", "Incubator"),
        "scarab": ("ItemOverview", "Scarab"),
        "fossil": ("ItemOverview", "Fossil"),
        "resonator": ("ItemOverview", "Resonator"),
        "artifact": ("ItemOverview", "Artifact"),
        "skill": ("ItemOverview", "SkillGem"),
        "gem": ("ItemOverview", "SkillGem"),
        "divination": ("ItemOverview", "DivinationCard"),
        "divcard": ("ItemOverview", "DivinationCard"),
        "card": ("ItemOverview", "DivinationCard"),
        "base": ("ItemOverview", "BaseType"),
        "helmet": ("ItemOverview", "BaseType"),
        "glove": ("ItemOverview", "BaseType"),
        "boot": ("ItemOverview", "BaseType"),
        "armor": ("ItemOverview", "BaseType"),
        "ring": ("ItemOverview", "BaseType"),
        "amulet": ("ItemOverview", "BaseType"),
        "belt": ("ItemOverview", "BaseType"),
        "weapon": ("ItemOverview", "BaseType"),
        "jewel": ("ItemOverview", "Jewel"),
        "cluster": ("ItemOverview", "ClusterJewel"),
        "flask": ("ItemOverview", "Flask"),
        "map": ("ItemOverview", "Map"),
        "memory": ("ItemOverview", "Memory"),
        "uniques": ("ItemOverview", "UniqueMap"),
        "unique": ("ItemOverview", "UniqueMap"),
    }
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
        self.data: Dict[str, Any] = {}
    
    def get_api_url(self, league: str, game: str = "poe2", item_type: str = "Currency") -> str:
        return build_api_url(league, game, item_type)
    
    def _cache_key(self, url: str) -> str:
        return url
    
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_time:
            return False
        return (time.time() - self._cache_time[key]) < self.CACHE_TTL
    
    def load_data(self, data: dict):
        """加载 API 返回的 JSON 数据"""
        self.data = data
    
    def _fetch_json(self, url: str) -> Optional[dict]:
        """发起 HTTP GET 请求并返回 JSON"""
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Referer': 'https://poe.ninja/',
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[NinjaPriceAPI] 请求失败: {url} -> {e}")
            return None
    
    def search(self, query: str, data: dict = None) -> dict:
        """搜索物品"""
        if data is None:
            data = self.data
        
        if not data:
            return {"error": "没有数据，请先刷新"}
        
        if not query:
            return {"error": "请输入搜索关键词"}
        
        query_lower = query.lower()
        results = []
        
        lines = data.get("lines", [])
        for item in lines:
            name = item.get("name", "")
            # 货币类型用 currencyTypeName，物品类型用 name
            if not name:
                name = item.get("currencyTypeName", "")
            
            if query_lower in name.lower():
                chaos_value = item.get("chaosEquivalent", item.get("listingCount", 0))
                divine_value = item.get("divineEquivalent", 0)
                sparkline = item.get("sparkline", {})
                low = sparkline.get("low", 0)
                high = sparkline.get("high", 0)
                change = 0
                if low and low > 0:
                    change = ((high - low) / low) * 100 if high else 0
                
                results.append({
                    "name": name,
                    "chaosValue": round(chaos_value, 1) if isinstance(chaos_value, float) else chaos_value,
                    "divineValue": round(divine_value, 1) if isinstance(divine_value, float) else divine_value,
                    "sparkline": f"{'↑' if change > 0 else '↓' if change < 0 else '→'} {change:+.1f}%",
                    "typeGroup": self._get_type_group(item),
                })
        
        if not results:
            return {"error": f"未找到匹配 '{query}' 的物品", "query": query}
        
        return {"results": results, "query": query}
    
    def _get_type_group(self, item: dict) -> str:
        """获取物品分类"""
        if "currencyTypeName" in item:
            return "货币"
        lines = item.get("listingCount", 0)
        item_class = item.get("itemClass", 0)
        class_map = {
            0: "普通物品",
            1: "通货",
            2: "地图",
            3: "碎片",
            4: "地图碎片",
            5: "命运卡",
            6: "药剂",
            7: "技能宝石",
            8: "辅助宝石",
        }
        return class_map.get(item_class, "物品")
    
    def get_mod_data(self, mod_name: str, data: dict = None) -> dict:
        """搜索词缀相关物品"""
        if data is None:
            data = self.data
        
        if not data:
            return {"error": "没有数据，请先刷新"}
        
        if not mod_name:
            return {"error": "请输入词缀关键词"}
        
        query_lower = mod_name.lower()
        results = []
        
        lines = data.get("lines", [])
        for item in lines:
            # 检查物品的各种属性中是否包含词缀关键词
            name = item.get("name", "")
            type_name = item.get("type", "")
            desc = item.get("desc", "")
            
            searchable = f"{name} {type_name} {desc}".lower()
            if query_lower in searchable:
                chaos_value = item.get("chaosEquivalent", item.get("listingCount", 0))
                results.append({
                    "name": name,
                    "type": type_name,
                    "chaosValue": round(chaos_value, 1) if isinstance(chaos_value, float) else chaos_value,
                    "typeGroup": self._get_type_group(item),
                    "desc": desc[:100] if desc else "",
                })
        
        if not results:
            return {"error": f"未找到与 '{mod_name}' 相关的物品", "query": mod_name}
        
        return {"results": results, "query": mod_name}