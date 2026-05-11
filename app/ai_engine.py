import os
import re
import sys
import json
import asyncio

# Fix Windows cp1252 emoji encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

from google import genai

from app.scraping import WebScraper
from app.retrieval import RetrievalEngine


# =====================================================
# LOAD ENV
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

dotenv_path = os.path.join(BASE_DIR, "..", ".env")

load_dotenv(dotenv_path, override=True)


# =====================================================
# SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """
You are an intelligent AI assistant — like ChatGPT — capable of:
1. Answering general knowledge questions using web-retrieved information
2. Analyzing uploaded documents (PDF, TXT, CSV, DOCX, JSON, MD)
3. Combining document knowledge with live web data

RULES:
- Be conversational, helpful, and accurate
- If document chunks are available, prioritize them but also use your general knowledge
- If only web results are available, synthesize them clearly
- If no context exists, answer from your own knowledge and say so
- NEVER refuse to answer — always provide the best response you can
- Use inline citations when referencing sources
- Keep answers concise unless the user asks for detail
- Maintain conversational continuity with the chat history
"""

# =====================================================
# INTENT CLASSIFICATION PROMPT
# =====================================================

INTENT_PROMPT = """
You are an intelligent query router for a hybrid AI system.

Analyze the user query and conversation history, then classify the intent.

Conversation History:
{history}

User Query:
{query}

Has uploaded document: {has_doc}

Return ONLY valid JSON — no markdown, no explanation:

{{
    "intent": "<one of: general | rag_only | hybrid | summary | comparison>",
    "rewritten_query": "<semantically optimized version of the query>",
    "needs_web_search": <true|false>,
    "needs_doc_search": <true|false>,
    "reasoning": "<one line explanation>"
}}

Intent definitions:
- "general"     : General knowledge, facts, news, current events — use web search
- "rag_only"    : Specific question about the uploaded document content
- "hybrid"      : Question that benefits from BOTH document AND web data
- "summary"     : User wants a summary / overview of the entire document
- "comparison"  : Compare document content with external information

