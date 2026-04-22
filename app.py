from __future__ import annotations

import asyncio
import re

import streamlit as st

from common import maybe_load_env
from router_agent import RouterBeeAI


def extract_trace_details(trace: str) -> dict[str, str]:
    patterns = {
        "route": r"^ROUTE:\s*(.+)$",
        "called": r"^CALLED:\s*(.+)$",
        "fallback": r"^ROUTER_FALLBACK:\s*(.+)$",
        "task_status": r"^TASK_STATUS:\s*(.+)$",
        "synthesized_by": r"^SYNTHESIZED_BY:\s*(.+)$",
        "agent_error": r"^AGENT_ERROR:\s*(.+)$",
    }
    details: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, trace, flags=re.MULTILINE)
        if match:
            details[key] = match.group(1).strip()
    return details


def run_router(prompt: str) -> tuple[str, str]:
    return asyncio.run(RouterBeeAI().answer(prompt))


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_page() -> None:
    st.set_page_config(
        page_title="Router Chat Demo",
        page_icon="AI",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top, rgba(255,123,84,0.18), transparent 22%),
                    linear-gradient(180deg, #0f1117 0%, #121722 100%);
            }
            .block-container {
                max-width: 860px;
                padding-top: 1.2rem;
                padding-bottom: 2rem;
            }
            .topbar {
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 22px;
                padding: 1rem 1.1rem;
                background: rgba(255,255,255,0.03);
                margin-bottom: 1rem;
                box-shadow: 0 16px 40px rgba(0,0,0,0.20);
            }
            .title {
                font-size: 1.7rem;
                font-weight: 700;
                color: #ffffff;
                margin-bottom: 0.25rem;
            }
            .subtitle {
                color: #aab4c7;
                font-size: 0.96rem;
                line-height: 1.5;
            }
            .agent-strip {
                display: flex;
                gap: 0.65rem;
                flex-wrap: wrap;
                margin-top: 0.8rem;
            }
            .agent-pill {
                border: 1px solid rgba(255,255,255,0.10);
                background: rgba(255,255,255,0.04);
                color: #f8f8fb;
                border-radius: 999px;
                padding: 0.42rem 0.75rem;
                font-size: 0.88rem;
            }
            .answer-box {
                border: 1px solid rgba(255,255,255,0.08);
                background: linear-gradient(135deg, rgba(255,132,92,0.16), rgba(255,255,255,0.04));
                border-radius: 18px;
                padding: 0.95rem 1rem;
                margin-top: 0.35rem;
            }
            .answer-label {
                color: #ffbd9d;
                font-size: 0.76rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 0.45rem;
            }
            .answer-text {
                color: #fff8f3;
                line-height: 1.65;
                font-size: 1rem;
            }
            .hint {
                color: #96a2b6;
                font-size: 0.92rem;
                margin-top: 0.6rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="topbar">
            <div class="title">Router Chat Demo</div>
            <div class="subtitle">
                Giao dien demo dang chatbot. Moi cau hoi se duoc Router xu ly, Gemma chon sub-agent phu hop,
                sau do tra lai cau tra loi cuoi.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### Demo Control")
        if st.button("Xoa lich su", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.markdown("---")
        st.markdown("### Agent map")
        st.markdown(
            """
            - `math` -> MathAgent
            - `weather` -> WeatherAgent
            - `research` -> ResearchAgent
            - Gemma -> route + synthesize
            """
        )


def render_messages() -> None:
    for item in st.session_state.messages:
        with st.chat_message("user"):
            st.markdown(item["prompt"])

        with st.chat_message("assistant"):
            st.markdown(
                f"""
                <div class="answer-box">
                    <div class="answer-label">Cau tra loi</div>
                    <div class="answer-text">{item["answer"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            route = item["details"].get("route", "unknown")
            called = item["details"].get("called", "unknown")
            fallback = item["details"].get("fallback")
            task_status = item["details"].get("task_status", "unknown")
            synthesized_by = item["details"].get("synthesized_by")
            agent_error = item["details"].get("agent_error")

            pills = [
                f'<div class="agent-pill">Task: {task_status}</div>',
                f'<div class="agent-pill">Gemma route: {route}</div>',
                f'<div class="agent-pill">Sub-agent: {called}</div>',
            ]
            if synthesized_by:
                pills.append(f'<div class="agent-pill">Synthesize: {synthesized_by}</div>')
            if fallback:
                pills.append(f'<div class="agent-pill">Fallback: {fallback}</div>')
            if agent_error:
                pills.append(f'<div class="agent-pill">Error: {agent_error}</div>')

            st.markdown(
                f'<div class="agent-strip">{"".join(pills)}</div>',
                unsafe_allow_html=True,
            )


def main() -> None:
    maybe_load_env()
    init_state()
    render_page()
    render_sidebar()

    st.markdown(
        """
        <div class="hint">
            Ban co the chat nhu binh thuong. UI se chi hien agent nao da duoc goi, khong hien trace dai.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_messages()

    prompt = st.chat_input("Nhap cau hoi...")
    if prompt:
        with st.spinner("Router dang xu ly..."):
            answer, trace = run_router(prompt)

        details = extract_trace_details(trace)
        st.session_state.messages.append(
            {
                "prompt": prompt,
                "answer": answer,
                "details": details,
            }
        )
        st.rerun()


if __name__ == "__main__":
    main()
