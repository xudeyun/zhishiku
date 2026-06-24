import os
import json
import streamlit as st

# ── Page config ──
st.set_page_config(page_title="知识库 ZhiShiKu", page_icon="📚", layout="wide")

# ── API Keys ──
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", "") or os.environ.get("DEEPSEEK_API_KEY", "")
DATABASE_URL = st.secrets.get("DATABASE_URL", "") or os.environ.get("DATABASE_URL", "")

if not DEEPSEEK_API_KEY:
    st.error("⚠️ 请在 Settings > Secrets 中添加 `DEEPSEEK_API_KEY`，[获取](https://platform.deepseek.com)")
    st.stop()
if not DATABASE_URL:
    st.error("⚠️ 请在 Settings > Secrets 中添加 `DATABASE_URL`（Supabase 连接字符串）")
    st.stop()

os.environ["DATABASE_URL"] = DATABASE_URL

# ── Init ──
from kb import (
    MODULES,
    add_document, list_documents, delete_document,
    add_knowledge, list_knowledge, update_knowledge, delete_knowledge, get_knowledge,
    create_conversation, add_message, get_conversation_messages,
    list_conversations, delete_conversation, search,
)
from rag import rag_stream

# ── Session state ──
if "current_module" not in st.session_state:
    st.session_state.current_module = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

# ── Helper ──
def get_conv_id(module_id: str) -> str:
    if module_id not in st.session_state.conversation_id:
        st.session_state.conversation_id[module_id] = create_conversation(module_id)
    return st.session_state.conversation_id[module_id]

def get_history(module_id: str) -> list:
    if module_id not in st.session_state.chat_history:
        st.session_state.chat_history[module_id] = []
    return st.session_state.chat_history[module_id]

def get_module_by_id(mid: str) -> dict:
    for m in MODULES:
        if m["id"] == mid:
            return m
    return MODULES[0]


