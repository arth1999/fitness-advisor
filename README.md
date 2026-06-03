# Fitness Advisor

基于 26 本专业教材的 AI 运动医学与营养学顾问。支持 Claude Code 终端和微信 Bot 两种使用方式。

## 功能模块

| 命令 | 功能 | 变体 |
|------|------|------|
| `/food` | 饮食营养建议 | `-simple` (100字) / 默认 / `-detail` |
| `/training` | 训练计划与安排 | `-simple` / 默认 / `-detail` |
| `/exercise` | 动作技术解析 | `-simple` / 默认 |
| `/supplement` | 补剂证据评估 | `-simple` / 默认 / `-detail` |
| `/analysis` | 身体与训练数据分析 | `-simple` / 默认 |
| `/plan` | 长期训练方案设计 | 默认 / `-detail` |
| `/log` | 记录身体数据/训练记录 | — |

短命令返回核心结论，detail 命令展开原理并引用教材来源。

## 知识库

采用 [book-to-skill](https://github.com/virgiliojr94/book-to-skill) 方法论构建：从原文提取命名框架、心智模型、决策模式，按章组织，按需加载。

### 覆盖教材

| 领域 | 数量 | 代表教材 |
|------|------|---------|
| 运动生理学 | 2 | 运动生理学 (邓树勋), Advanced Nutrition & Metabolism |
| 解剖与肌动学 | 3 | 运动解剖学, 基础肌动学, 解剖列车 (Myers) |
| 训练与运动处方 | 5 | NSCA CSCS, NASM CPT, ACE IFT, ACSM运动处方指南, 体能训练 |
| 运动营养学 | 8 | 中国居民膳食指南2022, ACSM运动营养学, 高级运动营养学 (Benardot) 等 |
| 运动补剂 | 1 | 8 篇 ISSN 立场声明 |
| 运动医学 | 2 | Brukner & Khan 临床运动医学 v1 + v2 |
| 康复与纠正性训练 | 3 | 重返巅峰, 纠正性训练, 功能性动作科学 (FMS/SFMA) |
| 特殊人群 | 1 | NSCA Essentials of Training Special Populations (40+ 疾病) |
| 执教沟通 | 1 | 执教的语言 |

### 架构

```
references_book_to_skill/          # 26 本教材 (455 文件, 2.5 MB)
  index.md                         # 总路由索引
  <book-slug>/
    SKILL.md                       # 核心框架 + 章节索引
    chapters/                      # 按章按需加载
    glossary.md                    # 术语表
    patterns.md                    # 决策模式
    cheatsheet.md                  # 快速参考

commands/                          # 7 个命令模块
  food.md / training.md / log.md
  analysis.md / plan.md
  exercise.md / supplement.md
  _shared/                         # 共享规则（长度/安全/数据加载）

assets/
  food-database.json               # 1657 种中国常见食物 (32 字段 + GI)
  exercise-library.json            # 45 个标准动作
  body-reference.json              # 东亚人群体测参考值

templates/                         # 输出模板
```

## 安装

### 终端使用

```bash
git clone https://github.com/arth1999/fitness-advisor.git
cp -r fitness-advisor ~/.claude/skills/fitness-advisor
```

在 Claude Code 终端中用 `/food`、`/training` 等命令触发，或自然语言提问自动路由。

### 微信 Bot (cc-connect)

1. 安装 cc-connect:
```bash
npm install -g cc-connect@beta
```

2. 绑定微信:
```bash
cc-connect weixin setup
```

3. 编辑 `~/.cc-connect/config.toml`:
```toml
[[projects]]
name = "fitness-advisor"
path = "/path/to/fitness-advisor"

[projects.agent]
type = "claudecode"

[projects.agent.options]
mode = "default"

[[projects.platforms]]
type = "weixin"
[projects.platforms.options]
token = "你的bot_token"
base_url = "https://ilinkai.weixin.qq.com"
account_id = "你的account_id"

# 注册命令
[[commands]]
name = "food"
prompt = "读 commands/food.md，按 default 模式回答：{{1}}"
# ... 其余命令同上
```

4. 启动:
```bash
cc-connect
```

## 数据来源

### 教材知识库

知识库编译自以下 26 本教材，采用 book-to-skill 方法论提取结构与决策规则：

**运动生理学**
- 运动生理学 第3版 — 邓树勋、王健、乔德才, 高等教育出版社, 2015
- Advanced Nutrition and Metabolism 8th Edition — Sareen Gropper, Jack Smith, Timothy Carr, Cengage, 2022

**解剖与肌动学**
- 运动解剖学 第3版 — 李世昌, 高等教育出版社, 2015
- 基础肌动学 第4版 — Paul Mansfield, Donald Neumann, Elsevier, 2021
- 解剖列车 第3版 — Thomas Myers, 北京科学技术出版社, 2016

**训练与运动处方**
- NSCA Essentials of Strength Training and Conditioning 5th Edition — G. Gregory Haff, N. Travis Triplett, Human Kinetics, 2024
- NASM Essentials of Personal Fitness Training 7th Edition — NASM, Jones & Bartlett, 2021
- ACE Personal Trainer Manual 5th Edition — ACE, 2014
- ACSM Guidelines for Exercise Testing and Prescription 11th Edition — ACSM, Wolters Kluwer, 2021
- 体能训练 — 杨世勇, 高等教育出版社, 2013

**运动营养学**
- 中国居民膳食指南 2022 — 中国营养学会, 人民卫生出版社, 2022
- 中国营养科学全书 第2版 — 中国营养学会, 人民卫生出版社, 2020
- ACSM运动营养学 — ACSM, 2021
- NSCA运动营养指南 — Bill Campbell, 2020
- Sports Nutrition Handbook 6th Edition — Nancy Clark, Human Kinetics, 2020
- 高级运动营养学 第2版 — Dan Benardot, Human Kinetics, 2020
- 临床运动营养学 — Louise Burke, 2020
- 营养学概念与争论 15th Edition — Frances Sizer, Eleanor Whitney, Cengage, 2020

**运动补剂**
- ISSN 立场声明 (8篇) — 涵盖肌酸、蛋白质、咖啡因、beta-丙氨酸、HMB、女性运动员等, 2017-2022
- 补剂数据交叉验证: [Examine.com](https://examine.com) 证据等级数据库

**运动医学**
- Brukner & Khan Clinical Sports Medicine 5th Edition (Vol 1) — Peter Brukner, Karim Khan, McGraw-Hill, 2017
- Brukner & Khan Clinical Sports Medicine 5th Edition (Vol 2) — Peter Brukner, Karim Khan, McGraw-Hill, 2019
- 重返巅峰: 运动康复训练 — 陈方灿, 北京体育大学出版社, 2018

**纠正性训练与评估**
- 基于生物力学的纠正性训练 — Justin Price, 2020
- 功能性动作科学: FMS与SFMA评估体系 — Gray Cook, Lee Burton, 2019

**特殊人群**
- NSCA Essentials of Training Special Populations — NSCA, Human Kinetics, 2018

**执教与沟通**
- 执教的语言: 动作教学的科学与艺术 — Nick Winkelman, 2021

### 营养数据库

- **食物成分**: 《中国食物成分表》标准版第6版 — 杨月欣主编, 北京大学医学出版社, 2019。1657 种中国常见食材，每 100g 可食部含 32 个营养字段。
- **GI 值**: [Sanotsu/fetch-glycemic-index](https://github.com/Sanotsu/fetch-glycemic-index) — 基于 2021 年发表的 GI 系统综述数据，经模糊匹配合并至食物库，当前 489/1657 条食物含 GI 值。

### 动作库

- 45 个标准力量训练动作，编译自: NSCA CSCS 5th, NASM CPT 7th, ACE IFT, 基础肌动学 4th, 功能性动作科学。含目标肌群、关节运动、器械类型、难度分级、安全注意事项。

### 身体参考标准

- **BMI 切点**: WHO 西太平洋标准 + 中国肥胖问题工作组 (COTF) 标准
- **体脂率**: 东亚人群调整值 (同 BMI 下较西方高约 2%)
- **腰围风险阈值**: 中国标准 (男 >=85cm, 女 >=80cm)
- **血压分级**: 中国高血压防治指南 2018
- **膳食结构**: 中国居民膳食宝塔 2022
- **训练参考值**: ACSM, NSCA, NASM 训练参数表

## 项目统计

```
教材总数:     26 本
知识库文件:   455 个
知识库大小:   2.5 MB
命令模块:     7 个 (16 个变体)
食物数据:     1,657 条
动作数据:     45 条
```

## 声明

本知识库提供运动科学和营养学教育信息，不构成医疗诊断或治疗建议。如有伤病或健康问题，请咨询执业医师。

## License

MIT
