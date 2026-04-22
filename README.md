# A2A Multi-Agent Demo

## Thanh phan

```text
math_agent.py      -> tinh toan deterministic
weather_agent.py   -> thoi tiet
research_agent.py  -> research
gemma_agent.py     -> goi Gemma host qua Gradio
router_agent.py    -> router custom
app.py             -> UI Streamlit de demo
```

## Huong da chot

```text
Colab
  -> Gemma_Gradio_Host.ipynb 
  -> Share URL

Local
  -> gemma_agent.py
  -> router_agent.py
  -> math / weather / research
```

Noi ngan gon:

```text
Gemma host qua Gradio
+ gemma_agent.py
+ router custom
```

Trang thai cuoi cung cua project demo:

```text
CHOT HUONG:
  Khong dung RequirementAgent cho router
  Khong dung HandoffTool cua BeeAI
  Gemma duoc host tren Colab qua Gradio
  Local goi Gemma thong qua gemma_agent.py
  Router custom tu route va goi sub-agent qua A2A helpers
```

## So sanh nhanh 2 huong

### Huong da thu truoc do

```text
User
  -> RouterAgent (RequirementAgent)
  -> ThinkTool
  -> HandoffTool
  -> Sub-agent
  -> ThinkTool
  -> Final answer
```

### Huong da chot hien tai

```text
User
  -> RouterAgent (custom)
  -> GemmaAgent route
  -> call_a2a_agent(...)
  -> MathAgent / WeatherAgent / ResearchAgent
  -> GemmaAgent synthesize
  -> Final answer
```

## Vi sao bo `RequirementAgent`

```text
RequirementAgent
  -> dep pattern framework
  -> can provider on dinh
  -> can host API chuan

Demo hien tai
  -> Colab khong on dinh du
  -> host API chuan ton cong
  -> uu tien "chay duoc"
```

Ket luan:

```text
Khong bo RequirementAgent vi no do
Ma bo vi no khong con la lua chon thuc dung nhat cho demo nay
```

## Tai sao khong thay `HandoffTool`

```text
Truoc day:
RequirementAgent -> HandoffTool -> sub-agent

Hien tai:
router custom -> call_a2a_agent(...) -> sub-agent
```

Y nghia:

- van co handoff ve mat y tuong
- nhung handoff duoc viet thu cong trong code
- khong con dung class `HandoffTool` cua BeeAI nua

## Vi sao chot huong hien tai

```text
Huong truoc
  + dep kien truc
  - Colab cham
  - nhieu lop trung gian
  - kho debug
  - ton cong van hanh

Huong hien tai
  + de chay
  + de debug
  + de fallback
  + hop boi canh demo
  - khong dep bang framework pattern
```

## Vai tro cua Gemma

Gemma co 2 vai tro trung tam:

```text
1. Route
User prompt
  -> GemmaAgent
  -> chon MathAgent / WeatherAgent / ResearchAgent

2. Synthesize
Ket qua tu sub-agent
  -> GemmaAgent
  -> viet lai thanh cau tra loi cuoi
```

Gemma khong chi la chatbot phu. Trong huong da chot, Gemma la:

- bo nao route
- lop tong hop cuoi

## Cach host va dung Gemma trong project nay

### 1. Host Gemma tren Colab

```text
Colab
  -> cai Ollama
  -> bat ollama serve
  -> pull model gemma3:1b
  -> mo Gradio share URL
```

File dung de host:

```text
Gemma_Gradio_Host.ipynb
hoac
Gemma_Gradio_Host.py
```

Ket qua cuoi cung can lay la:

```text
Share URL
vi du:
https://xxxx.gradio.live
```

### 2. Dan Share URL vao env local

```env
GEMMA_GRADIO_URL=https://xxxx.gradio.live
GEMMA_GRADIO_API_NAME=/predict
GEMMA_AGENT_URL=http://127.0.0.1:9104
```

### 3. Local dung Gemma nhu the nao

```text
router_agent.py
  -> khong goi model Gemma truc tiep
  -> goi GemmaAgent qua A2A

gemma_agent.py
  -> dung gradio_client
  -> goi Gradio share URL
  -> Gradio host goi Ollama / Gemma tren Colab
```

### 4. Workflow tong quat cua Gemma

```text
RouterBeeAI
  -> call_a2a_agent(gemma_url, ...)
  -> GemmaAgentExecutor.execute(...)
  -> GemmaAgentCore.answer(...)
  -> gradio_client.Client.predict(...)
  -> Gradio host
  -> Ollama / Gemma
  -> response quay ve router
```

