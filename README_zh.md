# Paperang P2 打印机 - Home Assistant 集成

通过 Home Assistant 控制和监控 Paperang P2 热敏打印机。支持通过 USB 或蓝牙连接，从设备页面交互式打印文本、图片、QR 码、取件码，以及实时打印机遥测数据。

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mdj2812&repository=paperang-hacs&category=integration)

## 功能

- 🔌 **USB 自动发现** — 插入 USB 后自动检测打印机
- 📡 **蓝牙** — 无线连接（自动扫描）
- 🎛️ **设备页面控制** — 交互式打印面板，含模式选择器、文本输入、参数滑杆、打印按钮
- 📊 **6 个遥测传感器** — 电池、状态、电压、温度、加热浓度和连接状态（诊断）；静态信息（型号、固件、板版本、序列号）显示在设备卡片上
- 🖨️ **7 个服务** — 打印文本、图片、QR 码、取件码、测试页、获取状态、进纸
- 📦 **单一设备** — 所有实体归入一个「Paperang P2 Printer」设备

## 安装

### 方式一：HACS（推荐）

1. 在 HACS 中添加自定义仓库：
   - HACS → Integrations → ⋮ → Custom repositories
   - 添加仓库地址：`https://github.com/mdj2812/paperang-hacs`
   - Category 选择 `Integration`
   - 安装 `Paperang P2 Printer`

### 方式二：手动安装

```bash
git clone https://github.com/mdj2812/paperang-hacs.git
cp -r paperang-hacs/custom_components/paperang /config/custom_components/paperang
```

安装后重启 Home Assistant。

## 设置

### USB 自动发现

将 Paperang P2 插入 USB。Home Assistant 会自动检测并弹出通知 — 点击确认即可完成设置。

### 蓝牙设置

**设置 → 设备与服务** — 打印机开机且在蓝牙范围内时，HA 会自动发现并弹出通知，点击确认即可添加。

### 手动设置

**设置 → 设备与服务 → 添加集成 → 搜索「Paperang P2 Printer」** — 选择 **USB** 或 **蓝牙**。

### YAML 导入

如果更喜欢通过 `configuration.yaml` 配置，添加：

```yaml
paperang:
```

重启后 HA 会自动将其导入为配置条目。

## 前提条件

**USB：** Paperang P2 打印机通过 USB 连接到 HA 主机。USB 设备需直通到 HA VM（如果在虚拟机中运行）。

**蓝牙：** HA 主机需配备蓝牙适配器。打印机需开机且在蓝牙范围内。支持 `Paperang` 和 `MiaoMiaoJi`（喵喵机）两种品牌名称的设备。

> 📦 需要 `paperang-p2-lib[qr,cjk]>=1.1.1`（HA 自动安装）。

## 设备控制

设备页面提供交互式打印面板：

| 实体 | 类型 | 说明 |
|------|------|------|
| Print Mode | 选择器 | text / image / qr / pickup_code |
| Print Content | 文本输入 | 输入文字、URL、QR 数据或取件码 |
| Font Size | 数字 (12–96) | 文本打印字体大小 |
| Heat Density | 数字 (0–100%) | 打印浓度 |
| QR Size | 数字 (100–576px) | QR 码尺寸 |
| Image Profile | 选择器 | portrait / landscape / document / high_contrast / light |
| Feed Lines | 数字 (10–500) | 进纸行数 |

| 按钮 | 动作 |
|------|------|
| Print | 读取当前所有设置并执行对应的打印操作 |
| Feed Paper | 按 Feed Lines 值进纸 |
| Test Print | 打印测试页 |

## 传感器

| 传感器 | 描述 | 单位 |
|--------|------|------|
| Battery | 电池电量 | % |
| Status | 打印机状态码 | — |
| Voltage | 电池电压 | mV |
| Temperature | 打印头温度 | °C |
| Heat Density | 当前加热浓度设置 | % |
| Connection | 连接状态（诊断） | — |

> ℹ️ 静态信息（型号、固件版本、板版本、序列号）显示在设备卡片上，不作为独立传感器。

## 服务

### paperang.print_text

打印文本内容。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| text | string | — | 要打印的文本 |
| font_size | number | 24 | 字体大小（12–96） |
| heat_density | number | 75 | 加热浓度（0–100） |

### paperang.print_image

打印图片（支持本地文件路径或远程 URL）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| image_url | string | — | 图片 URL 或本地文件路径 |
| profile | select | document | portrait / landscape / document / high_contrast / light |
| heat_density | number | 75 | 加热浓度（0–100） |

### paperang.print_qr

打印 QR 码。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| qr_content | string | — | QR 码内容 |
| qr_size | number | 500 | QR 码大小（100–576） |
| heat_density | number | 75 | 加热浓度（0–100） |

### paperang.print_pickup_code

打印大号取件码。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| pickup_code | string | — | 取件码，如 "19-4308" |

### paperang.print_test_page

打印内置测试页（无参数）。

### paperang.get_status

查询当前电池和状态，结果记录在 INFO 日志中。

### paperang.feed_paper

按指定行数进纸。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| lines | number | 100 | 进纸行数 |

## 自动化示例

### 快递到站自动打印取件码

```yaml
automation:
  - alias: "打印快递取件码"
    trigger:
      platform: state
      entity_id: sensor.package_arrived
    action:
      - service: paperang.print_pickup_code
        data:
          pickup_code: "{{ states('input_text.pickup_code') }}"
```

### 每日天气打印

```yaml
automation:
  - alias: "每日天气打印"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: paperang.print_text
        data:
          text: >
            今天天气：{{ states('weather.home') }}
            温度：{{ states('sensor.home_temperature') }}°C
          font_size: 18
          heat_density: 60
```

### 低电量告警

```yaml
automation:
  - alias: "低电量告警"
    trigger:
      - platform: numeric_state
        entity_id: sensor.paperang_p2_battery
        below: 20
    action:
      - service: paperang.print_text
        data:
          text: >
            ⚠️ 打印机电量过低！
            {{ states('sensor.paperang_p2_battery') }}%
          font_size: 24
```

### 打印机恢复在线时打印

```yaml
automation:
  - alias: "打印机恢复在线通知"
    trigger:
      - platform: state
        entity_id: sensor.paperang_p2_status
        from: "unavailable"
    action:
      - service: paperang.print_text
        data:
          text: "🟢 Paperang P2 已上线"
          font_size: 24
          heat_density: 50
```

## 许可证

MIT License — Copyright (c) 2026 Martin Ma
