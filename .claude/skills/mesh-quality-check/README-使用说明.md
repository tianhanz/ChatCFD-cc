# mesh-quality-check Skill 使用说明

> **版本**: v1.0
> **适用对象**: 使用 OpenFOAM 或 ANSYS Fluent 进行 CFD 仿真的工程师
> **安装位置**: `~/.claude/skills/mesh-quality-check/`

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
~/.claude/skills/mesh-quality-check/
├── SKILL.md                            # 主技能定义文件（Claude 读取此文件获取指令）
├── scripts/
│   ├── parse_checkmesh.py              # OpenFOAM checkMesh 日志解析器
│   ├── parse_fluent_mesh.py            # Fluent mesh quality 输出解析器
│   └── evaluate_quality.py             # 质量评估引擎 + 报告生成器
├── references/
│   └── quality_criteria.md             # 详细阈值参考（300+ 行，含各工况建议）
└── evals/                              # 测试用例（可用于验证 skill 正常工作）
    ├── evals.json
    ├── test_openfoam_good.log
    ├── test_openfoam_bad.log
    └── test_fluent_mixed.log
```

---

## 三、如何使用

### 方法 1：直接对话（最简单）

在 Claude Code 中直接输入自然语言，skill 会自动触发：

```
# 粘贴 checkMesh 输出
帮我看看这个 checkMesh 输出有没有问题：
<粘贴 checkMesh 日志>

# 指定日志文件路径
分析一下 /path/to/checkMesh.log 的网格质量

# 粘贴 Fluent 输出
这是 Fluent 的 mesh check 结果，帮我评估一下：
<粘贴 Fluent 输出>

# 指定湍流模型，获取针对性建议
我要用 k-omega SST 模型，帮我检查一下网格质量够不够

# 遇到收敛问题时
仿真跑不收敛，会不会是网格问题？帮我看看 checkMesh 日志
```

**自动触发关键词**：checkMesh、mesh quality、网格质量、non-orthogonality、skewness、aspect ratio、y+、negative volumes、正交质量、偏斜度 等。

### 方法 2：手动调用脚本（独立于 Claude）

脚本也可以在命令行中独立使用，不依赖 Claude：

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
| **Volume Ratio** | > 0.01 | 0.001–0.01 | < 0.001 | 相邻单元体积比（需 -allGeometry） |
| **Determinant** | > 0.1 | 0.001–0.1 | < 0.001 | 单元变形程度（需 -allGeometry） |
| **Face Weight** | > 0.2 | 0.05–0.2 | < 0.05 | 插值权重均衡性（需 -allGeometry） |

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
将整个 `~/.claude/skills/mesh-quality-check/` 目录复制到同事机器上的相同位置即可：

```bash
# 打包
tar -czf mesh-quality-check.tar.gz -C ~/.claude/skills mesh-quality-check

# 同事解压到对应位置
mkdir -p ~/.claude/skills
tar -xzf mesh-quality-check.tar.gz -C ~/.claude/skills/
```

### Q6: 我可以修改阈值吗？
可以。阈值定义在 `scripts/evaluate_quality.py` 文件的 `OF_CRITERIA`（OpenFOAM）和 `FL_CRITERIA`（Fluent）字典中，直接修改数值即可。例如你觉得非正交性的警告线应该从 65° 改为 60°：

```python
"non_orthogonality_max": {
    "pass": 60,    # 修改此处
    "warn": 80,
    ...
},
```

---

## 七、测试验证

Skill 附带了 3 个测试用例，可用于验证安装正确：

```bash
SKILL=~/.claude/skills/mesh-quality-check

# 测试 1：OpenFOAM 合格网格 → 应输出 PASS
python3 $SKILL/scripts/parse_checkmesh.py $SKILL/evals/test_openfoam_good.log > /tmp/p.json
python3 $SKILL/scripts/evaluate_quality.py /tmp/p.json --report | head -5

# 测试 2：OpenFOAM 问题网格 → 应输出 FAIL（负体积 + 高 AR）
python3 $SKILL/scripts/parse_checkmesh.py $SKILL/evals/test_openfoam_bad.log > /tmp/p.json
python3 $SKILL/scripts/evaluate_quality.py /tmp/p.json --report | head -5

# 测试 3：Fluent 混合质量网格 → 应输出 FAIL（正交质量 < 0.1）
python3 $SKILL/scripts/parse_fluent_mesh.py $SKILL/evals/test_fluent_mixed.log > /tmp/p.json
python3 $SKILL/scripts/evaluate_quality.py /tmp/p.json --report | head -5
```

预期输出分别包含 `✅ PASS`、`❌ FAIL` 和 `❌ FAIL`。
