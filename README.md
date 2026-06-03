# Fitness Advisor

基于 26 本专业教材的 AI 运动医学与营养学顾问。

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
  analysis.md / plan.md / exercise.md / supplement.md
  _shared/                         # 长度规则 / 安全声明 / 数据加载

scripts/                           # 工具脚本
  db_init.py                       # 初始化 SQLite 数据库
  db_migrate.py                    # 从 JSON 迁移数据到 SQLite
  db_query.py                      # 趋势/训练/力量查询
  import_apple_health.py           # Apple Health XML 导入
  import_csv_workout.py            # 训记/Strong/Hevy CSV 导入
  merge_gi_data.py                 # GI 数据匹配合并

assets/
  food-database.json               # 1657 种食物 (32 营养字段 + GI)
  exercise-library.json            # 45 个标准动作
  body-reference.json              # 人群体测参考标准
  user-data/                       # 用户数据 (SQLite + JSON 备份)

templates/                         # 输出模板
.claude/commands/                  # 斜杠命令注册 (16 个)
```

## 安装

```bash
git clone https://github.com/arth1999/fitness-advisor-skill.git
cp -r fitness-advisor-skill ~/.claude/skills/fitness-advisor
```

首次使用时初始化数据库：

```bash
python scripts/db_init.py
```

如有旧 JSON 数据，迁移到 SQLite：

```bash
python scripts/db_migrate.py
```

## 工具与方法论

本项目的构建使用了以下开源工具和方法论。所有第三方成果均已标注出处。

| 工具/方法 | 用途 | 来源 |
|-----------|------|------|
| [book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 教材知识提取方法论：提取命名框架、心智模型、决策模式，按章组织，按需加载 | virgiliojr94 |
| [MinerU](https://github.com/opendatalab/MinerU) | PDF 文档 OCR 与结构化提取，将扫描教材转为 Markdown | OpenDataLab, 上海 AI 实验室 |
| [Sanotsu/china-food-composition-data](https://github.com/Sanotsu/china-food-composition-data) | 《中国食物成分表》第6版 OCR 提取，使用 Qwen2.5-VL-72B 视觉模型 | Sanotsu |
| [Sanotsu/fetch-glycemic-index](https://github.com/Sanotsu/fetch-glycemic-index) | 血糖生成指数 (GI) 系统综述数据 | Sanotsu |
| [Qwen2.5-VL-72B](https://github.com/QwenLM/Qwen2.5-VL) | 食物成分表 OCR 视觉语言模型 | Alibaba Cloud / Tongyi Lab |
| [cc-connect](https://github.com/chenhg5/cc-connect) | Claude Code 到微信等多平台的消息桥接 | chenhg5 |
| [Claude Code](https://claude.com/claude-code) | AI 编程助手，技能运行平台 | Anthropic |
| [pypdf](https://github.com/py-pdf/pypdf) | PDF 拆分工具（教材按章分割） | py-pdf |
| [wger-project/wger](https://github.com/wger-project/wger) | 健身数据模型参考（训练周期、身体测量 schema） | wger |
| [Apple HealthKit](https://developer.apple.com/documentation/healthkit) | 健康数据导出格式 (export.xml)，Apple Health 导入脚本参考 | Apple Inc. |

### 健康参考标准

身体数据分析中使用的标准切点来自以下指南和研究：

| 标准 | 来源 |
|------|------|
| BMI 切点（亚洲） | WHO 西太平洋地区标准 + 中国肥胖问题工作组 (COTF) |
| 体脂率（亚洲调整） | ACSM 体脂率分类; Gallagher 2000 (Am J Clin Nutr) 亚裔数据 |
| 腰围风险阈值 | 中国 COTF + IDF 东亚标准 |
| 腰臀比 / 腰高比 | WHO; Browning 2010; 中国心血管病风险评估 |
| 血压分级 | 中国高血压防治指南 2018 |
| 血脂参考 | 中国成人血脂异常防治指南 2016 |
| 血糖参考 | 中国 2 型糖尿病防治指南 2020 |
| 最大心率公式 | ACSM; Tanaka (2001); Gellish (2007) |
| 基础代谢率 | Mifflin-St Jeor 方程 (1990) |
| 握力参考 | 中国国民体质测定标准 2023; Dodds 2014 |
| 微量营养素参考 | 中国居民膳食营养素参考摄入量 (DRIs) 2013; Endocrine Society |
| 宏量素分配范围 | 中国居民膳食指南 2022 |

## 数据来源

### 教材知识库

知识库编译自以下教材，采用 book-to-skill 方法论提取结构与决策规则。

**运动生理学**

| 教材 | 作者 | 版次 | 出版社 | 年份 |
|------|------|------|--------|------|
| 运动生理学 | 邓树勋、王健、乔德才、郝选明 | 第3版 | 高等教育出版社 | 2015 |
| Advanced Nutrition and Human Metabolism | Sareen S. Gropper, Jack L. Smith, Timothy P. Carr | 8th | Cengage Learning | 2018 |

**解剖与肌动学**

| 教材 | 作者 | 版次 | 出版社 | 年份 |
|------|------|------|--------|------|
| 运动解剖学 | 李世昌 | 第3版 | 高等教育出版社 | 2015 |
| 基础肌动学 (Essentials of Kinesiology) | Paul J. Mansfield, Donald A. Neumann | 第4版 | Elsevier | 2019 |
| 解剖列车 (Anatomy Trains) | Thomas W. Myers | 第3版 | 北京科学技术出版社 | 2016 |

**训练与运动处方**

| 教材 | 作者 | 版次 | 出版社 | 年份 |
|------|------|------|--------|------|
| NSCA Essentials of Strength Training and Conditioning | G. Gregory Haff, N. Travis Triplett (eds.) | 5th | Human Kinetics | 2023 |
| NASM Essentials of Personal Fitness Training | Brian G. Sutton (ed.), NASM | 7th | Jones & Bartlett | 2022 |
| ACE Personal Trainer Manual | Todd Galati et al., ACE | 5th | American Council on Exercise | 2014 |
| ACSM运动测试与运动处方指南 (ACSM's Guidelines for Exercise Testing and Prescription) | Gary Liguori (ed.), ACSM; 王正珍 主译 | 第11版 | 北京体育大学出版社 | 2026 |
| 体能训练 | 曹景伟 主编, 中国体育科学学会 组编 | — | 人民邮电出版社 | 2024 |

**运动营养学**

| 教材 | 作者 | 版次 | 出版社 | 年份 |
|------|------|------|--------|------|
| 中国居民膳食指南 | 中国营养学会 | 2022 | 人民卫生出版社 | 2022 |
| 中国营养科学全书 | 杨月欣、葛可佑 总主编 | 第2版 | 人民卫生出版社 | 2019 |
| ACSM运动营养学 (ACSM's Nutrition for Exercise Science) | Dan Benardot; 高炳宏 主译 | — | 科学出版社 | 2021 |
| NSCA运动营养指南 (NSCA's Guide to Sport and Exercise Nutrition) | Bill Campbell (ed.), NSCA | — | Human Kinetics / 人民邮电出版社 | 2019 |
| Sports Nutrition: A Handbook for Professionals | Christine Karpinski, Christine A. Rosenbloom (eds.) | 6th | Academy of Nutrition and Dietetics | 2017 |
| 高级运动营养学 (Advanced Sports Nutrition) | Dan Benardot | 第2版 | 北京科学技术出版社 | 2019 |
| 临床运动营养学 (Clinical Sports Nutrition) | Louise Burke, Vicki Deakin; 王启荣 主译 | 第4版 | 世界图书出版西安有限公司 | 2011 |
| 营养学: 概念与争论 (Nutrition: Concepts and Controversies) | Frances S. Sizer, Eleanor N. Whitney; 陈伟 主译 | 第15版 | 清华大学出版社 | 2024 |

**运动补剂**

| 来源 | 说明 | 年份 |
|------|------|------|
| ISSN 立场声明 (8篇) | 涵盖肌酸、蛋白质、咖啡因、beta-丙氨酸、HMB、女性运动员等主题 | 2013–2021 |
| [Examine.com](https://examine.com) | 补剂证据等级交叉验证 | — |

**运动医学**

| 教材 | 作者 | 版次 | 出版社 | 年份 |
|------|------|------|--------|------|
| Brukner & Khan's Clinical Sports Medicine, Vol 1: Injuries | Peter Brukner, Ben Clarsen, Jill Cook, Ann Cools, Kay Crossley, Mark Hutchinson, Paul McCrory, Roald Bahr, Karim Khan | 5th | McGraw-Hill | 2017 |
| Brukner & Khan's Clinical Sports Medicine, Vol 2: The Medicine of Exercise | Peter Brukner, Karim Khan | 5th | McGraw-Hill | 2019 |
| 重返巅峰: 力量训练者伤后功能重建与能力发展 (Rebuilding Milo) | Aaron Horschig, Kevin Sonthana | — | — | — |

**纠正性训练与评估**

| 教材 | 作者 | 出版社 | 年份 |
|------|------|--------|------|
| 基于生物力学的纠正性训练 (The BioMechanics Method) | Justin Price; 王雄 译 | 人民邮电出版社 | 2019 |
| 功能性动作科学 (Functional Movement Systems) | Gray Cook, Jeremy Hall, Matt Cook; 张丹玥 译 | 人民邮电出版社 | 2024 |

**特殊人群**

| 教材 | 作者 | 版次 | 出版社 | 年份 |
|------|------|------|--------|------|
| NSCA's Essentials of Training Special Populations | Patrick L. Jacobs (ed.), NSCA | — | Human Kinetics | 2018 |

**执教与沟通**

| 教材 | 作者 | 出版社 | 年份 |
|------|------|--------|------|
| 执教的语言: 动作教学中的科学与艺术 (The Language of Coaching) | Nick Winkelman; 王雄、吴俊纬 译 | 人民邮电出版社 | 2022 |

### 营养数据库

- **食物成分**: 《中国食物成分表》标准版第6版 — 杨月欣 主编, 北京大学医学出版社, 2019。1657 种中国常见食材，每 100g 可食部含 32 个营养字段。
- **GI 值**: [Sanotsu/fetch-glycemic-index](https://github.com/Sanotsu/fetch-glycemic-index) — 基于 2021 年发表的 GI 系统综述数据，经模糊匹配合并至食物库。当前 489/1657 条食物含 GI 值。

### 动作库

45 个标准力量训练动作，编译自 NSCA CSCS 5th, NASM CPT 7th, ACE 5th, 基础肌动学 4th, 功能性动作科学。含目标肌群、关节运动、器械类型、难度分级、安全注意事项。

### 身体参考标准

| 指标 | 数据来源 | 标准 |
|------|---------|------|
| BMI 切点 | WHO 西太平洋标准 + 中国肥胖问题工作组 (COTF) | 正常 18.5–23.9, 超重 24–27.9, 肥胖 >=28 |
| 体脂率 | ACSM, 东亚人群调整 | 同 BMI 下较西方高约 2% |
| 腰围风险阈值 | 中国标准 | 男 >=85cm, 女 >=80cm |
| 血压分级 | 中国高血压防治指南 2018 | <120/80 正常 |
| 膳食结构 | 中国居民膳食宝塔 2022 | — |
| 训练参数 | ACSM, NSCA, NASM | %1RM 表, FITT-VP, 加重规则 |

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