### 5. Gemma tham gia vao he thong o dau

```text
Buoc 1:
  _route_with_gemma(prompt)
  -> Gemma chon math / weather / research

Buoc 2:
  _synthesize_with_gemma(prompt, route, agent_text)
  -> Gemma tong hop cau tra loi cuoi
```

Ket luan:

```text
Gemma khong thay sub-agent chuyen mon
Gemma dung de route va tong hop
```

## Router dang lam gi

```text
prompt
  -> Gemma route
  -> goi sub-agent
  -> lay ket qua
  -> Gemma tong hop
  -> tra loi
```

Fallback hien co:

```text
Neu Gemma route loi
  -> fallback_math
  -> fallback_weather
  -> fallback_research
```

## Luong end-to-end theo cau hoi mau

### Vi du 1: "LLM la gi"

```text
User
  -> RouterBeeAI.answer_sync("LLM la gi")
  -> RouterBeeAI._route_with_gemma(...)
      -> call_a2a_agent(gemma_url, routing_prompt)
      -> GemmaAgentExecutor.execute(...)
      -> GemmaAgentCore.answer(...)
      -> gradio_client.Client.predict(...)
      -> Gemma host tren Colab
      -> Gemma tra ve "research"
  -> RouterBeeAI._call_selected_agent(...)
      -> call_a2a_agent_detailed(research_url, prompt)
      -> ResearchAgentExecutor.execute(...)
      -> ResearchAgentCore.research_async(...)
      -> Gemini / research backend tra ket qua
  -> RouterBeeAI._synthesize_with_gemma(...)
      -> call_a2a_agent(gemma_url, synthesis_prompt)
      -> GemmaAgent tong hop cau tra loi cuoi
  -> final answer
```

### Vi du 2: "4 + 5"

```text
User
  -> RouterBeeAI.answer_sync("4+5")
  -> _route_with_gemma(...)
      -> Gemma tra ve "math"
  -> _call_selected_agent(...)
      -> call_a2a_agent_detailed(math_url, "4+5")
      -> MathAgentExecutor.execute(...)
      -> MathAgentCore.answer(...)
      -> MathNormalizer.normalize(...)
      -> SafeMathEvaluator.evaluate(...)
      -> ket qua "9"
  -> _synthesize_with_gemma(...)
      -> Gemma viet lai ket qua cuoi
  -> final answer
```

## Workflow chi tiet theo class va ham

### 1. Router workflow

```text
Class: RouterBeeAI

__init__()
  -> load_dotenv()
  -> _load_config()

_load_config()
  -> doc MATH_AGENT_URL
  -> doc WEATHER_AGENT_URL
  -> doc RESEARCH_AGENT_URL
  -> doc GEMMA_AGENT_URL
  -> doc ROUTER_AGENT_TIMEOUT

answer(prompt)
  -> asyncio.to_thread(answer_sync, prompt)

answer_sync(prompt)
  -> _route_with_gemma(prompt)
      -> call_a2a_agent(gemma_url, routing_prompt)
      -> _parse_route_result(...)
      -> neu fail thi _fallback_route(...)
  -> _call_selected_agent(route, prompt)
      -> call_a2a_agent_detailed(math|weather|research_url, prompt)
  -> _needs_passthrough(agent_result)?
      -> neu sub-agent can hoi them thi tra thang ve user
  -> _looks_like_agent_error(agent_text)?
      -> neu sub-agent loi thi _friendly_error(...)
  -> _synthesize_with_gemma(prompt, route, agent_text)
      -> call_a2a_agent(gemma_url, synthesis_prompt)
  -> tra (final_answer, trace_text)
```

### 1A. Luong end-to-end cua mot cau hoi research

Vi du user hoi:

```text
LLM la gi
```

Luong se di nhu sau:

```text
User
  -> RouterBeeAI.answer_sync("LLM la gi")
  -> RouterBeeAI._route_with_gemma(...)
      -> call_a2a_agent(gemma_url, routing_prompt)
      -> GemmaAgent phan tich va tra ve {"agent":"research", ...}
  -> RouterBeeAI._call_selected_agent(...)
      -> call_a2a_agent_detailed(research_url, "LLM la gi")
      -> ResearchAgentExecutor.execute(...)
      -> ResearchAgentCore.research_async(...)
      -> Gemini tra noi dung
  -> RouterBeeAI._synthesize_with_gemma(...)
      -> call_a2a_agent(gemma_url, synthesis_prompt)
      -> GemmaAgent viet lai cau tra loi cuoi
  -> RouterBeeAI tra (final_answer, trace)
```

