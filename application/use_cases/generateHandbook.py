import json
import re
from typing import List, Dict, Any

from domain.entities.document import Document
from infrastructure.config.settings import Settings


class GenerateHandbook:
    def __init__(self, llm, rag_service, lightrag_service=None):
        self.llm = llm
        self.rag_service = rag_service
        self.lightrag_service = lightrag_service
        self.target_words = Settings.HANDBOOK_TARGET_WORDS
        self.section_words = Settings.HANDBOOK_SECTION_WORDS

    async def execute(self, topic: str, documents: List[Document]) -> str:
        if not documents:
            return "No documents available. Please upload documents first."

        topic = topic.strip() or "Handbook"
        try:
            outline = self._create_outline(topic, documents)
        except Exception as err:
            if _is_rate_limit_error(err):
                return self._fallback_handbook(topic, documents, reason="Rate limit exceeded.")
            return (
                "Handbook generation failed while creating the outline. "
                "OpenRouter may be unavailable. Please check your internet "
                "connection and OPENROUTER_API_KEY, then try again.\n\n"
                f"Error: {err}"
            )

        handbook_lines = [f"# {topic} Handbook", ""]
        handbook_lines.append("## Table of Contents")
        for idx, section in enumerate(outline, 1):
            handbook_lines.append(f"{idx}. {section['title']}")
        handbook_lines.append("")

        total_words = 0
        for section in outline:
            if total_words >= self.target_words:
                break
            try:
                section_text = await self._write_section(topic, section["title"], self.section_words)
            except Exception as err:
                if _is_rate_limit_error(err):
                    return self._fallback_handbook(topic, documents, reason="Rate limit exceeded.")
                return (
                    "Handbook generation failed while writing a section. "
                    "OpenRouter may be unavailable. Please check your internet "
                    "connection and OPENROUTER_API_KEY, then try again.\n\n"
                    f"Error: {err}"
                )
            handbook_lines.append(f"## {section['title']}")
            handbook_lines.append(section_text)
            handbook_lines.append("")
            total_words += _word_count(section_text)

        return "\n".join(handbook_lines)

    async def stream_execute(self, topic: str, documents: List[Document]):
        if not documents:
            yield "No documents available. Please upload documents first."
            return

        topic = topic.strip() or "Handbook"
        try:
            outline = self._create_outline(topic, documents)
        except Exception as err:
            if _is_rate_limit_error(err):
                yield self._fallback_handbook(topic, documents, reason="Rate limit exceeded.")
                return
            yield (
                "Handbook generation failed while creating the outline. "
                "OpenRouter may be unavailable. Please check your internet "
                "connection and OPENROUTER_API_KEY, then try again.\n\n"
                f"Error: {err}"
            )
            return

        handbook_lines = [f"# {topic} Handbook", ""]
        handbook_lines.append("## Table of Contents")
        for idx, section in enumerate(outline, 1):
            handbook_lines.append(f"{idx}. {section['title']}")
        handbook_lines.append("")
        handbook_text = "\n".join(handbook_lines)
        yield handbook_text

        total_words = 0
        for section in outline:
            if total_words >= self.target_words:
                break
            try:
                section_text = await self._write_section(topic, section["title"], self.section_words)
            except Exception as err:
                if _is_rate_limit_error(err):
                    yield self._fallback_handbook(topic, documents, reason="Rate limit exceeded.")
                    return
                yield (
                    "Handbook generation failed while writing a section. "
                    "OpenRouter may be unavailable. Please check your internet "
                    "connection and OPENROUTER_API_KEY, then try again.\n\n"
                    f"Error: {err}"
                )
                return

            handbook_text += f"\n## {section['title']}\n"
            for chunk in _stream_chunks(section_text):
                handbook_text += chunk
                yield handbook_text
            handbook_text += "\n"
            total_words += _word_count(section_text)

    def _fallback_handbook(self, topic: str, documents: List[Document], reason: str) -> str:
        outline = self._fallback_outline(documents)
        handbook_lines = [f"# {topic} Handbook", ""]
        handbook_lines.append(f"_Generated in fallback mode: {reason}_")
        handbook_lines.append("")
        handbook_lines.append("## Table of Contents")
        for idx, section in enumerate(outline, 1):
            handbook_lines.append(f"{idx}. {section['title']}")
        handbook_lines.append("")

        for section in outline:
            handbook_lines.append(f"## {section['title']}")
            sources = self.rag_service.retrieve(f"{topic} - {section['title']}")
            context = _build_context_block(sources, max_snippets=8)
            handbook_lines.append(context or "No context available.")
            handbook_lines.append("")

        return "\n".join(handbook_lines)

    def _create_outline(self, topic: str, documents: List[Document]) -> List[Dict[str, Any]]:
        doc_titles = [doc.file_name for doc in documents if doc.file_name]
        outline_hint = self._fallback_outline(documents)

        prompt = (
            "You are generating a handbook outline.\n"
            f"Topic: {topic}\n"
            f"Documents: {', '.join(doc_titles)}\n\n"
            "Return a JSON array of section objects with a 'title' field.\n"
            "Aim for 10-16 sections. Keep titles concise.\n"
            f"Existing outline hints: {outline_hint}\n"
        )

        response = self.llm.generate(prompt, max_tokens=800)
        parsed = _parse_json_array(response)
        if parsed:
            return [{"title": str(item.get("title", "")).strip() or "Untitled"} for item in parsed]

        return outline_hint or [{"title": "Overview"}, {"title": "Key Concepts"}, {"title": "Applications"}]

    def _fallback_outline(self, documents: List[Document]) -> List[Dict[str, Any]]:
        titles = []
        for doc in documents:
            outline = getattr(doc, "outline", [])
            for chapter in outline[:8]:
                title = str(chapter.get("chapter", "")).strip()
                if title:
                    titles.append({"title": title})
            if len(titles) >= 12:
                break
        return titles

    async def _write_section(self, topic: str, section_title: str, target_words: int) -> str:
        if self.lightrag_service:
            result = await self.lightrag_service.query(
                f"Write a detailed section about {section_title} for a handbook on {topic}.",
                mode="hybrid",
            )
            return result or ""

        sources = self.rag_service.retrieve(f"{topic} - {section_title}")
        context = _build_context_block(sources, max_snippets=6)

        base_prompt = (
            f"Write a detailed handbook section.\n"
            f"Topic: {topic}\n"
            f"Section title: {section_title}\n"
            f"Target length: {target_words} words.\n"
            "Use the provided context. Cite sources inline as [source: DocumentName].\n"
            f"Context:\n{context}\n"
        )

        section_text = self.llm.generate(base_prompt, max_tokens=1600)
        attempts = 0
        while _word_count(section_text) < target_words and attempts < 2:
            continuation_prompt = (
                f"Continue the section '{section_title}' with additional depth.\n"
                f"Keep coherence and avoid repeating sentences.\n"
                f"Current text (truncated):\n{section_text[-1200:]}\n"
            )
            section_text += "\n\n" + self.llm.generate(continuation_prompt, max_tokens=1600)
            attempts += 1

        section_text = section_text.strip()
        if sources:
            section_text += "\n\nSources:\n" + "\n".join(
                f"- {src.get('metadata', {}).get('document_name', 'Unknown')}" for src in sources
            )
        return section_text


def _parse_json_array(text: str) -> List[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return []


def _build_context_block(results: List[Dict[str, Any]], max_snippets: int) -> str:
    snippets = []
    for result in results[:max_snippets]:
        meta = result.get("metadata", {}) or {}
        doc_name = meta.get("document_name", "Unknown")
        text = meta.get("text", "")
        if not text:
            continue
        snippets.append(f"[{doc_name}] {text}")
    return "\n\n".join(snippets).strip() or "No context available."


def _word_count(text: str) -> int:
    return len(text.split())


def _is_rate_limit_error(err: Exception) -> bool:
    message = str(err).lower()
    return "rate limit" in message or "429" in message


def _stream_chunks(text: str, chunk_size: int = 80):
    if not text:
        return
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
