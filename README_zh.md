# Paperang P2 打印机 - Home Assistant 集成

通过 Home Assistant 控制 Paperang P2 热敏打印机，支持文本、图片、QR 码和取件码打印。

## 安装

### 方式一：HACS（推荐）

1. 在 HACS 中添加自定义仓库：
   - HACS → Integrations → ⋮ → Custom repositories
   - 添加仓库地址：`https://github.com/mdj2812/paperang-hacs.git`
   - Category 选择 `Integration`
   - 安装 `Paperang P2 Printer`

### 方式二：手动安装

1. 直接克隆到 HA 的 custom_components：
   ```bash
   git clone https://github.com/mdj2812/paperang-hacs.git /config/custom_components/paperang
   ```
2. 安装 pip 依赖：
   ```bash
   pip install paperang-p2-lib[qr,cjk]>=0.2.0
   ```
3. 重启 Home Assistant

## 前提条件

- Paperang P2 打印机通过 USB 连接到 HA 主机
- USB 设备已直通到 HA VM（如果在虚拟机中运行）

## 服务

### paperang.print_text

打印文本内容。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| text | string | - | 要打印的文本 |
| font_size | number | 24 | 字体大小（12-96） |
| heat_density | number | 75 | 加热浓度（0-100） |

### paperang.print_pickup_code

打印大号取件码（如快递柜取件码）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| pickup_code | string | - | 取件码，如 "19-4308" |

### paperang.print_qr

打印 QR 码。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| qr_content | string | - | QR 码内容 |
| qr_size | number | 500 | QR 码大小（100-576） |
| heat_density | number | 75 | 加热浓度（0-100） |

### paperang.print_image

打印图片。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| image_url | string | - | 图片 URL 或本地路径 |
| profile | select | document | 打印配置：portrait/landscape/document/high_contrast/light |
| heat_density | number | 75 | 加热浓度（0-100） |

## Automation 示例

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

### 门铃通知打印

```yaml
automation:
  - alias: "门铃通知打印"
    trigger:
      platform: state
      entity_id: binary_sensor.doorbell
      to: "on"
    action:
      - service: paperang.print_text
        data:
          text: "有人按门铃！"
          font_size: 32
          heat_density: 80
```

## 许可证

MIT License - Copyright (c) 2026 Martin Ma