### 1B. Luong end-to-end cua mot cau hoi toan

Vi du user hoi:

```text
Tinh 10 nhan 10 roi cong 100
```

Luong se di nhu sau:

```text
User
  -> RouterBeeAI.answer_sync(...)
  -> RouterBeeAI._route_with_gemma(...)
      -> GemmaAgent chon "math"
  -> RouterBeeAI._call_selected_agent(...)
      -> call_a2a_agent_detailed(math_url, prompt)
      -> MathAgentExecutor.execute(...)
      -> MathAgentCore.answer(...)
      -> MathNormalizer.normalize(...)
      -> SafeMathEvaluator.evaluate(...)
  -> RouterBeeAI._synthesize_with_gemma(...)
      -> GemmaAgent viet lai ket qua cho de doc
  -> final_answer
```

### 2. Router A2A server workflow

```text
Class: RouterAgentExecutor

execute(context, event_queue)
  -> lay prompt tu context.get_user_input()
  -> neu chua co task thi new_task(...)
  -> TaskUpdater(...)
  -> self.router.answer(prompt)
  -> updater.complete(new_agent_text_message(answer))
```

### 3. Gemma agent workflow

```text
Class: GemmaAgentCore

__init__()
  -> doc GEMMA_GRADIO_URL
  -> doc GEMMA_GRADIO_API_NAME
  -> doc GEMMA_AGENT_SYSTEM_PROMPT

_get_client()
  -> Client(base_url)

_build_prompt(prompt)
  -> them system prompt
  -> tao prompt theo format:
     "Nguoi dung: ... / Tra loi:"

answer(prompt)
  -> _get_client()
  -> client.predict(final_prompt, api_name=api_name)
  -> lam sach result
  -> tra text
```

### 3A. Luong rieng cua Gemma

Gemma trong he thong nay khong nam truc tiep ben trong `router_agent.py`.
No di qua mot luong rieng:

```text
Router / local code
  -> call_a2a_agent(gemma_url, ...)
  -> GemmaAgentExecutor.execute(...)
  -> GemmaAgentCore.answer(...)
  -> _get_client()
  -> gradio_client.Client(base_url)
  -> client.predict(final_prompt, api_name="/predict")
  -> Gemma_Gradio_Host tren Colab
  -> Ollama / Gemma model
  -> response quay nguoc lai
```

Co the nhin ngan gon hon:

```text
router
  -> a2a request
  -> gemma_agent.py
  -> gradio_client
  -> Gradio share URL
  -> Gemma host
  -> response
```

### 3B. Gemma duoc goi o dau

Trong `RouterBeeAI`, Gemma duoc goi o 2 ham chinh:

```text
_route_with_gemma(prompt)
  -> Gemma quyet dinh goi math / weather / research

_synthesize_with_gemma(user_prompt, route, agent_text)
  -> Gemma tong hop cau tra loi cuoi
```

Tuc la Gemma khong thay the sub-agent chuyen mon.
Gemma dong vai tro:

- router support
- synthesis support

### 3A. Flow rieng cua Gemma trong he thong

Gemma khong duoc goi truc tiep tu router bang Python SDK cua model.
Gemma di qua 3 lop:

```text
RouterBeeAI / local code
  -> call_a2a_agent(gemma_url, ...)
  -> GemmaAgentExecutor.execute(...)
  -> GemmaAgentCore.answer(...)
  -> gradio_client.Client.predict(...)
  -> Gradio share URL
  -> Ollama / Gemma host tren Colab
  -> ket qua quay nguoc lai
```

Noi cach khac, flow cua Gemma la:

```text
router
  -> a2a request
  -> gemma_agent.py
  -> gradio_client
  -> Gradio host
  -> Gemma model
  -> response
```

### 3B. Gemma duoc goi o nhung diem nao

Trong `router_agent.py`, Gemma duoc goi o 2 diem:

```text
1. _route_with_gemma(prompt)
   -> Gemma chon math / weather / research

2. _synthesize_with_gemma(user_prompt, route, agent_text)
   -> Gemma tong hop cau tra loi cuoi
```

Tuc la Gemma khong thay the sub-agent.
Gemma dung de:

- quyet dinh goi ai
- viet lai cau tra loi cuoi

### 4. Gemma agent A2A workflow

```text
Class: GemmaAgentExecutor

execute(context, event_queue)
  -> lay prompt
  -> new_task(...) neu can
  -> TaskUpdater(...)
  -> self.agent.answer(prompt)
  -> updater.complete(new_agent_text_message(result))
```

