from typing import List, Tuple, Type, Any, Dict, Optional
import os
import threading
import json
import requests
from datetime import datetime, timezone

# 导入 MaiBot 插件系统
from src.plugin_system import BasePlugin, register_plugin, ComponentInfo
from src.plugin_system.base.config_types import ConfigField
from src.plugin_system.base.base_command import BaseCommand

# 兼容不同版本 MaiBot：定义枚举类型（新旧框架都可用）
class ComponentType:
    COMMAND = "command"
    ACTION = "action"
    TOOL = "tool"
    EVENT_HANDLER = "event_handler"

# 日志系统
from src.common.logger import get_logger
logger = get_logger("steam_status_plugin")

# 常量配置
STEAM_API_HOST = "https://api.steampowered.com"
TIMEOUT = 8
PERSONA_STATE = {
    0: "离线",
    1: "在线",
    2: "忙碌",
    3: "离开",
    4: "暂离（打盹）",
    5: "寻找交易",
    6: "寻找玩伴",
}

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
_lock = threading.Lock()


# ====== 数据存取 ======
def _load_store() -> Dict[str, Any]:
    with _lock:
        if not os.path.exists(DATA_FILE):
            return {}
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

def _save_store(store: Dict[str, Any]) -> None:
    with _lock:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)

def _get_chat_key(ctx_or_msg: Any) -> str:
    try:
        candidate = ctx_or_msg if isinstance(ctx_or_msg, dict) else getattr(ctx_or_msg, "context", {})
        for k in ("chat_id", "chat", "group_id", "room_id", "channel_id", "conversation_id"):
            v = (candidate or {}).get(k)
            if v:
                return str(v)
    except Exception:
        pass
    return "global"


