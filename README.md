# Steam 在线状态插件（steam_status_plugin）v1.0.0

一个基于 MaiBot 框架开发的 **Steam 在线状态与别名管理插件**。  
支持通过命令快速查询 Steam 用户在线状态、当前游戏，并允许在群内绑定和管理昵称映射。

![example](https://github.com/jinjidechefeng/maibot_steam_status/blob/main/example.png)

---

## 功能特性

- 查询在线状态  
  `/steam status <别名|steamid|vanity>`  
  获取玩家在线、离线、游戏中等状态。

- 绑定别名  
  `/steam link <别名> <steamid|vanity>`  
  将某个 Steam 用户绑定到群内自定义昵称。

- 解除绑定  
  `/steam unlink <别名>`  
  移除群内绑定。

- 查看绑定列表  
  `/steam list`  
  列出当前群的所有 Steam 绑定信息。

- 用户信息查询  
  `/steam whois <别名>`  
  查看绑定的 Steam 用户详细信息。

- 帮助命令  
  `/steam help`  
  查看插件命令说明与配置提示。

---

## 安装步骤

1. 将`steam_status_plugin`放入 MaiBot 主目录下的`plugin`文件夹
2. 确保目录结构如下：
   plugins/  
 ├── steam_status_plugin/  
 │ ├── plugin.py   
 │ └── _manifest.json

3. 启动 MaiBot，插件系统将自动检测并生成配置文件`config.toml`
4. 打开 `config.toml`，填写你的 Steam Web API Key：
```toml
[plugin]
enabled = true

[steam]
api_key = "你的SteamWebAPIKey"
```
5. 重启Maibot即可

---

## 获取 Steam Web API Key

1. 打开 [https://steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)
2. 登录你的 Steam 账号
3. 在 “Domain Name” 一栏中填写任意内容（如 `localhost`）
4. 点击 “Register” 按钮获取你的 API Key
5. 复制该 Key，并填入配置文件 `config.toml`：

```toml
[steam]
api_key = "你的SteamWebAPIKey"
```

## 使用示例
 | 命令                          | 说明                |
 | --------------------------- | ----------------- |
 | `/steam help`               | 查看帮助信息            |
 | `/steam link 麦麦 1145141919810` | 将 Steam 用户绑定为“麦麦” |
 | `/steam list`               | 显示本群绑定列表          |
 | `/steam status 麦麦`          | 查询“麦麦”当前在线状态      |
 | `/steam unlink 麦麦`          | 移除“麦麦”的绑定         |
 | `/steam whois 麦麦`           | 查看绑定的 Steam 用户详情  |

 支持 SteamID64、SteamID32（自动转换）、自定义 URL（Vanity URL）。

 ## 隐私与访问控制

 * 若用户资料未公开，Steam API 不会返回详细信息。
 * 插件会提示 “该用户资料未公开或部分未公开”。
 * 所有绑定数据仅存储于插件本地 `data.json` 文件，不会上传或外泄。

 ## 技术实现概览

 * 基于 `BasePlugin` + `BaseCommand` 架构。
 * 自动生成配置文件（Schema 由 `ConfigField` 定义）。
 * 使用 `requests` 调用 Steam Web API。
 * 多线程锁防止并发写入冲突。
 * 自动处理 SteamID32 → SteamID64 转换。
 * 支持群级别别名隔离。

 ## 开发者信息

 | 项目字段 | 内容                                                                                                             |
 | ---- | -------------------------------------------------------------------------------------------------------------- |
 | 插件名称 | steam_status_plugin                                                                                            |
 | 作者   | chefeng                                                                                                        |
 | 仓库   | [https://github.com/jinjidechefeng/maibot_steam_status](https://github.com/jinjidechefeng/maibot_steam_status) |
 | 许可证  | GPL-3.0                                                                                                        |
 | 兼容版本 | MaiBot 0.10.0 及以上                                                                                              |


 ## 致谢

 特别感谢 **Mai-with-u 团队**
 提供了开放且优雅的插件框架，让开发 Steam 工具类插件成为可能。