Rules:
- If no document uploaded → always use "general" (web search)
- If user says "in my document / in this file / from the PDF" → "rag_only"
- If query is about current events, news, prices, live data → "general"
- If query references both doc and external world → "hybrid"
- Short greetings (hi, hello, thanks) → "general", needs_web_search: false
"""


# =====================================================
# AI ENGINE
# =====================================================

class AIEngine:

    def __init__(self):

        self.retrieval = RetrievalEngine()
        self.scraper = WebScraper()

        self.model_name = "gemini-2.5-flash"

        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

        print("\n✅ AI ENGINE READY\n")

    # =================================================
    # INTENT CLASSIFICATION  ← NEW
    # =================================================

    async def classify_intent(self, query, history, has_doc):
        """
        LLM-powered intent router. Returns:
        {intent, rewritten_query, needs_web_search, needs_doc_search, reasoning}
        """
        try:
            history_text = "\n".join([
                f"{m['role']}: {m['content']}"
                for m in history[-6:]
            ])

            prompt = INTENT_PROMPT.format(
                history=history_text or "No history",
                query=query,
                has_doc=str(has_doc)
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )

            text = response.text.strip()

            # Strip markdown fences if present
            text = re.sub(r"```json", "", text)
            text = re.sub(r"```", "", text)
            text = text.strip()

            parsed = json.loads(text)

            intent = parsed.get("intent", "general")
            rewritten_query = parsed.get("rewritten_query", query)
            needs_web = parsed.get("needs_web_search", True)
            needs_doc = parsed.get("needs_doc_search", has_doc)

            # Safety overrides
            if not has_doc:
                needs_doc = False
                if intent in ("rag_only", "summary", "comparison"):
                    intent = "general"
                needs_web = True

            # ← FIXED: Never override short greetings with doc summary
            lower_q = query.lower().strip()
            greetings = {"hi", "hello", "hey", "thanks", "ok", "bye"}
            if lower_q in greetings or len(query.split()) <= 2:
                intent = "general"
                needs_web = False
                needs_doc = False
                rewritten_query = query

            print(f"\n🧠 Intent: {intent} | Web: {needs_web} | Doc: {needs_doc}")
            print(f"📝 Rewritten: {rewritten_query}\n")

            return {
                "intent": intent,
                "rewritten_query": rewritten_query,
                "needs_web_search": needs_web,
                "needs_doc_search": needs_doc,
                "reasoning": parsed.get("reasoning", "")
            }

        except Exception as e:
            print(f"\n❌ INTENT CLASSIFICATION ERROR: {e}\n")

            # Safe fallback
            return {
                "intent": "general" if not has_doc else "hybrid",
                "rewritten_query": query,
                "needs_web_search": not has_doc,
                "needs_doc_search": has_doc,
                "reasoning": "fallback"
            }

    # =================================================
    # MEMORY
    # =================================================

    async def retrieve_memory(self, history):
        memory = []
        for msg in (history or [])[-8:]:
            memory.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return memory

    # =================================================
    # DOCUMENT RETRIEVAL (ASYNC)
    # =================================================

    async def retrieve_docs_async(self, query):
        try:
            print(f"\n🔍 Running Doc Retrieval: {query[:80]}\n")

            if not self.retrieval.active_documents:
                print("\n❌ No Active Documents\n")
                return []

            results = await asyncio.to_thread(
                self.retrieval.retrieve_from_docs,
                query,
                8
            )

            print(f"\n📄 Doc Results: {len(results)}\n")
            return results

        except Exception as e:
            print(f"\n❌ DOC RETRIEVAL ERROR: {e}\n")
            return []

    # =================================================
    # SUMMARY RETRIEVAL — gets full doc context
    # =================================================

    async def retrieve_full_doc_async(self):
        """For summary intent — retrieve broad chunks."""
        try:
            fallback_query = (
                "main topics key concepts important information "
                "overview summary introduction conclusion"
            )
            results = await asyncio.to_thread(
                self.retrieval.retrieve_from_docs,
                fallback_query,
                15
            )
            print(f"\n📋 Summary chunks: {len(results)}\n")
            return results
        except Exception as e:
            print(f"\n❌ SUMMARY RETRIEVAL ERROR: {e}\n")
            return []

    # =================================================
    # WEB RETRIEVAL (ASYNC)
    # =================================================

    async def retrieve_web_async(self, query):
        try:
            print(f"\n🌐 Running Web Search: {query[:80]}\n")

            documents = await self.scraper.scrape(query)

            if not documents:
                print("\n❌ No Web Documents\n")
                return []

            results = await asyncio.to_thread(
                self.retrieval.retrieve_web_documents,
                query,
                documents,
                6
            )

            print(f"\n🌐 Web Results: {len(results)}\n")
            return results

        except Exception as e:
            print(f"\n❌ WEB RETRIEVAL ERROR: {e}\n")
            return []

    # =================================================
    # ANSWER GENERATION  ← FIXED SYSTEM PROMPT
    # =================================================

    async def generate_answer(
        self,
        query,
        rewritten_query,
        context,
        memory,
        retrieved_docs,
        intent
    ):
        try:
            memory_context = "\n".join([
                f"{m['role'].upper()}: {m['content']}"
                for m in memory
            ])

            # Build citation list
            citations = []
            for chunk in retrieved_docs[:10]:
                doc_name = chunk.get("document_name", "unknown")
                page = chunk.get("page_number")
                source = chunk.get("source", "")

                if chunk.get("type") == "web":
                    citations.append(f"🌐 {doc_name} ({source})")
                elif page:
                    citations.append(f"📄 {doc_name} — Page {page}")
                else:
                    citations.append(f"📄 {doc_name}")

            citations_text = "\n".join(sorted(set(citations)))

            doc_chunks = [c for c in retrieved_docs if c.get("type") != "web"]
            web_chunks = [c for c in retrieved_docs if c.get("type") == "web"]

            # Build intent-aware instruction
            if intent == "summary":
                task_instruction = """
Provide a comprehensive, well-structured SUMMARY of the document.
Cover: main topics, key arguments, important data, conclusions.
Use headers and bullet points for clarity.
"""
            elif intent == "rag_only":
                task_instruction = """
Answer the user's question using ONLY the document chunks provided.
If the document does not contain the answer, say so clearly.
"""
            elif intent == "general":
                task_instruction = """
Answer the user's question using the web search results and your general knowledge.
Be accurate, concise, and cite sources where possible.
"""
            elif intent == "comparison":
                task_instruction = """
Compare the information in the document with the web results.
Highlight similarities, differences, and insights.
"""
            else:  # hybrid
                task_instruction = """
Answer using BOTH the document and web search results.
Prioritize document content when relevant, supplement with web data.
"""

            prompt = f"""{SYSTEM_PROMPT}

================ CONVERSATION HISTORY ================
{memory_context or "No previous conversation."}
======================================================

================ RETRIEVED CONTEXT ==================
{context or "No context retrieved. Use your general knowledge."}
======================================================

QUERY: {rewritten_query}

INTENT: {intent}
DOCUMENT CHUNKS: {len(doc_chunks)}
WEB CHUNKS: {len(web_chunks)}

AVAILABLE SOURCES:
{citations_text or "None"}

TASK:
{task_instruction}

