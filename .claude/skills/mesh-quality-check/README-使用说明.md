# mesh-quality-check Skill 使用说明

> **版本**: v2.0（经 Gemini / GPT 交叉审核后修订）
> **适用对象**: 使用 OpenFOAM 或 ANSYS Fluent 进行 CFD 仿真的工程师
> **安装位置**: `~/.claude/skills/mesh-quality-check/` 或项目内 `.claude/skills/mesh-quality-check/`
> **环境要求**: Python 3.6+（无第三方依赖），可选 OpenFOAM 环境

---

## 零、什么是 Claude Code？什么是 Skill？

> 如果你已经熟悉 Claude Code，可以跳过本节。

### Claude Code 是什么

[Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) 是 Anthropic 出品的**终端 AI 编程助手**。简单来说：

- 你在终端里输入 `claude`，打开一个对话窗口
- 你用自然语言告诉它要做什么（中文/英文都行）
- 它可以帮你读文件、写代码、运行命令、分析结果
- 它能看到你当前目录下的文件，并且可以调用各种工具

类比：如果 ChatGPT 是一个网页聊天助手，Claude Code 就是一个**住在你终端里的编程搭档**，它可以直接操作你的文件系统。

### 如何安装 Claude Code

```bash
# 方法 1：npm 安装（推荐）
npm install -g @anthropic-ai/claude-code

# 方法 2：如果没有 npm，用 brew（Mac）
brew install claude-code

# 安装后，在终端输入以下命令启动：
claude
```

首次运行时需要登录 Anthropic 账号。登录后即可在终端中与 Claude 对话。

### Skill 是什么

Skill（技能）是给 Claude Code 的**预制指令包**。你可以把它理解为：

- **没有 Skill 时**：你每次都要告诉 Claude "用什么阈值判断网格质量、怎么解析 checkMesh、报告格式是什么..."——很麻烦，而且每次说的可能不一样
- **有了 Skill 后**：Claude 自动读取 Skill 文件里的指令，知道该怎么做。你只需要说 "帮我查一下网格质量"，它就会按照标准流程执行

Skill 本质上是一组放在 `.claude/skills/` 目录下的文件（Markdown 指令 + Python 脚本 + 参考资料），Claude Code 启动时会自动发现并加载它们。

### Skill 的两种安装位置

| 位置 | 路径 | 作用域 | 适用场景 |
|------|------|--------|---------|
| **用户级** | `~/.claude/skills/mesh-quality-check/` | 你所有项目都能用 | 个人工作站 |
| **项目级** | `<项目>/.claude/skills/mesh-quality-check/` | 仅本项目可用 | 团队共享，随 git 同步 |

本仓库已将 skill 放在项目级目录下 (`.claude/skills/mesh-quality-check/`)，clone 本仓库后直接可用。如果你想在其他项目里也用，把目录复制到 `~/.claude/skills/` 即可。

---

## 一、这个 Skill 是做什么的？

`mesh-quality-check` 是一个 Claude Code skill，用于**自动化检查 CFD 网格质量**。它可以：

1. **解析** OpenFOAM `checkMesh` 日志 或 Fluent mesh check 输出
2. **评估** 各项网格质量指标是否达标（PASS / WARNING / FAIL）
3. **生成** 结构化的网格质量报告，包含具体数值、阈值对比和修复建议
4. **给出** 针对不同湍流模型的 y+ 近壁网格建议

支持的求解器：
- **OpenFOAM**（解析 `checkMesh` / `checkMesh -allGeometry -allTopology` 输出）
- **ANSYS Fluent**（解析 `Mesh → Check` / `Quality → Examine Mesh` 输出）

---

## 二、文件结构

```
.claude/skills/mesh-quality-check/
├── SKILL.md                            # 主技能定义文件（Claude 读取此文件获取指令）
├── README-使用说明.md                   # 本文件（人类阅读的使用说明）
├── scripts/
│   ├── parse_checkmesh.py              # OpenFOAM checkMesh 日志解析器
│   ├── parse_fluent_mesh.py            # Fluent mesh quality 输出解析器
│   └── evaluate_quality.py             # 质量评估引擎 + 报告生成器
├── references/
│   └── quality_criteria.md             # 详细阈值参考（300+ 行，含各工况建议）
└── evals/                              # 测试用例（可用于验证 skill 正常工作）
    ├── evals.json                      # 测试定义（3 个用例）
    ├── test_openfoam_good.log          # 合格网格样本
    ├── test_openfoam_bad.log           # 问题网格样本（负体积 + 高 AR）
    └── test_fluent_mixed.log           # Fluent 混合质量样本
```