# ══════════════════════════════════════════
# HOMEPAGE
# ══════════════════════════════════════════
if st.session_state.current_module is None:
    st.markdown("""
    <div style='text-align:center; padding: 2rem 0 1rem;'>
        <h1 style='font-size:2.5rem; margin-bottom:0.25rem;'>📚 知识库</h1>
        <p style='color:#6b7280; font-size:1.1rem;'>选择模块开始管理知识、提问和搜索</p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(3)
    for i, mod in enumerate(MODULES):
        with cols[i]:
            doc_count = len(list_documents(mod["id"]))
            kn_count = len(list_knowledge(mod["id"]))
            if st.button(
                f"{mod['icon']}  {mod['name']}\n\n{doc_count} 个文件 · {kn_count} 条知识",
                key=f"mod_{mod['id']}",
                use_container_width=True,
            ):
                st.session_state.current_module = mod["id"]
                st.rerun()

    st.markdown("---")
    st.subheader("🔍 全局搜索")
    g_query = st.text_input("输入关键词搜索所有模块", key="global_search", placeholder="搜索...")
    if g_query:
        results = search(g_query, top_k=10)
        if results:
            for r in results:
                mod = get_module_by_id(r.get("module_id", ""))
                label = f"{'📄' if r['source_type']=='document' else '💡'} [{mod['name']}] {r.get('source_title', '未知')}"
                if r.get("page_number"):
                    label += f" · 第{r['page_number']}页"
                st.markdown(f"**{label}**")
                st.caption(r["content"][:200])
        else:
            st.info("未找到相关结果")


# ══════════════════════════════════════════
# MODULE VIEW
# ══════════════════════════════════════════
else:
    mod = get_module_by_id(st.session_state.current_module)
    module_id = mod["id"]

    # Header
    col_back, col_title, col_search = st.columns([1, 6, 3])
    with col_back:
        if st.button("← 返回", key="back"):
            st.session_state.current_module = None
            st.rerun()
    with col_title:
        st.markdown(f"## {mod['icon']} {mod['name']}")
    with col_search:
        s_query = st.text_input("🔍 搜索", key=f"search_{module_id}", placeholder="在本模块中搜索...")
        if s_query:
            results = search(s_query, module_id=module_id, top_k=8)
            if results:
                for r in results:
                    icon = "📄" if r["source_type"] == "document" else "💡"
                    extra = f" · 第{r['page_number']}页" if r.get("page_number") else ""
                    st.markdown(f"**{icon} {r.get('source_title','')}**{extra}")
                    st.caption(r["content"][:150])
            else:
                st.info("未找到相关结果")

    st.divider()

    # Layout: sidebar + chat
    sidebar, chat = st.columns([1, 2.5])

    # ── Sidebar ──
    with sidebar:
        tab_files, tab_kn, tab_conv = st.tabs(["📄 文件", "💡 知识", "💬 对话"])

        # Files tab
        with tab_files:
            uploaded = st.file_uploader(
                "上传文件", type=["pdf", "docx", "xlsx", "md", "txt"],
                key=f"upload_{module_id}",
            )
            if uploaded:
                file_bytes = uploaded.getbuffer()
                ext = uploaded.name.rsplit(".", 1)[-1].lower()
                try:
                    add_document(module_id, uploaded.name, ext, file_bytes)
                    st.success(f"✅ {uploaded.name} 已上传并处理完成")
                except Exception as e:
                    st.error(f"处理失败: {e}")
                st.rerun()

            docs = list_documents(module_id)
            for doc in docs:
                col1, col2 = st.columns([5, 1])
                with col1:
                    icon = {"pdf":"📄","docx":"📝","xlsx":"📊","md":"📋","txt":"📃"}.get(doc["file_type"], "📄")
                    status = "" if doc["status"] == "ready" else f" ({doc['status']})"
                    st.text(f"{icon} {doc['title']}{status}")
                with col2:
                    if st.button("🗑", key=f"del_doc_{doc['id']}"):
                        delete_document(doc["id"])
                        st.rerun()

        # Knowledge tab
        with tab_kn:
            with st.expander("➕ 添加知识"):
                kn_title = st.text_input("标题", key=f"kn_title_{module_id}")
                kn_content = st.text_area("内容", key=f"kn_content_{module_id}", height=120)
                kn_tags = st.text_input("标签（逗号分隔）", key=f"kn_tags_{module_id}")
                if st.button("保存知识", key=f"kn_save_{module_id}"):
                    if kn_title and kn_content:
                        add_knowledge(module_id, kn_title, kn_content, kn_tags)
                        st.success("✅ 已保存")
                        st.rerun()

            kn_list = list_knowledge(module_id)
            for kn in kn_list:
                with st.expander(f"💡 {kn['title']} (v{kn['version']})"):
                    st.markdown(kn["content"])
                    if kn.get("tags"):
                        st.caption(f"标签: {kn['tags']}")
                    col_edit, col_del = st.columns(2)
                    with col_edit:
                        if st.button("✏️ 编辑", key=f"edit_kn_{kn['id']}"):
                            st.session_state[f"editing_{kn['id']}"] = True
                            st.rerun()
                    with col_del:
                        if st.button("🗑 删除", key=f"del_kn_{kn['id']}"):
                            delete_knowledge(kn["id"])
                            st.rerun()

            # Edit form
            for kn in kn_list:
                if st.session_state.get(f"editing_{kn['id']}"):
                    st.markdown("---")
                    st.markdown(f"**编辑: {kn['title']}**")
                    new_title = st.text_input("标题", value=kn["title"], key=f"edit_t_{kn['id']}")
                    new_content = st.text_area("内容", value=kn["content"], key=f"edit_c_{kn['id']}", height=120)
                    new_tags = st.text_input("标签", value=kn.get("tags", ""), key=f"edit_tag_{kn['id']}")
                    col_s, col_c = st.columns(2)
                    with col_s:
                        if st.button("✅ 保存", key=f"save_edit_{kn['id']}"):
                            update_knowledge(kn["id"], title=new_title, content=new_content, tags=new_tags)
                            st.session_state[f"editing_{kn['id']}"] = False
                            st.success("已更新")
                            st.rerun()
                    with col_c:
                        if st.button("取消", key=f"cancel_edit_{kn['id']}"):
                            st.session_state[f"editing_{kn['id']}"] = False
                            st.rerun()

        # Conversations tab
        with tab_conv:
            if st.button("🆕 新对话", key=f"new_conv_{module_id}"):
                st.session_state.conversation_id[module_id] = create_conversation(module_id)
                st.session_state.chat_history[module_id] = []
                st.rerun()

            convs = list_conversations(module_id)
            for conv in convs:
                col1, col2 = st.columns([5, 1])
                with col1:
                    if st.button(conv["title"] or "新对话", key=f"conv_{conv['id']}"):
                        st.session_state.conversation_id[module_id] = conv["id"]
                        msgs = get_conversation_messages(conv["id"])
                        st.session_state.chat_history[module_id] = [
                            {"role": m["role"], "content": m["content"], "citations": json.loads(m["citations"]) if m.get("citations") else []}
                            for m in msgs
                        ]
                        st.rerun()
                with col2:
                    if st.button("🗑", key=f"del_conv_{conv['id']}"):
                        delete_conversation(conv["id"])
                        st.rerun()

    # ── Chat ──
    with chat:
        conv_id = get_conv_id(module_id)
        history = get_history(module_id)

        # Display history
        for msg in history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("citations"):
                    for cit in msg["citations"]:
                        icon = "📄" if cit["source_type"] == "document" else "💡"
                        label = f"{icon} {cit['source_title']}"
                        if cit.get("page_number"):
                            label += f" · 第{cit['page_number']}页"
                        st.caption(label)

        # Input
        if prompt := st.chat_input("输入问题，或 /save + 内容 保存知识..."):
            # Handle /save command
            if prompt.strip().startswith("/save "):
                content = prompt.strip()[6:].strip()
                if content:
                    add_knowledge(module_id, content[:50], content)
                    st.success("✅ 知识已保存")
                    st.rerun()
            else:
                # Show user message
                with st.chat_message("user"):
                    st.markdown(prompt)
                history.append({"role": "user", "content": prompt, "citations": []})

                # RAG response
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    full_text = ""
                    citations = []

                    try:
                        for event_type, data in rag_stream(prompt, module_id, DEEPSEEK_API_KEY):
                            if event_type == "content":
                                full_text += data
                                response_placeholder.markdown(full_text + "▊")
                            elif event_type == "citations":
                                citations = data
                            elif event_type == "full_text":
                                full_text = data

                        response_placeholder.markdown(full_text)

                        if citations:
                            for cit in citations:
                                icon = "📄" if cit["source_type"] == "document" else "💡"
                                label = f"{icon} {cit['source_title']}"
                                if cit.get("page_number"):
                                    label += f" · 第{cit['page_number']}页"
                                st.caption(label)

                    except Exception as e:
                        full_text = f"回答失败: {e}"
                        response_placeholder.error(full_text)

                history.append({"role": "assistant", "content": full_text, "citations": citations})
                add_message(conv_id, "user", prompt)
                add_message(conv_id, "assistant", full_text, citations)

        st.session_state.chat_history[module_id] = history