### 5. Research agent workflow

```text
Class: ResearchAgentCore

__init__()
  -> doc RESEARCH_MODEL hoac GEMINI_CHAT_MODEL
  -> ChatModel.from_name(model_name)

research_async(query)
  -> SystemMessage(...)
  -> UserMessage(...)
  -> self.model.run(...)
  -> get_text_content()
```

### 6. Research agent A2A workflow

```text
Class: ResearchAgentExecutor

execute(context, event_queue)
  -> lay prompt
  -> new_task(...) neu can
  -> TaskUpdater(...)
  -> self.agent.research_async(prompt)
  -> updater.complete(new_agent_text_message(result))
```

### 7. Math agent workflow

```text
MathAgentCore.answer(prompt)
  -> MathNormalizer.normalize(prompt)
  -> SafeMathEvaluator.evaluate(expression)
  -> tra ket qua dang text
```

### 8. Weather agent workflow

```text
WeatherAgentCore
  -> needs_location(prompt)?
  -> normalize_location(prompt)
  -> _geocode(location)
  -> _forecast(latitude, longitude)
  -> get_weather(location)
```

### 9. Common layer duoc dung de "handoff thu cong"

```text
common.py

call_a2a_agent(...)
  -> goi call_a2a_agent_detailed(...)
  -> tra ve text

call_a2a_agent_detailed(...)
  -> tao payload JSON-RPC
  -> requests.post(url, json=payload)
  -> parse response A2A
  -> tra ve:
     - text
     - texts
     - states
     - raw
```

Day la diem thay the `HandoffTool` trong huong hien tai:

```text
Truoc:
HandoffTool -> framework chuyen task

Hien tai:
call_a2a_agent(...) -> code cua minh tu gui request A2A
```

## Vai tro tung file

```text
Gemma_Gradio_Host.py
  -> host Gemma don gian tren Colab

Gemma_Gradio_Host.ipynb
  -> notebook Colab de cai Ollama, pull model, mo share URL

gemma_agent.py
  -> adapter giua local app va Gemma host

router_agent.py
  -> router custom, khong dung RequirementAgent

research_agent.py
  -> research agent

math_agent.py / weather_agent.py
  -> sub-agent deterministic

app.py
  -> UI Streamlit, co history + route + trace
```

## Env can co

```env
GEMMA_GRADIO_URL=https://your-gradio-share-url-here
GEMMA_GRADIO_API_NAME=/predict
GEMMA_AGENT_URL=http://127.0.0.1:9104
GEMMA_AGENT_PORT=9104

GEMINI_API_KEY=your_gemini_api_key_here
RESEARCH_MODEL=gemini:gemini-2.5-flash

MATH_AGENT_URL=http://127.0.0.1:9101
WEATHER_AGENT_URL=http://127.0.0.1:9102
RESEARCH_AGENT_URL=http://127.0.0.1:9103

AGENT_HOST=127.0.0.1
ROUTER_AGENT_PORT=9100
MATH_AGENT_PORT=9101
WEATHER_AGENT_PORT=9102
RESEARCH_AGENT_PORT=9103
```

## Cach chay demo

### 1. Colab

```text
Chay Gemma_Gradio_Host.ipynb
  -> lay Share URL
```

### 2. Env local

```env
GEMMA_GRADIO_URL=https://xxxx.gradio.live
GEMMA_GRADIO_API_NAME=/predict
```

### 3. Cai dependency

```powershell
python -m pip install -r requirements.txt
```

### 4. Chay local

```powershell
python gemma_agent.py
python math_agent.py
python weather_agent.py
python research_agent.py
python router_agent.py --cli
```

### 5. Chay UI dep hon

```powershell
streamlit run app.py
```

### 6. Cach dung trong demo

```text
User hoi
  -> Streamlit / CLI
  -> RouterAgent
  -> Gemma chon sub-agent
  -> sub-agent xu ly
  -> Gemma tong hop
  -> UI hien:
     - cau tra loi
     - Gemma route
     - Sub-agent duoc goi
```

## Script de trinh bay voi mentor

```text
Ban dau em thu RequirementAgent + API chuan
-> dep kien truc

Nhung khi demo thuc te:
-> Colab cham
-> host API chuan ton cong
-> kho debug

Nen em chot huong:
Gemma host qua Gradio
+ gemma_agent.py
+ router custom

Ly do:
-> de chay hon
-> de debug hon
-> hop muc tieu demo hon
```
