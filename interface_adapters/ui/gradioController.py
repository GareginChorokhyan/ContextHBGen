import gradio as gr
from pathlib import Path
from datetime import datetime
from typing import List

from domain.entities.document import Document
from domain.services.paragraphChunking import ParagraphChunking
from domain.services.chunkingService import ChunkingService
from domain.services.outlineService import OutlineService
from domain.services.ragService import RagService
from domain.services.lightRagService import LightRagService
from domain.ports.documentLoader import DocumentLoader
from infrastructure.loaders.pathBasedLoader import PathBasedLoader
from infrastructure.llm.openrouter_client import OpenRouterLLM
from infrastructure.vector_store.supabase_pgvector import VectorStore
from infrastructure.vector_store.in_memory import InMemoryVectorStore
from infrastructure.llm.local_embedder import LocalHashEmbedder
from infrastructure.config.settings import Settings
from application.use_cases.ingestDocument import IngestDocument
from application.use_cases.handbookStructure import HandbookStructure
from application.use_cases.generateHandbook import GenerateHandbook
from application.dto.handbookResult import HandbookResult


processed_documents: List[Document] = []
latest_handbook_result: HandbookResult = None
rag_service_instance: RagService = None
light_rag_service_instance: LightRagService = None
stop_handbook_flag: bool = False


def _create_ingest_use_case() -> IngestDocument:
    loader: DocumentLoader = PathBasedLoader()
    strategy = ParagraphChunking(min_words=200, max_words=500)
    chunking_service = ChunkingService(strategy)
    outline_service = OutlineService(max_chunk_per_section=5, max_title_words=10)
    rag_service = _get_or_create_rag_service()
    lightrag_service = _get_or_create_lightrag_service()
    return IngestDocument(
        document_loader=loader,
        chunking_service=chunking_service,
        outline_service=outline_service,
        rag_service=rag_service,
        lightrag_service=lightrag_service,
    )


def _get_or_create_rag_service() -> RagService:
    global rag_service_instance
    if rag_service_instance:
        return rag_service_instance

    embedder = OpenRouterLLM()
    fallback_embedder = LocalHashEmbedder()
    fallback_vector_store = InMemoryVectorStore()
    try:
        if Settings.SUPABASE_URL and Settings.SUPABASE_KEY:
            vector_store = VectorStore()
        else:
            vector_store = InMemoryVectorStore()
    except Exception:
        vector_store = InMemoryVectorStore()
    rag_service_instance = RagService(
        embedder=embedder,
        vector_store=vector_store,
        fallback_embedder=fallback_embedder,
        fallback_vector_store=fallback_vector_store,
    )
    return rag_service_instance


def _get_or_create_lightrag_service() -> LightRagService:
    global light_rag_service_instance
    if light_rag_service_instance:
        return light_rag_service_instance
    if not Settings.USE_LIGHTRAG:
        return None
    try:
        light_rag_service_instance = LightRagService()
    except Exception:
        light_rag_service_instance = None
    return light_rag_service_instance