**文件之间的关系**（数据流）：

```
checkMesh 日志 ──→ parse_checkmesh.py ──→ JSON ──→ evaluate_quality.py ──→ 报告
Fluent 输出   ──→ parse_fluent_mesh.py ──→ JSON ──→ evaluate_quality.py ──→ 报告
```

每个脚本功能单一：解析器只负责把日志变成 JSON，评估器只负责拿 JSON 跟阈值比较出报告。这样如果你的日志格式有变化，只需改解析器；如果你想调整阈值标准，只需改评估器。

---

## 三、如何使用

### 方法 1：在 Claude Code 里直接对话（最简单，推荐新手）

> **前提**：你已安装 Claude Code（见第零节），并且在项目目录或 `~/.claude/skills/` 下有本 skill。

**操作步骤**：

```
1. 打开终端
2. cd 到你的 OpenFOAM case 目录或项目目录
3. 输入 claude 启动 Claude Code
4. 直接用自然语言提问
```

**对话示例**（可直接复制粘贴）：

```
# 示例 1：粘贴 checkMesh 输出
帮我看看这个 checkMesh 输出有没有问题：
<粘贴 checkMesh 日志>

# 示例 2：指定日志文件路径
分析一下 /path/to/checkMesh.log 的网格质量

# 示例 3：粘贴 Fluent 输出
这是 Fluent 的 mesh check 结果，帮我评估一下：
<粘贴 Fluent 输出>

# 示例 4：指定湍流模型，获取针对性建议
我要用 k-omega SST 模型，帮我检查一下网格质量够不够

# 示例 5：遇到收敛问题时
仿真跑不收敛，会不会是网格问题？帮我看看 checkMesh 日志

# 示例 6：让 Claude 直接运行 checkMesh
帮我在 /home/user/cavity 目录跑一下 checkMesh 看看网格质量
```

**自动触发关键词**：checkMesh、mesh quality、网格质量、non-orthogonality、skewness、aspect ratio、y+、negative volumes、正交质量、偏斜度 等。只要你的提问包含这些词，Claude 就会自动调用本 skill。

### 方法 2：手动调用脚本（不需要 Claude Code）

三个 Python 脚本可以在命令行中独立使用，**完全不依赖 Claude**。适用于：
- 你还没安装 Claude Code
- 你想在 CI/CD 管道里自动化检查
- 你想集成到自己的脚本里

```bash
# ========== OpenFOAM 工作流 ==========

# 步骤 1：运行 checkMesh（如果还没有日志）
checkMesh -case /path/to/case > checkMesh.log 2>&1
# 或扩展检查：
checkMesh -case /path/to/case -allGeometry -allTopology > checkMesh.log 2>&1

# 步骤 2：解析日志为 JSON
python3 ~/.claude/skills/mesh-quality-check/scripts/parse_checkmesh.py checkMesh.log > parsed.json

# 步骤 3a：输出评估 JSON（程序化使用）
python3 ~/.claude/skills/mesh-quality-check/scripts/evaluate_quality.py parsed.json

# 步骤 3b：输出 Markdown 格式报告（人类阅读）
python3 ~/.claude/skills/mesh-quality-check/scripts/evaluate_quality.py parsed.json --report

# 也支持管道操作（一行完成）
python3 ~/.claude/skills/mesh-quality-check/scripts/parse_checkmesh.py checkMesh.log \
  > /tmp/parsed.json && \
  python3 ~/.claude/skills/mesh-quality-check/scripts/evaluate_quality.py /tmp/parsed.json --report


# ========== Fluent 工作流 ==========

# 将 Fluent 的 Mesh Check 输出保存为文本文件，然后：
python3 ~/.claude/skills/mesh-quality-check/scripts/parse_fluent_mesh.py fluent_check.log > parsed.json
python3 ~/.claude/skills/mesh-quality-check/scripts/evaluate_quality.py parsed.json --report
```

---

## 四、网格质量评判标准

### 4.1 OpenFOAM 指标阈值

