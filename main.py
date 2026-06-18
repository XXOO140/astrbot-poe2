import sys
import os
import json
import importlib
import tempfile

# 确保插件目录在 Python 路径中
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from astrbot.api.star import Context, Star
from astrbot.api.event import filter, AstrMessageEvent

from poe_trade_api import TradeAPI

# 配置文件路径
CONFIG_FILE = os.path.join(_plugin_dir, "config.json")


def load_config() -> dict:
    """加载配置文件"""
    default_config = {
        "league": "runesofaldur",
        "game": "poe2",
        "poesessid": "",
        "trade_api_enabled": False,
        "trade_league": "Mirage",
        "cache_duration_minutes": 30
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
    except Exception as e:
        print(f"[Config] Load error: {e}")
    return default_config


def save_config(config: dict):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Config] Save error: {e}")


class PoE2NinjaPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.local_config = load_config()
        self.config = config or {}
        self.league = self.config.get("league", self.local_config.get("league", "runesofaldur"))
        self.game = self.config.get("game", self.local_config.get("game", "poe2"))

        # Trade API
        poesessid = self.config.get("poesessid", self.local_config.get("poesessid", ""))
        self.trade_api = TradeAPI(poesessid)
        self.trade_enabled = self.local_config.get("trade_api_enabled", bool(poesessid))
        self.trade_league = self.local_config.get("trade_league", "Standard")

    # ============ Trade API 命令 ============

    @filter.command("poe2 重载", aliases=["poe 重载", "poe2 reload", "poe reload"],
                    description="热重载插件代码 (无需重启AstrBot)")
    async def handle_reload(self, event: AstrMessageEvent):
        try:
            import translations
            translations._translations_cache = None

            import poe_trade_api
            importlib.reload(poe_trade_api)
            from poe_trade_api import TradeAPI

            poesessid = self.local_config.get("poesessid", "")
            self.trade_api = TradeAPI(poesessid)

            yield event.plain_result(
                f"✅ 插件热重载成功！\n"
                f"📦 版本: {poe_trade_api.TradeAPI.APP_VERSION}\n"
                f"🔄 翻译缓存已刷新，无需重启 AstrBot"
            )
        except Exception as e:
            yield event.plain_result(f"❌ 重载失败: {str(e)}")

    @filter.command("poe2 设置sessid", aliases=["poe 设置sessid", "poe2 sessid", "poe sessid"],
                    description="设置 POESESSID 以启用传说装备查价")
    async def handle_set_sessid(self, event: AstrMessageEvent, sessid: str = ""):
        if not sessid:
            yield event.plain_result(
                "用法: poe2 设置sessid <你的POESESSID>\n\n"
                "📌 如何获取 POESESSID:\n"
                "1. 登录 https://www.pathofexile.com\n"
                "2. 按 F12 打开开发者工具\n"
                "3. 切换到 Application/存储 标签\n"
                "4. 在 Cookies 中找到 POESESSID\n"
                "5. 复制值并发送给我"
            )
            return

        self.local_config["poesessid"] = sessid
        self.local_config["trade_api_enabled"] = True
        save_config(self.local_config)
        self.trade_api.poesessid = sessid
        self.trade_enabled = True

        yield event.plain_result("✅ POESESSID 已保存！传说装备查价功能已启用。\n使用 'poe2 物价 <物品名称>' 查询价格。")

    @filter.command("poe2 物价", aliases=["poe 物价", "poe2 trade", "poe trade"],
                    description="查询传说装备交易价格")
    async def handle_trade_price(self, event: AstrMessageEvent, args: str = ""):
        if not args:
            yield event.plain_result(
                "用法: poe2 物价 <物品名称>\n"
                "示例:\n"
                "  poe2 物价 猎首\n"
                "  poe2 物价 Headhunter\n\n"
                "💡 支持简体/繁体/英文，支持模糊搜索"
            )
            return

        if not self.trade_enabled:
            yield event.plain_result(
                "❌ 传说装备查价功能未启用\n"
                "请先使用 'poe2 设置sessid <POESESSID>' 设置凭证"
            )
            return

        try:
            item_name = args.strip()
            league = self.trade_league
            price_data = self.trade_api.get_item_price(league, item_name)
            if not price_data:
                yield event.plain_result(f"❌ 未找到 '{item_name}' 的交易信息")
                return

            result = self.trade_api.format_price(price_data)
            lines = [result, "", f"📅 赛季: {league}"]
            yield event.plain_result("\n".join(lines))

        except Exception as e:
            yield event.plain_result(f"❌ 查询失败: {str(e)}")

    @filter.command("poe2 查看", aliases=["poe 查看", "poe2 view", "poe view"],
                    description="查看卖家物品详情")
    async def handle_view_seller(self, event: AstrMessageEvent, args: str = ""):
        if not args:
            yield event.plain_result(
                "用法: poe2 查看 <卖家名或序号>\n"
                "示例:\n"
                "  poe2 查看 1\n"
                "  poe2 查看 Daniel#5289\n\n"
                "💡 需先使用 'poe2 物价' 搜索，再查看详情"
            )
            return

        try:
            items = self.trade_api._last_search_items
            if not items:
                yield event.plain_result("❌ 暂无缓存数据，请先使用 'poe2 物价' 搜索")
                return

            # Check if args is a number (index)
            if args.isdigit():
                index = int(args)
                if 1 <= index <= len(items):
                    item = items[index - 1]
                    result = self.trade_api.format_item_detail(item)
                    yield event.plain_result(result)
                    return
                else:
                    yield event.plain_result(f"❌ 序号超出范围，请输入 1-{len(items)}")
                    return

            # Search by seller name
            found = None
            for item in items:
                if item.get('seller', '').lower() == args.lower():
                    found = item
                    break

            if found:
                result = self.trade_api.format_item_detail(found)
                yield event.plain_result(result)
            else:
                yield event.plain_result(f"❌ 未找到卖家 '{args}'\n💡 可尝试输入序号 (1-{len(items)})")

        except Exception as e:
            yield event.plain_result(f"❌ 查询失败: {str(e)}")

    @filter.command("poe2 属性", aliases=["poe 属性", "poe2 stat", "poe stat"],
                    description="搜索带指定属性的传说装备")
    async def handle_search_mod(self, event: AstrMessageEvent, arg1: str = "", arg2: str = ""):
        if not arg1:
            yield event.plain_result(
                "用法: poe2 属性 <关键词1,关键词2,...> [页码]\n"
                "示例:\n"
                "  poe2 属性 力量\n"
                "  poe2 属性 暴击,生命\n"
                "  poe2 属性 暴击,攻速,力量 2\n\n"
                "💡 逗号分隔多个关键词，空格后跟页码"
            )
            return

        try:
            # Parse keywords (comma-separated)
            keywords = [kw.strip() for kw in arg1.split(',') if kw.strip()]
            keyword = ' '.join(keywords)
            
            # Parse page number
            page = int(arg2) if arg2 and arg2.isdigit() else 1
            
            if not keyword:
                yield event.plain_result("❌ 请输入搜索关键词")
                return
            
            # Use local data for search
            results = self.trade_api.search_local_by_mod(keyword)
            result = self.trade_api.format_local_search(results, keyword, page)
            yield event.plain_result(result)
        except Exception as e:
            yield event.plain_result(f"❌ 查询失败: {str(e)}")

    @filter.command("poe2 装备", aliases=["poe 装备", "poe2 item", "poe item"],
                    description="按装备名搜索传说装备")
    async def handle_search_item(self, event: AstrMessageEvent, keyword: str = ""):
        if not keyword:
            yield event.plain_result(
                "用法: poe2 装备 <装备名或序号>\n"
                "示例:\n"
                "  poe2 装备 猎首\n"
                "  poe2 装备 Headhunter\n"
                "  poe2 装备 1\n\n"
                "💡 支持中英文模糊搜索"
            )
            return

        try:
            # Check if keyword is a number (index)
            if keyword.isdigit():
                index = int(keyword)
                if hasattr(self, '_last_local_results') and self._last_local_results:
                    if 1 <= index <= len(self._last_local_results):
                        item = self._last_local_results[index - 1]
                        result = self.trade_api.format_local_item_detail(item)
                        yield event.plain_result(result)
                        return
                    else:
                        yield event.plain_result(f"❌ 序号超出范围，请输入 1-{len(self._last_local_results)}")
                        return
                else:
                    yield event.plain_result("❌ 请先使用 'poe2 装备 <名称>' 搜索")
                    return
            
            # Use local data for search
            results = self.trade_api.search_local_by_name(keyword)
            self._last_local_results = results  # Cache results
            
            # If only 1 result, show details directly
            if len(results) == 1:
                result = self.trade_api.format_local_item_detail(results[0])
            else:
                result = self.trade_api.format_local_search(results, keyword)
            
            yield event.plain_result(result)
        except Exception as e:
            yield event.plain_result(f"❌ 查询失败: {str(e)}")

    _CATEGORY_ALIASES = {
        '全部': None, 'all': None,
        '通货': 'currency', 'currency': 'currency',
        '碎片': 'fragments', '门票': 'fragments', 'fragment': 'fragments', 'fragments': 'fragments',
        '符文': 'runes', '镶嵌': 'runes', 'rune': 'runes', 'runes': 'runes',
        '精华': 'essences', 'essence': 'essences', 'essences': 'essences',
        '终局': 'ultimatum', '魂核': 'ultimatum', 'ultimatum': 'ultimatum',
        '探险': 'expedition', 'expedition': 'expedition',
        '通量': 'expedition', 'flux': 'expedition',
        '仪式': 'ritual', '祭坛': 'ritual', 'ritual': 'ritual',
        '圣物钥匙': 'vaultkeys', 'vaultkey': 'vaultkeys', 'vaultkeys': 'vaultkeys',
        '裂隙': 'breach', 'breach': 'breach',
        '催化剂': 'breach', 'catalyst': 'breach',
        '深渊': 'abyss', 'abyss': 'abyss',
        '未切割': 'uncutgems', 'uncut': 'uncutgems', 'uncutgems': 'uncutgems',
        '血统': 'lineagesupportgems', '辅助宝石': 'lineagesupportgems', 'lineage': 'lineagesupportgems', 'lineagesupportgems': 'lineagesupportgems',
        '谵妄': 'delirium', 'delirium': 'delirium',
        '涂油': 'delirium', 'oil': 'delirium',
        '入侵': 'incursion', '神庙': 'incursion', 'incursion': 'incursion',
        '神像': 'idol', 'idol': 'idol',
        '维里西姆': 'verisium', '合金': 'verisium', 'alloy': 'verisium', 'verisium': 'verisium',
        '瓦尔': 'vaal', 'vaal': 'vaal',
        '饰品': 'accessory', 'accessory': 'accessory',
        '护甲': 'armour', 'armour': 'armour',
        '药剂': 'flask', 'flask': 'flask',
        '珠宝': 'jewel', 'jewel': 'jewel',
        '地图': 'map', 'map': 'map',
        '圣域': 'sanctum', 'sanctum': 'sanctum',
        '护身符': 'talismans', 'talismans': 'talismans',
        '传送石': 'waystones', 'waystones': 'waystones',
        '武器': 'weapon', 'weapon': 'weapon',
    }

    @filter.command("poe2 通货", aliases=["poe 通货", "poe2 currency", "poe currency", "poe2 通货比例"],
                    description="查询通货比例")
    async def handle_currency_rate(self, event: AstrMessageEvent, arg1: str = "", arg2: str = ""):
        if not self.trade_enabled:
            yield event.plain_result(
                "❌ 传说装备查价功能未启用\n"
                "请先使用 'poe2 设置sessid <POESESSID>' 设置凭证"
            )
            return

        try:
            league = self.trade_league
            category = self._CATEGORY_ALIASES.get(arg1.lower() if arg1 else '')
            is_image_request = (arg1.lower() in self._CATEGORY_ALIASES if arg1 else False) and not arg2

            if is_image_request:
                from poe_trade_api import ITEM_ONLY_CATEGORIES

                if category in ITEM_ONLY_CATEGORIES:
                    data = self.trade_api.get_all_item_prices(league, category=category, top_n=20)
                else:
                    data = self.trade_api.get_all_currency_rates(league, category=category, top_n=20)

                if not data or not data.get('items'):
                    yield event.plain_result("❌ 获取数据失败")
                    return

                img_bytes = self.trade_api.render_currency_image(league, data, category=category)
                if img_bytes:
                    tmp_dir = tempfile.gettempdir()
                    img_path = os.path.join(tmp_dir, f"poe2_currency_{league}.png")
                    with open(img_path, 'wb') as f:
                        f.write(img_bytes)
                    yield event.image_result(img_path)
                else:
                    text_result = self.trade_api.format_currency_text(league, data, category=category)
                    yield event.plain_result(text_result)
                return

            if not arg1:
                result = self.trade_api.get_currency_rates(league)
            elif not arg2:
                result = self.trade_api.get_currency_rate(league, arg1, '崇高')
            else:
                result = self.trade_api.get_currency_rate(league, arg1, arg2)

            yield event.plain_result(result)
        except Exception as e:
            yield event.plain_result(f"❌ 查询失败: {str(e)}")

    @filter.command("poe2 帮助", aliases=["poe 帮助"], description="显示使用说明")
    async def handle_help(self, event: AstrMessageEvent):
        help_text = (
            "🎮 PoE2 助手 v4.2.0 - 使用说明\n\n"
            "🔮 市集查价 (官方 trade2 API):\n"
            "  poe2 设置sessid <ID> - 设置登录凭证\n"
            "  poe2 物价 <名称> - 查询传说装备价格\n"
            "  poe2 查看 <卖家名/序号> - 查看卖家物品详情\n"
            "  poe2 通货 [A] [B] - 查询通货比例\n\n"
            "🔍 传说装备查询:\n"
            "  poe2 属性 <关键词> [页码] - 搜索带该属性的装备\n"
            "  poe2 装备 <装备名/序号> - 按装备名搜索\n\n"
            "💡 属性搜索支持逗号分隔多关键词:\n"
            "  poe2 属性 暴击,攻速 → 同时包含暴击和攻速\n"
            "  poe2 属性 暴击,攻速,力量 2 → 第2页\n\n"
            "💰 通货价格图片 (poe.ninja 数据):\n"
            "  poe2 通货 全部 → TOP20全部通货比例图片\n"
            "  poe2 通货 通货 → 通货分类\n"
            "  poe2 通货 碎片/门票 → 碎片分类\n"
            "  poe2 通货 符文/镶嵌 → 符文分类\n"
            "  poe2 通货 精华 → 精华分类\n"
            "  poe2 通货 魂核 → 魂核分类\n"
            "  poe2 通货 探险/通量 → 探险分类\n"
            "  poe2 通货 仪式/祭坛 → 仪式分类\n"
            "  poe2 通货 圣物钥匙 → 圣物钥匙分类\n"
            "  poe2 通货 裂隙/催化剂 → 裂隙分类\n"
            "  poe2 通货 深渊 → 深渊分类\n"
            "  poe2 通货 未切割 → 未切割宝石\n"
            "  poe2 通货 血统/辅助宝石 → 血统辅助宝石\n"
            "  poe2 通货 谵妄/涂油 → 谵妄分类\n"
            "  poe2 通货 入侵/神庙 → 入侵分类\n"
            "  poe2 通货 神像 → 神像分类\n"
            "  poe2 通货 维里西姆/合金 → 维里西姆分类\n"
            "  poe2 通货 瓦尔 → 瓦尔分类\n\n"
            "⚔️ 装备价格图片 (poe.ninja 数据):\n"
            "  poe2 通货 饰品 → 饰品价格\n"
            "  poe2 通货 护甲 → 护甲价格\n"
            "  poe2 通货 药剂 → 药剂价格\n"
            "  poe2 通货 珠宝 → 珠宝价格\n"
            "  poe2 通货 地图 → 地图价格\n"
            "  poe2 通货 圣域 → 圣域研究价格\n"
            "  poe2 通货 护身符 → 护身符价格\n"
            "  poe2 通货 传送石 → 传送石价格\n"
            "  poe2 通货 武器 → 武器价格\n\n"
            "💡 通货快捷查询 (文字):\n"
            "  poe2 通货 → 查看主要通货比例\n"
            "  poe2 通货 d c → 神圣比混沌\n"
            "  poe2 通货 e → 崇高比神圣\n"
            "  快捷: D=神圣 E=崇高 C=混沌 镜子=魔镜\n\n"
            "🔧 系统命令:\n"
            "  poe2 重载 - 热重载插件+刷新翻译缓存\n"
            "  poe2 帮助 - 显示此帮助\n\n"
            "📌 数据来源:\n"
            "  pathofexile.com | poe2scout.com | poe2wiki.net | poe2db.tw\n"
            "  感谢所有为 PoE2 社区提供数据支持的网站！"
        )
        yield event.plain_result(help_text)