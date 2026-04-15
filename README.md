# A2A Multi-Agent Demo

Bộ demo giờ có 4 agent, nhưng `router_agent.py` đã được nâng cấp theo kiểu **Lesson 10**:

1. `math_agent.py` - agent toán an toàn, deterministic.
2. `weather_agent.py` - agent thời tiết, nếu thiếu địa điểm sẽ trả về trạng thái `input_required`.
3. `research_agent.py` - agent research dùng Gemini + Google Search tool.
4. `router_agent.py` - **LLM orchestrator**: phân tích câu hỏi, lập plan gọi sub-agent, nhận kết quả, rồi **tổng hợp lại** thành câu trả lời cuối.

## Flow mới của router

```text
User question
  -> Router LLM phân tích ý định
  -> tạo plan các step cần gọi
  -> handoff sang math / weather / research qua A2A
  -> gom kết quả các agent con
  -> Router LLM tổng hợp lại
  -> final answer
```

Điểm khác so với bản cũ:
- Không còn trả raw output thẳng từ downstream agent.
- Có bước **analysis / plan / synthesize** giống tinh thần Lesson 10.
- Có thể bật `show_trace` để xem router đã chạy qua các bước nào.

## Cài đặt

```bash
pip install -r requirements.txt
```

Bạn sẽ cần các package cốt lõi hiện có của project và thêm nhóm phụ thuộc cho Gemini nếu trước đó chưa có.

## Chuẩn bị biến môi trường

Copy `.env.example` thành `.env` rồi sửa nếu cần:

```bash
copy .env.example .env
```

Các biến quan trọng:
- `GEMINI_API_KEY` - bắt buộc cho `research_agent.py`, và cũng được router dùng để plan + synthesize.
- `RESEARCH_MODEL` - tùy chọn, mặc định `gemini-2.5-flash`.
- `ROUTER_MODEL` - tùy chọn, nếu không có sẽ dùng `RESEARCH_MODEL` hoặc `gemini-2.5-flash`.
- `AGENT_HOST` - mặc định `127.0.0.1`.
- `ROUTER_AGENT_PORT`, `MATH_AGENT_PORT`, `WEATHER_AGENT_PORT`, `RESEARCH_AGENT_PORT`.
- `LOCAL_ROUTER_ENABLED=true` nếu muốn `demo_api.py` gọi router trực tiếp trong process thay vì gọi qua A2A.

## Test local bằng CLI

### 1) Math
```bash
python math_agent.py --cli
python math_agent.py --expr "2 ** 5 + 1"
```

### 2) Weather
```bash
python weather_agent.py --cli
python weather_agent.py --expr "Hà Nội"
```

### 3) Research
```bash
python research_agent.py --cli
python research_agent.py --expr "Agent2Agent protocol"
```

### 4) Router (mới)
```bash
python router_agent.py --cli
python router_agent.py --expr "thời tiết Đà Nẵng"
python router_agent.py --expr "Hà Nội hôm nay mưa không và giải thích nhanh về áp thấp nhiệt đới" --show-trace
```

## Chạy A2A server cho từng agent

Mở 4 terminal riêng:

```bash
python math_agent.py
python weather_agent.py
python research_agent.py
python router_agent.py
```

Port mặc định:
- Router: `9100`
- Math: `9101`
- Weather: `9102`
- Research: `9103`

## Demo nhanh với router

Sau khi 4 server chạy:

```bash
python router_agent.py --expr "12 + 7" --show-trace
python router_agent.py --expr "thời tiết Hà Nội" --show-trace
python router_agent.py --expr "research về Open-Meteo API" --show-trace
python router_agent.py --expr "Đà Nẵng hôm nay bao nhiêu độ và giải thích ngắn về El Nino" --show-trace
```

## Demo API

Chạy API:

```bash
uvicorn demo_api:app --reload
```

Gọi thử:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hà Nội hôm nay thế nào và giải thích nhanh vì sao nồm", "show_trace": true}'
```

## Agent card

Sau khi chạy server, bạn có thể kiểm tra agent card bằng:

```bash
curl http://127.0.0.1:9101/.well-known/agent-card.json
curl http://127.0.0.1:9102/.well-known/agent-card.json
curl http://127.0.0.1:9103/.well-known/agent-card.json
curl http://127.0.0.1:9100/.well-known/agent-card.json
```

## Mentor talking points

Bạn có thể mô tả router mới như sau:
- Router là **LLM orchestrator**, không còn là rule-based `if/else` đơn thuần.
- Router có 3 pha: **analyze -> handoff -> synthesize**.
- Các sub-agent vẫn độc lập và có `AgentCard` riêng.
- `weather_agent` vẫn giữ behavior `input_required` nếu thiếu location.
- Router có trace để giải thích nó đã chọn agent nào, vì sao, và agent nào trả lời phần nào.