| 指标 | PASS（达标） | WARNING（警告） | FAIL（不达标） | 说明 |
|------|------------|----------------|--------------|------|
| **Non-orthogonality (max)** | < 65° | 65°–80° | > 80° | 面法向量与单元中心连线夹角 |
| **Non-orthogonality (avg)** | < 15° | 15°–30° | > 30° | 全场平均值 |
| **Skewness** | < 4.0 | 4.0–8.0 | > 8.0 | 面插值点偏离面中心的程度 |
| **Aspect Ratio** | < 100 | 100–1000 | > 1000 | 单元最长/最短边比 |
| **Min Volume** | > 0 | — | ≤ 0 | 负体积 = 倒置单元，必须修复 |
| **Volume Ratio** | > 0.1 | 0.01–0.1 | < 0.01 | 相邻单元体积比（需 -allGeometry） |
| **Determinant** | > 0.1 | 0.001–0.1 | < 0.001 | 单元变形程度（需 -allGeometry） |
| **Interpolation Weight** | > 0.2 | 0.05–0.2 | < 0.05 | 插值权重均衡性（需 -allGeometry） |

### 4.2 Fluent 指标阈值

| 指标 | PASS（达标） | WARNING（警告） | FAIL（不达标） | 说明 |
|------|------------|----------------|--------------|------|
| **Orthogonal Quality (min)** | > 0.3 | 0.1–0.3 | < 0.1 | 0-1，越高越好 |
| **Skewness (max)** | < 0.85 | 0.85–0.95 | > 0.95 | 0-1，越低越好 |
| **Aspect Ratio (max)** | < 20 | 20–100 | > 100 | 同 OpenFOAM 定义 |
| **Volume Change** | < 5 | 5–10 | > 10 | 相邻单元体积比 |
| **Cell Squish** | < 0.5 | 0.5–0.8 | > 0.8 | 单元压缩程度 |

### 4.3 两套指标的对应关系

| OpenFOAM | Fluent | 换算公式 |
|----------|--------|---------|
| Non-orthogonality (角度) | Orthogonal Quality (0–1) | `OQ ≈ cos(非正交角)` |
| Skewness (0–∞) | Skewness (0–1) | 定义不同，不可直接换算 |
| Aspect Ratio | Aspect Ratio | 相似定义 |
| Volume Ratio | Volume Change | Fluent 用相邻最大比；OF 用 min/max |

**跨求解器注意事项**（v2.0 新增，来自 Gemini/GPT 审核）：

1. **非正交性 / 正交质量阈值不完全对齐**：OpenFOAM WARNING 阈值 65° 对应 `cos(65°) ≈ 0.42`，但 Fluent 的 PASS 阈值是 0.3。这意味着同一个 72° 非正交角的网格，在 OpenFOAM 中会被标为 WARNING，但在 Fluent 中仍然是 PASS。**建议同时用两个求解器时取更严格的标准。**

2. **Aspect Ratio 阈值差异**：OpenFOAM PASS < 100 vs Fluent PASS < 20。这是因为 OpenFOAM 阈值考虑了边界层高长宽比网格（在壁面附近是正常的），而 Fluent 阈值更保守，面向体积域。**评估 Fluent 边界层网格时，近壁高 AR 不一定是问题，需要结合位置判断。**

### 4.4 y+ 近壁网格要求

| 湍流模型 | 目标 y+ | 边界层层数 | 增长比 |
|---------|---------|-----------|--------|
| k-ε + 标准壁面函数 | 30–300 | ≥ 5 | 1.2 |
| k-ε + 增强壁面处理 | ≈ 1 | 15–20 | 1.2 |
| k-ω SST | ≈ 1 | 15–20 | 1.2 |
| Spalart-Allmaras | ≈ 1 | 15–20 | 1.2 |
| LES / DES | ≈ 1 | 20+ | 1.1–1.15 |

**首层网格高度估算**：`Δy₁ ≈ y⁺_target × L / (Re_L × √(C_f / 2))`，其中 `C_f ≈ 0.058 × Re_L^(-0.2)`

---

## 五、报告输出示例

### 示例 1：网格合格（OpenFOAM）

