# 发布安装改成 OpenCentra自己的

## 背景

OpenCentra 是从 CoPaw 项目 fork 出来的项目，需要：
1. 发布到 PyPI， 包名为 `opencentra`
2. 用户可以从 OpenCentra 的 GitHub 安装
3. 保持与上游 CoPaw 的代码兼容,便于定期合并上游更新

4. 提交编译好的 `lib` 目录，避免 CI/CD 时 clone 和编译

5. 添加 `package.json` 解决版本引用问题

## 设计决策：最小改动 + 别名

为了**减少与上游合并时的冲突**， 采用以下策略：

| 改动 | 内容 | 合并冲突风险 |
|------|------|-------------|
| ✅ pyproject.toml | `name = "opencentra"` | 低（这个文件本来就要定制） |
| ✅ pyproject.toml | 加命令别名 `opencentra` | 低 |
| ❌ 源码目录 | 保持 `src/copaw/` 不变 | 无 |
| ❌ 内部 import | 保持 `from copaw.xxx` 不变 | 无 |
| ❌ 配置目录 | 保持 `~/.copaw/` 不变 | 无 |

**结果**：合并上游代码几乎无冲突，只需处理 `pyproject.toml` 和 `scripts/` 下的安装脚本。

## 修改的文件

### 1. pyproject.toml

```diff
 [project]
-name = "copaw"
+name = "opencentra"

 [project.scripts]
 copaw = "copaw.cli.main:cli"
+opencentra = "copaw.cli.main:cli"  # 别名，两个命令都能用
```

### 2. scripts/install.ps1
```diff
-$CopawRepo = "https://github.com/agentscope-ai/CoPaw.git"
+$CopawRepo = "https://github.com/opencentra/opencentra.git"

-    $package = "copaw"
-    if ($Version) { $package = "copaw==$Version" }
+    $package = "opencentra"
+    if ($Version) { $package = "opencentra==$Version" }
```

### 3. scripts/install.sh
```diff
-COPAW_REPO="https://github.com/agentscope-ai/CoPaw.git"
+COPAW_REPO="https://github.com/opencentra/opencentra.git"

-    PACKAGE="copaw"
-    if [ -n "$VERSION" ]; then
        PACKAGE="copaw==$VERSION"
-    fi
+    PACKAGE="opencentra"
+    if [ -n "$VERSION" ]; then
        PACKAGE="opencentra==$VERSION"
-    fi
```

### 4. scripts/install.bat
```diff
-set "COPAW_REPO=https://github.com/agentscope-ai/CoPaw.git"
+set "COPAW_REPO=https://github.com/opencentra/opencentra.git"

 :install_from_pypi
-set "_PACKAGE=copaw"
+set "_PACKAGE=opencentra"

-    set "_PACKAGE=copaw%ARG_VERSION%"
+    set "_PACKAGE=opencentra%ARG_VERSION%"
```

## 用户安装方式

### 方式一：一键安装（推荐）

**Windows PowerShell:**
```powershell
irm https://raw.githubusercontent.com/opencentra/opencentra/main/scripts/install.ps1 | iex
```

**Windows CMD:**
```cmd
curl -fsSL https://raw.githubusercontent.com/opencentra/opencentra/main/scripts/install.bat -o install.bat && install.bat
```

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/opencentra/opencentra/main/scripts/install.sh | bash
```

### 方式二: pip 安装
```bash
pip install opencentra
```

### 方式三: 从源码安装
```bash
git clone https://github.com/opencentra/opencentra.git
cd opencentra
pip install -e .
```

## 安装后使用

安装完成后,用户可以使用以下命令（两个都行）:

```bash
# 原命令(兼容)
copaw init
copaw app

# 新命令(别名)
opencentra init
opencentra app
```

## 发布到 PyPI 的步骤

### 1. 安装构建工具
```bash
pip install build twine
```

### 2. 构建
```bash
cd R:\crawelworkspace\py-Full-Market\ecommerce_tenant\opencentra
python -m build
```

### 3. 上传到 PyPI
```bash
# 先在 pypi.org 注册账号
twine upload dist/*
```

### 4. 测试安装
```bash
pip install opencentra
copaw --version
opencentra --version
```

## 合并上游 CoPaw 代码
```bash
# 添加上游仓库（如果还没添加)
git remote add upstream https://github.com/agentscope-ai/CoPaw.git

# 拉取上游更新
git fetch upstream

# 合并
git merge upstream/main

# 如果有冲突,主要会出现在:
- pyproject.toml（包名)
- scripts/install.*（仓库地址和包名)

# 解决冲突时保持 opencentra 的配置即可
```

## 关于提交 lib 和 package.json

为了解决 CI/CD 构建时的依赖问题，我们提交了：
- `console/packages/agentscope-spark-design/packages/spark-chat/lib/` (编译后的文件)
- `console/packages/agentscope-spark-design/packages/spark-chat/package.json` (版本引用需要)

## 修改日期

- 2026-03-15: 初始版本，完成包名和安装脚本修改
- 2026-03-15: 添加 lib 和 package.json 解决构建问题