Answer:"""

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )

            return response.text

        except Exception as e:
            print(f"\n❌ GENERATION ERROR: {e}\n")
            return (
                "I encountered an error while generating the response. "
                "Please try again."
            )

    # =================================================
    # MAIN PIPELINE  ← ChatGPT architecture
    # =================================================

    async def process_query(self, query, history=None):
        if history is None:
            history = []

        try:
            print(f"\n💬 USER QUERY: {query}\n")
            print(f"\n📚 Active Docs: {self.retrieval.active_documents}\n")

            has_doc = (
                len(self.retrieval.active_documents) > 0
                and self.retrieval.pdf_vectordb is not None
            )

            # =========================================
            # STEP 1: INTENT CLASSIFICATION + MEMORY
            # Run in parallel
            # =========================================

            intent_task = self.classify_intent(query, history, has_doc)
            memory_task = self.retrieve_memory(history)

            classification, memory = await asyncio.gather(
                intent_task,
                memory_task
            )

            intent = classification["intent"]
            rewritten_query = classification["rewritten_query"]
            needs_web = classification["needs_web_search"]
            needs_doc = classification["needs_doc_search"]

            # =========================================
            # STEP 2: PARALLEL RETRIEVAL
            # =========================================

            retrieval_tasks = []
            retrieval_keys = []

            if needs_doc and has_doc:
                if intent == "summary":
                    retrieval_tasks.append(self.retrieve_full_doc_async())
                else:
                    retrieval_tasks.append(self.retrieve_docs_async(rewritten_query))
                retrieval_keys.append("doc")

            if needs_web:
                retrieval_tasks.append(self.retrieve_web_async(rewritten_query))
                retrieval_keys.append("web")

            if not retrieval_tasks:
                # Pure conversational / greeting
                retrieval_results = []
            else:
                retrieval_results = await asyncio.gather(
                    *retrieval_tasks,
                    return_exceptions=True
                )

            doc_results = []
            web_results = []

            for idx, result in enumerate(retrieval_results):
                if isinstance(result, Exception):
                    print(f"\n❌ Retrieval Exception: {result}\n")
                    continue

                key = retrieval_keys[idx]

                if key == "doc":
                    doc_results = result
                elif key == "web":
                    web_results = result

            # =========================================
            # STEP 3: DOC FALLBACK
            # =========================================

            if needs_doc and has_doc and not doc_results:
                print("\n🔄 Doc Fallback — broadening search...\n")
                doc_results = await self.retrieve_full_doc_async()

            print(f"\n📄 Final Doc Chunks: {len(doc_results)}")
            print(f"🌐 Final Web Chunks: {len(web_results)}\n")

            # =========================================
            # STEP 4: HYBRID FUSION
            # =========================================

            retrieved_docs = await asyncio.to_thread(
                self.retrieval.fuse_contexts,
                doc_results,
                web_results
            )

            print(f"\n📚 Total After Fusion: {len(retrieved_docs)}\n")

            # =========================================
            # STEP 5: BUILD CONTEXT
            # =========================================

            if retrieved_docs:
                grounded_context = await asyncio.to_thread(
                    self.retrieval.build_context,
                    retrieved_docs,
                    30000
                )
            else:
                grounded_context = ""

            # =========================================
            # STEP 6: GENERATE ANSWER
            # =========================================

            answer = await self.generate_answer(
                query=query,
                rewritten_query=rewritten_query,
                context=grounded_context,
                memory=memory,
                retrieved_docs=retrieved_docs,
                intent=intent
            )

            # =========================================
            # STEP 7: BUILD RESPONSE
            # =========================================

            sources = list(set([
                chunk.get("source", "unknown")
                for chunk in retrieved_docs
            ]))

            return {
                "answer": answer,
                "intent": intent,
                "rewritten_query": rewritten_query,
                "reasoning": classification.get("reasoning", ""),
                "execution_plan": {
                    "parallel_retrieval": True,
                    "doc_used": bool(doc_results),
                    "web_used": bool(web_results),
                    "memory_used": bool(memory),
                    "doc_chunks": len(doc_results),
                    "web_chunks": len(web_results),
                    "total_chunks": len(retrieved_docs)
                },
                "sources": sources,
                "retrieved_chunks": retrieved_docs
            }

        except Exception as e:
            print(f"\n❌ AI ENGINE ERROR: {e}\n")
            import traceback
            traceback.print_exc()

            return {
                "answer": (
                    f"An error occurred: {str(e)}\n\n"
                    "Please check the backend logs."
                ),
                "intent": "error",
                "rewritten_query": query,
                "reasoning": str(e),
                "execution_plan": {},
                "sources": [],
                "retrieved_chunks": []
            }