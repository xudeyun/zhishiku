# 知识库 ZhiShiKu

基于 RAG 的智能知识库，支持文件上传、对话问答、知识管理。数据持久化存储在 Supabase 云数据库，永不丢失。

## 功能

- 📊 三大模块：核算、税务、其他
- 📄 支持上传 PDF / Word / Excel / Markdown / TXT 文件
- 💬 AI 对话问答（DeepSeek），自动引用知识库内容并标注来源
- 🔍 语义模糊搜索
- 💡 对话输入知识点，可随时编辑、更新、删除
- 📑 引用标注来源文件和页码
- 💾 数据持久化存储在 Supabase 云数据库

## 方案（国内可用，几乎免费）

| 组件 | 服务 | 费用 |
|------|------|------|
| 应用托管 | Streamlit Cloud | 免费 |
| 数据库 | Supabase PostgreSQL + pgvector | 免费（500MB） |
| AI 问答 | DeepSeek（deepseek-chat） | 注册送余额，个人用每月几毛钱 |
| 向量搜索 | pgvector（内嵌于 Supabase） | 免费 |
| 嵌入模型 | paraphrase-multilingual-MiniLM-L12-v2 | 免费（本地运行） |
| 代码托管 | GitHub | 免费 |

## 部署步骤

### 1. 创建 Supabase 数据库
1. 打开 https://supabase.com 注册
2. **New Project**，设置名称和密码
3. 进入项目 → **SQL Editor** → 粘贴 `setup.sql` 内容 → **Run**
4. **Settings** → **Database** → **Connection string** → 选 **URI**，复制并替换 `[YOUR-PASSWORD]`

### 2. 获取 DeepSeek API Key
1. 打开 https://platform.deepseek.com 注册
2. 左侧 **API Keys** → **创建 API Key** → 复制

### 3. 推代码到 GitHub
用 GitHub Desktop（图形界面）或 Git 命令，将本目录推送到 GitHub 仓库 `zhishiku`。

### 4. 部署到 Streamlit Cloud
1. 打开 https://share.streamlit.io 用 GitHub 登录
2. **New app** → 选 `zhishiku` 仓库 → 主文件 `app.py`
3. **Advanced settings** → Secrets 填入：
```toml
DEEPSEEK_API_KEY = "你的DeepSeek key"
DATABASE_URL = "你的Supabase连接字符串"
```
4. 点击 **Deploy**

部署完成后获得链接：**https://zhishiku-xxxx.streamlit.app**

所有数据保存在 Supabase 云数据库中，应用重启也不会丢失。
