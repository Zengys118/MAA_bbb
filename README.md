# MAA 小助手扩展

这是识宝小助手的干净开发副本，保留任务、资源和自定义动作源码，运行日志、设备配置、缓存和打包运行时均不进入仓库。

## 目录

- `agent/`：自定义动作、识别和策略代码。
- `characters/`：可独立编辑的角色出招表和触点配置。
- `resource/base/`：MAA 任务识别资源。
- `tasks/`：任务与界面下拉选项。
- `tests/`：离线回归测试。
- `tools/`：本地开发运行工具。

## 开发

使用现有 MAA 安装目录提供的 Python/运行时执行测试：

```powershell
python -m unittest discover -s tests -q
```

MuMu 地址和其他本机配置请放在未跟踪的 `config/config.json` 中。提交前确认没有日志、截图、设备地址或账号信息。