```
# Mesh Quality Report

## Summary
- Overall verdict: ✅ PASS
- Solver: OpenFOAM
- Total cells: 12,400
- Cell types: hexahedra: 11,200, prisms: 800, tetrahedra: 400

## Quality Metrics
| Metric                     | Value     | Status  | Pass | Warn |
|----------------------------|-----------|---------|------|------|
| Non-Orthogonality (max)    | 42.35 °   | ✅ PASS | 65   | 80   |
| Non-Orthogonality (avg)    | 8.765 °   | ✅ PASS | 15   | 30   |
| Skewness (max)             | 1.235     | ✅ PASS | 4.0  | 8.0  |
| Aspect Ratio (max)         | 8.45      | ✅ PASS | 100  | 1000 |

## Recommendations
All metrics within acceptable range. No action needed.
```

### 示例 2：网格有问题（OpenFOAM，含修复建议）

```
# Mesh Quality Report

## Summary
- Overall verdict: ❌ FAIL
- Failed checks: 2 (negative volumes, high aspect ratio)

## Quality Metrics
| Metric                     | Value     | Status      |
|----------------------------|-----------|-------------|
| Non-Orthogonality (max)    | 82.35 °   | ❌ FAIL     |
| Skewness (max)             | 6.789     | ⚠️ WARNING  |
| Aspect Ratio (max)         | 1523.45   | ❌ FAIL     |
| Negative Volumes           | 3 cells   | ❌ FAIL     |

## Recommendations
### ❌ Negative Volumes (FAIL)
Inverted cells detected — re-mesh the affected region...

### ❌ Aspect Ratio (FAIL)
Reduce boundary layer growth ratio...
```

---

## 六、常见问题

### Q1: 脚本需要安装什么依赖？
**不需要额外安装**。三个脚本只使用 Python 标准库（`re`, `json`, `sys`），Python 3.6+ 即可运行。

### Q2: checkMesh 的扩展参数 -allGeometry / -allTopology 有必要加吗？
建议加。默认 `checkMesh` 只检查基本指标（非正交性、偏斜度、长宽比、体积）。加上 `-allGeometry` 后还会输出体积比、行列式、面权重、面扭曲等更多指标，有助于更全面地评估网格。

### Q3: 有些指标是 WARNING 但不是 FAIL，需要修吗？
- **WARNING 指标**不会直接导致求解器崩溃，但可能影响精度和收敛速度
- 对于 RANS 稳态仿真，WARNING 通常可以接受
- 对于 LES/DES 等高精度仿真，WARNING 也建议修复

### Q4: Fluent 和 OpenFOAM 的阈值为什么不一样？
因为两个软件的指标定义不同。例如 OpenFOAM 的 "非正交性" 是角度（0°–90°，越低越好），而 Fluent 的 "正交质量" 是 0–1 的归一化值（越高越好）。Skill 的参考文档 `references/quality_criteria.md` 中有详细的对应关系和换算公式。

### Q5: 如何将这个 Skill 分享给同事？

**方法 A：通过 Git 仓库（推荐）**

本仓库已包含 skill，同事 clone 仓库后自动可用：

```bash
git clone <本仓库地址>
cd ChatCFD-cc
claude   # 启动 Claude Code，skill 自动加载
```

**方法 B：手动复制（用户级安装）**

将整个目录复制到同事机器上的 `~/.claude/skills/` 即可：

```bash
# 打包
tar -czf mesh-quality-check.tar.gz -C .claude/skills mesh-quality-check

# 同事解压到对应位置
mkdir -p ~/.claude/skills
tar -xzf mesh-quality-check.tar.gz -C ~/.claude/skills/
```

**方法 C：只用脚本（不需要 Claude Code）**

如果同事不想装 Claude Code，把 `scripts/` 目录单独给他们就行，三个 Python 脚本可以独立运行（见第三节方法 2）。

### Q6: 我可以修改阈值吗？
可以。阈值定义在 `scripts/evaluate_quality.py` 文件的 `OF_CRITERIA`（OpenFOAM）和 `FL_CRITERIA`（Fluent）字典中，直接修改数值即可。例如你觉得非正交性的警告线应该从 65° 改为 60°：

```python
"non_orthogonality_max": {
    "pass": 60,    # 修改此处
    "warn": 80,
    ...
},
```

修改后无需重启 Claude Code，下次触发 skill 时会自动使用新阈值。

### Q7: Claude Code 里 skill 没有触发怎么办？

检查以下几点：

