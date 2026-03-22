# ChatCFD-cc: CFD Automation Agent (Community Fork)

> **Fork from:** [ConMoo/ChatCFD](https://github.com/ConMoo/ChatCFD)  
> **Original Paper:** [ChatCFD: An LLM-Driven Agent for End-to-End CFD Automation](https://arxiv.org/abs/2506.02019v2)

This is a community-maintained fork of ChatCFD with customizations and improvements.

---

## 🆕 Fork Highlights

### Modifications from Original
- ✅ Configured for GPUGeek API (DeepSeek V3/R1)
- ✅ Custom deployment scripts
- ✅ Enhanced environment variable management
- ✅ Additional documentation

### Claude Code Skills (`.claude/skills/`)

| Skill | Description |
|-------|-------------|
| `mesh-quality-check` | CFD mesh quality checker for OpenFOAM (`checkMesh`) and Fluent. Parses logs, evaluates metrics (non-orthogonality, skewness, aspect ratio, y+, etc.) against standard thresholds, generates PASS/WARNING/FAIL reports with remediation guidance. See [detailed usage guide](https://github.com/your-org/ChatCFD-cc/blob/main/.claude/skills/mesh-quality-check/README-使用说明.md). |
| `wrap-up` | Branch finalization — discovers and updates docs, commits, merges to main, and optionally pushes. |

### Installation

Quick start with pre-configured environment:

```bash
cd ~/ChatCFD-cc
source chatcfd_venv/bin/activate
source /usr/lib/openfoam/openfoam2406/etc/bashrc
streamlit run src/chatbot.py --server.port=8501
```

Or use the startup script:
```bash
./start_chatcfd.sh
```

---

## 📚 Original Documentation

For complete documentation, see [ReadMe.md](ReadMe.md).

---

## 🔧 Configuration

API keys are managed via environment variables:
- `~/.chatcfd_env` - DeepSeek API configuration
- `inputs/chatcfd_config.json` - Main configuration file

---

## 📝 License

Same as original project. See [LICENSE.txt](LICENSE.txt).

---

## 🙏 Acknowledgments

Original project by ConMoo and contributors.