# ====== Steam API 封装 ======
class SteamService:
    def __init__(self, api_key: str):
        self.api_key = (api_key or "").strip()

    def resolve_vanity(self, vanity: str) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            r = requests.get(
                f"{STEAM_API_HOST}/ISteamUser/ResolveVanityURL/v1/",
                params={"key": self.api_key, "vanityurl": vanity},
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            resp = r.json().get("response", {})
            if resp.get("success") == 1 and resp.get("steamid"):
                return str(resp["steamid"])
        except Exception:
            pass
        return None

    def get_summary(self, steamid64: str) -> Dict[str, Any]:
        if not self.api_key:
            return {}
        try:
            r = requests.get(
                f"{STEAM_API_HOST}/ISteamUser/GetPlayerSummaries/v2/",
                params={"key": self.api_key, "steamids": steamid64},
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            players = r.json().get("response", {}).get("players", [])
            return players[0] if players else {}
        except Exception:
            return {}

    @staticmethod
    def fmt_ts(ts: int) -> str:
        try:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone()
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            return str(ts)

    @staticmethod
    def norm_alias(s: str) -> str:
        return s.strip().lstrip("@").lower()

    # 修正版：支持 SteamID32 → SteamID64 自动转换
    def norm_identifier(self, s: str) -> Optional[str]:
        s = s.strip().lstrip("@")
        if not s:
            return None

        # 纯数字处理
        if s.isdigit():
            if len(s) >= 16:
                # SteamID64
                return s
            try:
                # SteamID32 转换为 SteamID64
                sid64 = int(s) + 76561197960265728
                return str(sid64)
            except Exception:
                return None

        # vanity URL
        return self.resolve_vanity(s)


# ====== Command 组件 ======
class SteamCommand(BaseCommand):
    """
    /steam help
    /steam link <别名> <steamid|vanity>
    /steam unlink <别名>
    /steam list
    /steam status <别名|steamid|vanity>
    /steam whois <别名>
    """
    command_name = "steam"
    command_description = "Steam 在线状态与别名绑定（子命令：help/link/unlink/list/status/whois）"
    command_pattern = r"^/?steam\s+(?P<sub>help|status|link|unlink|list|whois)(?:\s+(?P<a>\S+))?(?:\s+(?P<b>\S+))?\s*$"

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        api_key = self.get_config("steam.api_key", "")
        service = SteamService(api_key=api_key)

        sub = (self.matched_groups.get("sub") or "").lower()
        a = self.matched_groups.get("a") or ""
        b = self.matched_groups.get("b") or ""

        if not hasattr(self, "context"):
            self.context = getattr(self, "event", {}).get("context", {})

        if sub == "help" or not sub:
            await self.send_text(self.help_text()); return True, "ok", True
        if sub == "list":
            await self.send_text(self.do_list()); return True, "ok", True
        if sub == "unlink" and a:
            await self.send_text(self.do_unlink(a)); return True, "ok", True
        if sub == "whois" and a:
            await self.send_text(self.do_whois(a, service)); return True, "ok", True
        if sub == "link" and a and b:
            await self.send_text(self.do_link(a, b, service)); return True, "ok", True
        if sub == "status" and a:
            await self.send_text(self.do_status(a, service)); return True, "ok", True

        await self.send_text("用法不正确。输入 /steam help 查看帮助。")
        return False, "bad-args", True

    def help_text(self) -> str:
        return (
            "Steam 插件帮助\n"
            "- /steam help 查看帮助\n"
            "- /steam link <别名> <steamid|vanity> 绑定别名\n"
            "- /steam unlink <别名> 解绑别名\n"
            "- /steam list 查看本群所有绑定\n"
            "- /steam status <别名|steamid|vanity> 查询在线状态\n"
            "- /steam whois <别名> 查看绑定详情\n"
            "请在配置中填写 steam.api_key（https://steamcommunity.com/dev/apikey），并将 plugin.enabled = true。"
        )

    def do_link(self, alias: str, ident: str, service: SteamService) -> str:
        if not service.api_key:
            return "请先配置 steam.api_key。"
        alias = service.norm_alias(alias)
        steamid = service.norm_identifier(ident)
        if not steamid:
            return f"无法解析为 SteamID：{ident}"

        info = service.get_summary(steamid)
        if not info:
            return f"绑定失败：未能获取该账号信息（steamid: {steamid}）。"

        store = _load_store()
        chat = _get_chat_key(self.context)
        aliases = store.setdefault(chat, {}).setdefault("aliases", {})
        aliases[alias] = {
            "steamid": steamid,
            "profileurl": info.get("profileurl", ""),
            "personaname": info.get("personaname", ""),
            "created_at": int(datetime.now(timezone.utc).timestamp())
        }
        _save_store(store)
        return f"已绑定：{alias} -> {info.get('personaname','')} ({steamid})"

    def do_unlink(self, alias: str) -> str:
        alias = alias.strip().lstrip("@").lower()
        store = _load_store()
        chat = _get_chat_key(self.context)
        aliases = store.get(chat, {}).get("aliases", {})
        if alias not in aliases:
            return f"未找到别名：{alias}"
        del aliases[alias]
        _save_store(store)
        return f"已解除绑定：{alias}"

    def do_list(self) -> str:
        store = _load_store()
        chat = _get_chat_key(self.context)
        aliases = store.get(chat, {}).get("aliases", {})
        if not aliases:
            return "本群未绑定任何别名。\n请使用：/steam link <别名> <steamid|vanity>"
        out = ["本群绑定列表："]
        for a, v in aliases.items():
            out.append(f"- {a} -> {v.get('personaname','-')} ({v.get('steamid')})")
        return "\n".join(out)

    def do_whois(self, alias: str, service: SteamService) -> str:
        alias = alias.strip().lstrip("@").lower()
        store = _load_store()
        chat = _get_chat_key(self.context)
        rec = store.get(chat, {}).get("aliases", {}).get(alias)
        if not rec:
            return f"未找到别名：{alias}"
        sid = rec["steamid"]
        info = service.get_summary(sid)
        if not info:
            return f"{alias} -> {sid}\n无法获取详细信息，可能隐私未公开或 API 出错。"
        vis = info.get("communityvisibilitystate")
        privacy = "" if vis == 3 else "该用户资料未公开或部分未公开。"
        lines = [f"{alias} -> {info.get('personaname','<未公开>')}（{sid}）"]
        if info.get("profileurl"):
            lines.append(f"档案: {info['profileurl']}")
        if privacy:
            lines.append(privacy)
        return "\n".join(lines)

    def do_status(self, target: str, service: SteamService) -> str:
        store = _load_store()
        chat = _get_chat_key(self.context)
        rec = store.get(chat, {}).get("aliases", {}).get(service.norm_alias(target))
        sid = rec["steamid"] if rec else service.norm_identifier(target)
        if not sid:
            return f"无法解析为 SteamID：{target}"

        info = service.get_summary(sid)
        if not info:
            return f"未能获取到用户信息（steamid: {sid}），可能是隐私设置或 API 出错。"

        vis = info.get("communityvisibilitystate")
        privacy = "" if vis == 3 else "该用户的个人资料未公开，可用信息受限。"
        name = info.get("personaname", "<未公开昵称>")
        state = info.get("personastate")

        if state is None:
            parts = [f"玩家: {name}（{sid}）", "状态: 无法判断（可能因隐私未公开）"]
            if info.get("profileurl"):
                parts.append(f"档案: {info['profileurl']}")
            if privacy:
                parts.append(privacy)
            return "\n".join(parts)

        s_text = PERSONA_STATE.get(state, f"未知状态({state})")
        parts = [f"玩家: {name}（{sid}）", f"状态: {s_text}"]
        if info.get("gameextrainfo"):
            parts.append(f"当前游戏: {info['gameextrainfo']}")
        if state == 0 and info.get("lastlogoff"):
            parts.append(f"最后下线时间: {service.fmt_ts(info['lastlogoff'])}")
        if info.get("profileurl"):
            parts.append(f"档案: {info['profileurl']}")
        if privacy:
            parts.append(privacy)
        return "\n".join(parts)


# ====== 主插件类 ======
@register_plugin
class SteamStatusPlugin(BasePlugin):
    plugin_name: str = "steam_status_plugin"
    enable_plugin: bool = False
    dependencies: List[str] = []
    python_dependencies: List[str] = ["requests"]
    config_file_name: str = "config.toml"

    config_schema: dict = {
        "plugin": {
            "name": ConfigField(type=str, default="steam_status_plugin", description="插件名称"),
            "config_version": ConfigField(type=str, default="1.0.0", description="配置文件版本"),
            "enabled": ConfigField(type=bool, default=False, description="是否启用插件（改为true后生效）"),
        },
        "steam": {
            "api_key": ConfigField(type=str, default="", description="Steam Web API Key（https://steamcommunity.com/dev/apikey）"),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        return [
            (SteamCommand.get_command_info(), SteamCommand),
        ]