1. **skill 文件位置是否正确**：确认 `SKILL.md` 存在于 `~/.claude/skills/mesh-quality-check/SKILL.md` 或 `<项目>/.claude/skills/mesh-quality-check/SKILL.md`
2. **Claude Code 版本**：skill 功能需要较新版本的 Claude Code，运行 `claude --version` 检查，建议更新到最新版
3. **提问方式**：确保你的提问中包含关键词（如 "checkMesh"、"mesh quality"、"网格质量" 等），这样 skill 才会被自动触发
4. **手动触发**：如果自动触发不灵，可以在 Claude Code 中显式说 "使用 mesh-quality-check skill 分析以下日志"

### Q8: v2.0 相比 v1.0 有什么改动？

v2.0 经过 Gemini-2.5-Pro 和 GPT-5.2 两个模型的交叉审核，主要改动：

| 改动 | 说明 |
|------|------|
| Volume Ratio 阈值收紧 | PASS 从 >0.01 改为 >0.1，WARNING 从 0.001-0.01 改为 0.01-0.1 |
| 重命名 Face Weight | 改为更准确的 "Interpolation Weight"（插值权重） |
| 新增 Fluent Volume Change 指标 | PASS <5, WARNING 5-10, FAIL >10 |
| 新增数据完整性提示 | 检测到缺少 -allGeometry 扩展指标时自动提醒 |
| 新增高 AR 单元位置提示 | 区分边界层高 AR（正常）和核心区高 AR（需修复） |
| 跨求解器阈值一致性说明 | 解释 OF 和 Fluent 阈值为何不完全对齐 |
| Fluent 解析大小写不敏感 | 适配不同 Fluent 版本的输出格式差异 |

---

## 七、测试验证

Skill 附带了 3 个测试用例，可用于验证安装正确：

```bash
# 如果是项目级安装
SKILL=.claude/skills/mesh-quality-check

# 如果是用户级安装
# SKILL=~/.claude/skills/mesh-quality-check

# 测试 1：OpenFOAM 合格网格 → 应输出 PASS
python3 $SKILL/scripts/parse_checkmesh.py $SKILL/evals/test_openfoam_good.log > /tmp/p.json
python3 $SKILL/scripts/evaluate_quality.py /tmp/p.json --report | head -5

# 测试 2：OpenFOAM 问题网格 → 应输出 FAIL（负体积 + 高 AR）
python3 $SKILL/scripts/parse_checkmesh.py $SKILL/evals/test_openfoam_bad.log > /tmp/p.json
python3 $SKILL/scripts/evaluate_quality.py /tmp/p.json --report | head -5

# 测试 3：Fluent 混合质量网格 → 应输出 FAIL（正交质量 < 0.1 + Volume Change）
python3 $SKILL/scripts/parse_fluent_mesh.py $SKILL/evals/test_fluent_mixed.log > /tmp/p.json
python3 $SKILL/scripts/evaluate_quality.py /tmp/p.json --report | head -5
```

预期输出分别包含 `✅ PASS`、`❌ FAIL` 和 `❌ FAIL`。

---

## 八、快速参考卡片

一页纸总结，可打印贴在工位旁：

```
╔═══════════════════════ CFD 网格质量速查 ═══════════════════════╗
║                                                                ║
║  OpenFOAM checkMesh              Fluent Mesh Check             ║
║  ─────────────────               ─────────────────             ║
║  Non-ortho max  < 65°   ✅       Ortho Quality   > 0.3   ✅   ║
║                 65-80°  ⚠️                        0.1-0.3 ⚠️   ║
║                 > 80°   ❌                        < 0.1   ❌   ║
║                                                                ║
║  Skewness       < 4.0   ✅       Skewness        < 0.85  ✅   ║
║                 4-8     ⚠️                        0.85-95 ⚠️   ║
║                 > 8.0   ❌                        > 0.95  ❌   ║
║                                                                ║
║  Aspect Ratio   < 100   ✅       Aspect Ratio    < 20    ✅   ║
║  Volume Ratio   > 0.1   ✅       Volume Change   < 5     ✅   ║
║  Negative Vol   = 0     ✅       Cell Squish     < 0.5   ✅   ║
║                                                                ║
║  y+ 目标: k-ε 壁面函数 30-300 | k-ω SST / SA / LES ≈ 1      ║
║                                                                ║
║  运行命令:                                                     ║
║  checkMesh -case <dir> -allGeometry -allTopology 2>&1          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```