async def process_documents(files) -> tuple[str, str, str]:
    global processed_documents, latest_handbook_result

    if not files:
        return "⚠️ No files uploaded. Please select at least one document.", "", ""

    file_paths = [Path(f) if not isinstance(f, Path) else f for f in files]
    paths = [str(p) for p in file_paths]
    names = [p.name for p in file_paths]

    ingest = _create_ingest_use_case()
    try:
        documents = ingest.execute(files=paths, doc_names=names)
    except Exception as e:
        return f"❌ Error processing documents: {e}", "", ""

    processed_documents.clear()
    processed_documents.extend(documents)

    lightrag_service = _get_or_create_lightrag_service()
    if lightrag_service:
        for doc in documents:
            chunks = [c.text for c in doc.chunks.get_chunks()]
            chunk_ids = [c.chunk_id for c in doc.chunks.get_chunks()]
            try:
                await lightrag_service.insert_chunks(
                    chunks,
                    ids=chunk_ids,
                    file_path=doc.metadata.source,
                )
            except Exception as err:
                return f"❌ Error indexing document into LightRAG: {err}", "", ""

    handbook_builder = HandbookStructure(max_total_words=20000)
    latest_handbook_result = handbook_builder.build_for_documents(documents)

    results = []
    for doc in documents:
        results.append(f"✅ **{doc.file_name}**")
        results.append(f"   • Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        results.append(f"   • Chunks extracted: {doc.chunks.count_chunks()}")
        outline = getattr(doc, "outline", [])
        results.append(f"   • Sections: {len(outline)}")
        results.append("")

    summary = f"### 📚 Successfully Processed {len(processed_documents)} Document(s)\n\n"
    summary += "\n".join(results)
    doc_list = "\n".join([f"• {doc.file_name}" for doc in processed_documents])
    
    handbook_display = _format_handbook_result(latest_handbook_result)

    return summary, doc_list, handbook_display


async def generate_handbook(topic: str):
    if not processed_documents:
        yield "No documents processed yet. Upload documents first."
        return

    global stop_handbook_flag
    stop_handbook_flag = False

    rag_service = _get_or_create_rag_service()
    llm = OpenRouterLLM()
    lightrag_service = _get_or_create_lightrag_service()
    generator = GenerateHandbook(
        llm=llm,
        rag_service=rag_service,
        lightrag_service=lightrag_service,
    )
    try:
        async for update in generator.stream_execute(topic, processed_documents):
            if stop_handbook_flag:
                break
            yield update
    except Exception as err:
        yield (
            "Handbook generation failed. OpenRouter may be unavailable. "
            "Please verify your internet connection and API key.\n\n"
            f"Error: {err}"
        )


def _format_handbook_result(handbook_result: HandbookResult) -> str:
    if not handbook_result or not handbook_result.sections:
        return "No handbook structure generated yet."
    
    lines = ["## 📖 Handbook Structure\n"]
    lines.append(f"**Total Sections:** {len(handbook_result.sections)}\n")
    lines.append("---\n")
    
    for i, section in enumerate(handbook_result.sections, 1):
        lines.append(f"### {section.section_title}")
        lines.append(f"**Chunk IDs:** {len(section.chunk_ids)} chunks")
        
        if len(section.chunk_ids) <= 5:
            for chunk_id in section.chunk_ids:
                lines.append(f"  - `{chunk_id}`")
        else:
            for chunk_id in section.chunk_ids[:3]:
                lines.append(f"  - `{chunk_id}`")
            lines.append(f"  - ... and {len(section.chunk_ids) - 3} more chunks")
        lines.append("")
    
    return "\n".join(lines)


def get_handbook_result() -> HandbookResult:
    return latest_handbook_result


def view_chunk_content(chunk_id: str) -> str:
    if not processed_documents:
        return "No documents processed yet."
    
    for doc in processed_documents:
        for chunk in doc.chunks.get_chunks():
            if chunk.chunk_id == chunk_id:
                return f"**Chunk ID:** `{chunk.chunk_id}`\n\n**Document:** {doc.file_name}\n\n**Content:**\n\n{chunk.text}"
    
    return f"Chunk with ID `{chunk_id}` not found."


def list_all_chunks() -> str:
    if not processed_documents:
        return "No documents processed yet."
    
    lines = ["## 📋 All Chunks\n"]
    
    for doc in processed_documents:
        lines.append(f"### 📄 {doc.file_name}")
        lines.append(f"**Total chunks:** {doc.chunks.count_chunks()}\n")
        
        for chunk in doc.chunks.get_chunks():
            preview = chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text
            preview = preview.replace("\n", " ")
            lines.append(f"**`{chunk.chunk_id}`**")
            lines.append(f"> {preview}\n")
    
    return "\n".join(lines)


def get_processed_documents() -> List[Document]:
    return list(processed_documents)


async def chat_with_ai(message, history):
    if not message or not str(message).strip():
        yield history or []
        return

    docs = get_processed_documents()
    context_info = ""
    if docs:
        context_info = f" (📎 {len(docs)} document(s) loaded)"

    if not docs:
        response = "No documents have been uploaded yet. Please upload documents in the 'Document Upload' tab first."
    else:
        lightrag_service = _get_or_create_lightrag_service()
        if lightrag_service:
            try:
                response = await lightrag_service.query(message, mode=Settings.LIGHTRAG_QUERY_MODE)
            except Exception as err:
                response = (
                    "LightRAG query failed. Check your Supabase Postgres settings and "
                    "OpenRouter connectivity.\n\n"
                    f"Error: {err}"
                )
        else:
            rag_service = _get_or_create_rag_service()
            sources = rag_service.retrieve(message)
            context = []
            for item in sources[:6]:
                meta = item.get("metadata", {}) or {}
                doc_name = meta.get("document_name", "Unknown")
                text = meta.get("text", "")
                if text:
                    context.append(f"[{doc_name}] {text}")
            context_block = "\n\n".join(context) if context else "No relevant context found."

            prompt = (
                "You are a helpful assistant answering questions using the provided context.\n"
                "Answer clearly and cite sources inline as [source: DocumentName].\n\n"
                f"Context:\n{context_block}\n\n"
                f"Question: {message}\n"
            )
            try:
                llm = OpenRouterLLM()
                response = llm.generate(prompt, max_tokens=800)
            except Exception as err:
                err_msg = str(err)
                if "rate limit" in err_msg.lower() or "429" in err_msg:
                    response = (
                        "OpenRouter rate limit reached. Here's a context-only answer based "
                        "on your documents:\n\n"
                        f"{context_block}\n\n"
                        "Add credits or switch to a paid model for full LLM responses."
                    )
                else:
                    response = (
                        "I couldn't reach the LLM right now. Please check your OpenRouter "
                        "connection or rate limits and try again.\n\n"
                        f"Error: {err}"
                    )

    if history is None:
        history = []
    history.append({"role": "user", "content": str(message).strip()})
    if not response:
        response = "No response generated. Please try again."
    history.append({"role": "assistant", "content": ""})
    yield history

    for chunk in _stream_chunks(str(response)):
        history[-1]["content"] += chunk
        yield history


def clear_chat():
    return []


def _stream_chunks(text: str, chunk_size: int = 80):
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def stop_handbook():
    global stop_handbook_flag
    stop_handbook_flag = True
    return None


def _toggle_chat_controls(enabled: bool, extra_buttons=None):
    updates = [
        gr.update(interactive=enabled),
        gr.update(interactive=enabled),
        gr.update(interactive=enabled),
    ]
    if extra_buttons:
        updates.extend([gr.update(interactive=enabled) for _ in extra_buttons])
    return updates


def example_question_clicked(question):
    return question


CUSTOM_CSS = """
/* Main container styling */
.gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Header styling */
.header-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
}

.header-title {
    color: white;
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
    text-align: center;
}

.header-subtitle {
    color: rgba(255, 255, 255, 0.9);
    font-size: 1.1rem;
    text-align: center;
    margin-top: 0.5rem;
}

/* Tab styling */
.tab-nav button {
    font-size: 1rem !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
}

.chatbot {
    border-radius: 12px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08) !important;
}

.chatbot .avatar img,
.chatbot img.avatar,
.chatbot .avatar > img {
    object-fit: cover !important;
    border-radius: 50% !important;
    width: 100% !important;
    height: 100% !important;
}

/* Button styling */
.primary-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 0.75rem 2rem !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
}

.primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
}

.secondary-btn {
    background: white !important;
    border: 2px solid #667eea !important;
    color: #667eea !important;
    font-weight: 600 !important;
    padding: 0.75rem 2rem !important;
    border-radius: 8px !important;
}

/* Example questions */
.example-btn {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
    border: none !important;
    color: white !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 20px !important;
    font-size: 0.9rem !important;
    margin: 0.3rem !important;
}

/* Info boxes */
.info-box {
    background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
    padding: 1.5rem;
    border-radius: 10px;
    border-left: 4px solid #667eea;
    margin: 1rem 0;
}

.doc-list {
    background: #f8f9ff;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e0e7ff;
}
"""


def create_demo() -> gr.Blocks:
    with gr.Blocks() as demo:
        
        gr.HTML("""
            <div class="header-container">
                <h1 class="header-title">🚀 Ultimate AI Chat Assistant</h1>
                <p class="header-subtitle">Upload documents, ask questions, and get intelligent answers</p>
            </div>
        """)
        
        generate_handbook_btn = None
        with gr.Tabs() as tabs:
            
            with gr.Tab("💬 Chat", id="chat"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            label="Conversation",
                            height=500,
                            show_label=False,
                            avatar_images=(None, "assets/images/logo.png")
                        )
                        
                        with gr.Row():
                            msg = gr.Textbox(
                                label="Message",
                                placeholder="Type your message here... (Shift + Enter for new line)",
                                show_label=False,
                                scale=4,
                                container=False
                            )
                            send_btn = gr.Button("Send 📤", scale=1, elem_classes="primary-btn")
                        
                        with gr.Row():
                            clear_btn = gr.Button("🗑️ Clear Chat", scale=1, elem_classes="secondary-btn")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### 📎 Loaded Documents")
                        doc_display = gr.Textbox(
                            label="Documents",
                            placeholder="No documents loaded yet",
                            interactive=False,
                            lines=8,
                            show_label=False,
                            elem_classes="doc-list"
                        )
                        
                        gr.Markdown("### 💡 Example Questions")
                        example_questions = [
                            "What documents do I have uploaded?",
                            "Summarize the main points",
                            "What are the key takeaways?",
                            "Explain this in simple terms"
                        ]
                        example_buttons = []
                        example_button_defs = []
                        for question in example_questions:
                            ex_btn = gr.Button(question, size="sm", elem_classes="example-btn")
                            example_buttons.append(ex_btn)
                            example_button_defs.append((ex_btn, question))
                
                clear_btn.click(clear_chat, None, chatbot)
            
            with gr.Tab("📄 Document Upload", id="upload"):
                gr.Markdown("""
                    ### Upload Your Documents
                    
                    Upload PDF, DOCX, or TXT files to enhance the AI's knowledge base.
                    The system will process and index your documents for intelligent Q&A.
                """)
                
                with gr.Row():
                    with gr.Column(scale=2):
                        file_input = gr.File(
                            label="📁 Select Documents",
                            type="filepath",
                            file_types=[".pdf", ".docx", ".txt"],
                            file_count="multiple",
                            height=200
                        )
                        
                        with gr.Row():
                            upload_btn = gr.Button("🔄 Process Documents", scale=2, elem_classes="primary-btn")
                    
                    with gr.Column(scale=3):
                        upload_output = gr.Markdown(
                            value="Upload documents to see processing results here...",
                            label="Processing Results"
                        )
                
                gr.Markdown("""
                    ---
                    
                    ### ✨ Features
                    
                    - 🔍 **Intelligent Search**: Ask questions and get context-aware answers
                    - 📊 **Document Analysis**: Automatic chunking and outline generation
                    - 💾 **Multi-format Support**: PDF, DOCX, and TXT files
                    - 🎯 **Contextual Responses**: Answers based on your uploaded documents
                    - ⚡ **Fast Processing**: Quick document indexing and retrieval
                """)
            
            with gr.Tab("📖 Handbook", id="handbook"):
                gr.Markdown("""
                    ### 📖 Handbook Structure Preview
                    
                    This tab shows the **HandbookResult** generated from your processed documents.
                    Use this to verify how your chunking and outline logic works before integrating LLM/RAG.
                """)
                
                with gr.Row():
                    with gr.Column(scale=2):
                        handbook_display = gr.Markdown(
                            value="Process documents in the 'Document Upload' tab to see the handbook structure here...",
                            label="Handbook Structure"
                        )
                        gr.Markdown("### 📝 Generate Handbook")
                        handbook_topic = gr.Textbox(
                            label="Handbook Topic",
                            placeholder="e.g., Retrieval-Augmented Generation",
                            show_label=True
                        )
                        with gr.Row():
                            generate_handbook_btn = gr.Button("Generate Handbook", elem_classes="primary-btn")
                            stop_handbook_btn = gr.Button("Stop", elem_classes="secondary-btn")
                        handbook_text = gr.Markdown(
                            value="Generated handbook will appear here.",
                            label="Generated Handbook"
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### 🔍 View Chunk Content")
                        chunk_id_input = gr.Textbox(
                            label="Chunk ID",
                            placeholder="Enter chunk ID (e.g., abc123_1)",
                            show_label=True
                        )
                        view_chunk_btn = gr.Button("View Chunk", elem_classes="secondary-btn")
                        chunk_content_display = gr.Markdown(
                            value="Enter a chunk ID above to view its content.",
                            label="Chunk Content"
                        )
                
                view_chunk_btn.click(
                    view_chunk_content,
                    inputs=chunk_id_input,
                    outputs=chunk_content_display
                )
                
                handbook_event = generate_handbook_btn.click(
                    fn=lambda: _toggle_chat_controls(False, example_buttons) + [gr.update(interactive=False)],
                    inputs=None,
                    outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
                    queue=False,
                ).then(
                    fn=generate_handbook,
                    inputs=handbook_topic,
                    outputs=handbook_text,
                ).then(
                    fn=lambda: _toggle_chat_controls(True, example_buttons) + [gr.update(interactive=True)],
                    inputs=None,
                    outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
                    queue=False,
                )
                stop_handbook_btn.click(
                    fn=stop_handbook,
                    inputs=None,
                    outputs=None,
                    queue=False,
                ).then(
                    fn=lambda: _toggle_chat_controls(True, example_buttons) + [gr.update(interactive=True)],
                    inputs=None,
                    outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
                    queue=False,
                )
                
                gr.Markdown("---")
                
                with gr.Accordion("📋 View All Chunks", open=False):
                    all_chunks_btn = gr.Button("Load All Chunks", elem_classes="secondary-btn")
                    all_chunks_display = gr.Markdown(
                        value="Click 'Load All Chunks' to see all chunk previews.",
                        label="All Chunks"
                    )
                    all_chunks_btn.click(
                        list_all_chunks,
                        inputs=None,
                        outputs=all_chunks_display
                    )
            
            
            with gr.Tab("⚙️ About", id="about"):
                gr.Markdown("""
                    # About This Application
                    
                    ## 🎯 Purpose
                    This is a demonstration of a modern, beautiful chat interface built with Gradio.
                    It showcases best practices in UI/UX design for AI-powered applications.
                    
                    ## ✨ Key Features
                    
                    - **Beautiful Design**: Modern gradient styling with smooth animations
                    - **Intuitive Interface**: Easy-to-use chat and document upload
                    - **Responsive Layout**: Works great on all screen sizes
                    - **Document Processing**: Upload and analyze multiple documents
                    - **Context-Aware Chat**: AI responses based on uploaded content
                    - **Example Questions**: Quick-start templates for common queries
                    
                    ## 🛠️ Technical Stack
                    
                    - **Framework**: Gradio 4.0+
                    - **Language**: Python 3.8+
                    - **Styling**: Custom CSS with modern design principles
                    - **Features**: File upload, chat history, state management
                    
                    ## 📝 How to Use
                    
                    1. **Upload Documents**: Go to the "Document Upload" tab and select your files
                    2. **Process**: Click "Process Documents" to index them
                    3. **Chat**: Switch to the "Chat" tab and start asking questions
                    4. **Examples**: Use example questions to get started quickly
                    
                    ## 🚀 Future Enhancements
                    
                    - Real AI integration (OpenAI, Anthropic, etc.)
                    - Multiple file support (PDF, DOCX, TXT)
                    - Streaming responses for chat and handbook
                    - LightRAG + Supabase pgvector indexing
                    
                    ---
                    
                    **Version**: 2.0  
                    **Last Updated**: 2026  
                    **License**: MIT
                """)
        
        upload_btn.click(
            process_documents, 
            inputs=file_input, 
            outputs=[upload_output, doc_display, handbook_display]
        )
        
        for ex_btn, question in example_button_defs:
            ex_btn.click(
                fn=lambda: _toggle_chat_controls(False, example_buttons) + [gr.update(interactive=False)],
                inputs=None,
                outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
                queue=False,
            ).then(
                fn=chat_with_ai,
                inputs=[gr.State(question), chatbot],
                outputs=chatbot
            ).then(
                fn=lambda: _toggle_chat_controls(True, example_buttons) + [gr.update(interactive=True)],
                inputs=None,
                outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
                queue=False,
            )
        
        msg.submit(
            fn=lambda: _toggle_chat_controls(False, example_buttons) + [gr.update(interactive=False)],
            inputs=None,
            outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
            queue=False,
        ).then(
            fn=chat_with_ai,
            inputs=[msg, chatbot],
            outputs=chatbot,
        ).then(
            fn=lambda: _toggle_chat_controls(True, example_buttons) + [gr.update(interactive=True)],
            inputs=None,
            outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
            queue=False,
        ).then(
            lambda: "", None, msg
        )
        send_btn.click(
            fn=lambda: _toggle_chat_controls(False, example_buttons) + [gr.update(interactive=False)],
            inputs=None,
            outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
            queue=False,
        ).then(
            fn=chat_with_ai,
            inputs=[msg, chatbot],
            outputs=chatbot,
        ).then(
            fn=lambda: _toggle_chat_controls(True, example_buttons) + [gr.update(interactive=True)],
            inputs=None,
            outputs=[send_btn, clear_btn, msg] + example_buttons + [generate_handbook_btn],
            queue=False,
        ).then(
            lambda: "", None, msg
        )

    return demo
