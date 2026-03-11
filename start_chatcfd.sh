#!/bin/bash
# ChatCFD 启动脚本 - 自动配置 API 密钥

cd ~/ChatCFD

# 激活虚拟环境
source chatcfd_venv/bin/activate

# 加载 OpenFOAM 环境
source /usr/lib/openfoam/openfoam2406/etc/bashrc 2>/dev/null

# 加载 API 密钥
if [ -f ~/.chatcfd_env ]; then
    source ~/.chatcfd_env
fi

# 更新配置文件（如果环境变量存在）
if [ ! -z "$DEEPSEEK_V3_KEY" ]; then
    python3 << EOF
import json

config_path = "inputs/chatcfd_config.json"
with open(config_path, 'r') as f:
    config = json.load(f)

# 从环境变量更新
import os
config["DEEPSEEK_V3_KEY"] = os.getenv("DEEPSEEK_V3_KEY", config["DEEPSEEK_V3_KEY"])
config["DEEPSEEK_V3_BASE_URL"] = os.getenv("DEEPSEEK_V3_BASE_URL", config["DEEPSEEK_V3_BASE_URL"])
config["DEEPSEEK_R1_KEY"] = os.getenv("DEEPSEEK_R1_KEY", config["DEEPSEEK_R1_KEY"])
config["DEEPSEEK_R1_BASE_URL"] = os.getenv("DEEPSEEK_R1_BASE_URL", config["DEEPSEEK_R1_BASE_URL"])

with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)

print("✅ 配置已从环境变量更新")
EOF
fi

# 启动 Web 界面
echo "🚀 启动 ChatCFD Web 界面..."
streamlit run run_chatcfd/chatcfd_web.py --server.port=8501
