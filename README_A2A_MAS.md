# A2A Protocol, Multi-Agent Systems, and MAS Comparison

## Abstract

Tai lieu nay tom tat co he thong ve:

- `A2A protocol`
- `A2A multi-agent system`
- so sanh giua `A2A` va `MAS`

Muc tieu la giai thich mot cach de doc, de trinh bay, nhung van giu duoc tu duy giong mot bai viet ky thuat hoc thuat. Trong tai lieu nay:

- `A2A` duoc nhin nhu mot **agent-to-agent communication protocol**
- `MAS` duoc nhin nhu mot **khung he thong nhieu tac tu**
- `A2A` khong phai doi lap hoan toan voi `MAS`; trong nhieu truong hop, `A2A` co the duoc xem la mot cach cu the de hien thuc giao tiep ben trong mot `MAS`

## 1. Problem Statement

Khi xay dung he thong tri tue nhan tao phuc hop, mot agent duy nhat thuong gap gioi han:

- khong chuyen sau tren moi bai toan
- kho mo rong
- kho theo doi va kiem thu
- kho tach biet vai tro va trach nhiem

Vi vay, nhieu he thong chuyen sang kieu `multi-agent`, trong do moi agent phu trach mot vai tro rieng. Van de dat ra la:

```text
Neu co nhieu agent, chung giao tiep va phoi hop voi nhau bang cach nao?
```

Day chinh la diem ma `A2A protocol` tro nen quan trong.

## 2. Research Questions

Tai lieu nay tra loi 4 cau hoi chinh:

1. `A2A protocol` la gi?
2. `A2A multi-agent system` hoat dong nhu the nao?
3. `A2A` khac `MAS` o diem nao?
4. Khi nao nen noi ve `A2A`, khi nao nen noi ve `MAS`?

## 3. Core Definitions

### 3.1. Agent

Trong boi canh nay, `agent` la mot thuc the phan mem co kha nang:

- nhan input
- xu ly
- dua ra output
- co the hanh dong doc lap trong mot vai tro cu the

Vi du:

- `MathAgent` de tinh toan
- `WeatherAgent` de lay du lieu thoi tiet
- `ResearchAgent` de giai thich kien thuc
- `RouterAgent` de dieu phoi

### 3.2. Multi-Agent System (MAS)

`MAS` la khai niem he thong. No noi ve mot tap hop nhieu agent cung ton tai trong mot moi truong va phoi hop de giai bai toan lon hon.

Noi ngan gon:

```text
MAS = he thong nhieu agent
```

MAS quan tam nhieu den:

- vai tro cua tung agent
- cach phan chia trach nhiem
- cach phoi hop
- cach ra quyet dinh cua toan he thong

### 3.3. A2A Protocol

`A2A` la viet tat cua `Agent-to-Agent`.

Trong tai lieu nay, `A2A protocol` duoc hieu la giao thuc cho phep:

- mot agent gui request cho agent khac
- agent nhan xu ly request
- agent nhan tra response lai
- ca hai ben co the thong nhat format message, task, status, va output

Noi ngan gon:

```text
A2A = cach agent noi chuyen voi agent khac
```

Neu `MAS` tra loi cau hoi:

```text
He thong nay co nhung agent nao va phoi hop ra sao?
```

thi `A2A` tra loi cau hoi:

```text
Khi mot agent can nhan viec cho agent khac, no gui message theo format nao?
```

## 4. Key Idea

`MAS` va `A2A` khong phai la hai thu thay the hoan toan cho nhau.

Quan he cua chung tot nhat nen hieu nhu sau:

```text
MAS = architecture / system-level view
A2A = communication / protocol-level view
```

Hay noi cach khac:

```text
MAS la "he thong nhieu agent"
A2A la "ngon ngu giao tiep giua cac agent"
```

## 5. A2A Multi-Agent System

Mot `A2A multi-agent system` la he thong nhieu agent ma trong do cac agent giao tiep voi nhau thong qua `A2A protocol`.

### 5.1. Minimal structure

```text
User
  -> RouterAgent
  -> MathAgent / WeatherAgent / ResearchAgent
  -> RouterAgent
  -> User
```

Neu nhin ky hon, he thong thuc su la:

```text
User prompt
  -> RouterAgent
      -> A2A request to MathAgent
      -> A2A request to WeatherAgent
      -> A2A request to ResearchAgent
  -> final answer
```

### 5.2. Main components

Mot he thong `A2A multi-agent` thuong co:

- `orchestrator` hoac `router`
- mot hoac nhieu `specialized agents`
- mot giao thuc thong nhat cho request/response
- co che theo doi task state

### 5.3. Typical lifecycle

```text
1. User gui cau hoi
2. RouterAgent nhan cau hoi
3. RouterAgent quyet dinh can goi agent nao
4. RouterAgent gui A2A request
5. Sub-agent xu ly
6. Sub-agent tra A2A response
7. RouterAgent tong hop
8. RouterAgent tra cau tra loi cuoi cho user
```

## 6. Detailed Workflow Example

### 6.1. Example A: Math question

User hoi:

```text
Tinh 10 nhan 10 roi cong 100
```

Workflow:

```text
User
  -> RouterAgent
      -> phan loai cau hoi la "math"
      -> gui A2A request toi MathAgent
  -> MathAgent
      -> xu ly bieu thuc
      -> tra ket qua
  -> RouterAgent
      -> nhan ket qua
      -> viet lai thanh cau tra loi cuoi
  -> User
```

### 6.2. Example B: Weather question

User hoi:

```text
Thoi tiet Da Nang hom nay
```

Workflow:

```text
User
  -> RouterAgent
      -> phan loai la "weather"
      -> gui A2A request toi WeatherAgent
  -> WeatherAgent
      -> geocode
      -> lay du lieu du bao
      -> tra ve noi dung da tong hop
  -> RouterAgent
      -> tra lai ket qua cho user
```

### 6.3. Example C: Knowledge question

User hoi:

```text
LLM la gi
```

Workflow:

```text
User
  -> RouterAgent
      -> phan loai la "research"
      -> gui A2A request toi ResearchAgent
  -> ResearchAgent
      -> giai thich khai niem
      -> tra response
  -> RouterAgent
      -> tong hop va tra lai user
```

## 7. Protocol View vs System View

De thay ro su khac nhau, co the dat 2 goc nhin canh nhau:

### 7.1. System view

```text
User
  -> RouterAgent
  -> Specialist Agents
  -> Final Answer
```

Day la goc nhin `MAS`.

### 7.2. Protocol view

```text
Agent A
  -> send request
  -> wait status
  -> receive output
```

Day la goc nhin `A2A`.

## 8. A2A vs MAS

## 8.1. Short answer

```text
MAS = what the system is
A2A = how agents communicate inside the system
```

## 8.2. Side-by-side comparison

| Tieu chi | A2A | MAS |
|---|---|---|
| Ban chat | Giao thuc giao tiep | Mo hinh he thong |
| Muc quan tam | Message, request, response, task state | Vai tro, phoi hop, hanh vi tong the |
| Cau hoi chinh | Agent noi voi nhau bang cach nao? | Nhieu agent cung giai bai toan ra sao? |
| Muc truu tuong | Thap hon | Cao hon |
| Don vi phan tich | Tung lan giao tiep | Toan bo kien truc |
| Vi du | JSON-RPC request giua Router va MathAgent | Router + Math + Weather + Research tao thanh mot he thong |

## 8.3. Important conclusion

Khong nen noi:

```text
A2A va MAS la mot
```

Cung khong nen noi:

```text
A2A va MAS la hai huong hoan toan doi lap
```

Cach dung hon la:

```text
MAS la he thong nhieu agent
A2A la mot co che giao tiep ben trong he thong do
```

## 9. Why A2A Matters in Multi-Agent Design

Neu chi co nhieu agent ma khong co giao tiep ro rang, he thong se gap van de:

- kho ket noi agent moi
- kho thay doi agent
- kho theo doi trang thai task
- kho debug

Khi co `A2A protocol`, ta co duoc:

- message format ro rang
- task state ro rang
- cach gui/nhan ket qua thong nhat
- kha nang thay the sub-agent de dang hon

Noi cach khac:

```text
MAS giup chia bai toan
A2A giup cac phan vua chia do noi chuyen duoc voi nhau
```

## 10. Benefits and Limitations

### 10.1. Benefits of MAS

- chia nho bai toan
- moi agent chuyen trach mot viec
- de mo rong he thong
- de kiem thu tung phan

### 10.2. Benefits of A2A

- giao tiep nhat quan
- de debug task handoff
- de theo doi trang thai
- de thay sub-agent ben duoi

### 10.3. Limitations

Neu lam MAS ma khong co protocol ro:

- he thong de roi vao custom logic ro rac

Neu qua phu thuoc protocol ma khong quy hoach kien truc:

- he thong van co the giao tiep duoc
- nhung van khong co thiet ke multi-agent tot

## 11. Mapping to the Demo Project

Trong project nay:

### 11.1. MAS view

```text
System
  -> RouterAgent
  -> MathAgent
  -> WeatherAgent
  -> ResearchAgent
  -> GemmaAgent
```

Day la goc nhin he thong.

### 11.2. A2A view

```text
RouterAgent
  -> call_a2a_agent(...)
  -> call_a2a_agent_detailed(...)
  -> JSON-RPC request
  -> response tu sub-agent
```

Day la goc nhin giao tiep.

### 11.3. Combined interpretation

```text
Project nay la mot MAS
va A2A la co che de cac agent giao tiep trong MAS do
```

## 11A. How the hosted Gemma model is used in this project

Trong project nay, Gemma khong nam truc tiep ben trong local app duoi dang Python model object.
Thay vao do, Gemma duoc su dung theo mo hinh `hosted remote model`.

### 11A.1. Hosting pipeline

```text
Colab runtime
  -> cai Ollama
  -> bat ollama serve
  -> pull model gemma3:1b
  -> mo Gradio host
  -> sinh Share URL
```

Nghia la model Gemma duoc chay tu xa, con local app chi giu vai tro client.

### 11A.2. Usage pipeline from local system

```text
router_agent.py
  -> A2A request toi gemma_agent.py
  -> gemma_agent.py dung gradio_client
  -> gradio_client goi Share URL
  -> Gradio host goi Ollama
  -> Ollama goi Gemma model
  -> ket qua tra nguoc lai local system
```

### 11A.3. Why this matters conceptually

Dieu nay quan trong vi no cho thay:

- model layer co the nam o xa
- agent layer co the nam o local
- A2A layer van giu giao tiep agent-to-agent ro rang

Noi cach khac:

```text
Gemma la hosted model
GemmaAgent la local agent wrapper
RouterAgent giao tiep voi GemmaAgent bang A2A
```

## 11B. Gemma workflow inside the A2A multi-agent system

Gemma trong project nay duoc dung cho 2 nhiem vu:

### 11B.1. Routing

```text
User prompt
  -> RouterAgent
  -> A2A request toi GemmaAgent
  -> GemmaAgent goi hosted Gemma
  -> Gemma quyet dinh:
     math / weather / research
  -> RouterAgent tiep tuc handoff thu cong
```

### 11B.2. Synthesis

```text
Sub-agent result
  -> RouterAgent
  -> A2A request toi GemmaAgent
  -> GemmaAgent goi hosted Gemma
  -> Gemma viet lai cau tra loi cuoi
  -> RouterAgent tra ve user
```

### 11B.3. Interpretation

Tu goc nhin system design:

```text
Gemma khong phai specialist agent
Gemma la coordination-support agent
```

Hay noi ro hon:

- MathAgent giai toan
- WeatherAgent lay thoi tiet
- ResearchAgent giai thich kien thuc
- GemmaAgent ho tro router chon agent va tong hop output

## 11C. End-to-end workflow with hosted Gemma

```text
User
  -> RouterAgent
  -> GemmaAgent (route)
  -> hosted Gemma on Colab
  -> RouterAgent
  -> Specialist Agent
  -> RouterAgent
  -> GemmaAgent (synthesize)
  -> hosted Gemma on Colab
  -> RouterAgent
  -> User
```

Day la diem rat de trinh bay trong bao cao:

```text
Project nay khong chi la MAS
ma la MAS co mot hosted model duoc goi thong qua agent wrapper
```

## 12. End-to-End Demonstration Flow

```text
User question
  -> Streamlit UI or CLI
  -> RouterAgent
      -> route decision
      -> A2A request to sub-agent
  -> Sub-agent
      -> task execution
      -> response
  -> RouterAgent
      -> synthesis
  -> User
```

Neu can dien giai ro hon:

```text
UI layer       : app.py / CLI
orchestrator   : router_agent.py
protocol layer : common.py (A2A request helpers)
worker layer   : math / weather / research / gemma
```

## 13. Scientific-Style Conclusion

Tu goc nhin he thong, `MAS` la mo hinh phan ra va phoi hop nhieu agent de giai mot bai toan phuc hop. Tu goc nhin giao tiep, `A2A protocol` la co che cho phep cac agent do trao doi request, state, va output mot cach thong nhat.

Do do, mot cach ket luan chinh xac la:

```text
MAS la architecture
A2A la protocol
A2A co the la mot phan ben trong MAS
```

Trong cac he thong thuc te, mot `A2A multi-agent system` la su ket hop giua:

- thiet ke he thong nhieu agent
- giao thuc giao tiep ro rang giua agent

Day la ly do `A2A` va `MAS` can duoc hieu nhu hai tang bo sung cho nhau, thay vi xem chung la hai khai niem dong nhat hoac loai tru nhau.

## 14. One-Slide Summary

```text
MAS
  = he thong nhieu agent

A2A
  = giao thuc de cac agent noi chuyen

A2A multi-agent system
  = he thong nhieu agent trong do cac agent phoi hop thong qua A2A
```

## 15. Slide Outline for Presentation

### Slide 1. Problem

Tieu de:

```text
Why do we need multiple agents?
```

Noi dung chinh:

- mot agent duy nhat de bi qua tai
- moi bai toan can chuyen mon khac nhau
- can co co che phan chia nhiem vu

Thong diep chot:

```text
He thong phuc hop thuong can nhieu agent thay vi mot agent duy nhat
```

### Slide 2. Agent

Tieu de:

```text
What is an agent?
```

Noi dung chinh:

```text
Agent
  -> nhan input
  -> xu ly
  -> dua ra output
  -> phu trach mot vai tro cu the
```

Vi du:

```text
MathAgent     -> tinh toan
WeatherAgent  -> thoi tiet
ResearchAgent -> giai thich kien thuc
RouterAgent   -> dieu phoi
```

Thong diep chot:

```text
Agent = don vi xu ly co vai tro rieng trong he thong
```

### Slide 3. MAS

Tieu de:

```text
What is a Multi-Agent System?
```

Noi dung chinh:

```text
MAS
  = mot he thong gom nhieu agent
  = moi agent co vai tro rieng
  = cac agent cung phoi hop de giai bai toan lon hon
```

Thong diep chot:

```text
MAS la goc nhin he thong
```

### Slide 4. A2A

Tieu de:

```text
What is A2A protocol?
```

Noi dung chinh:

```text
A2A
  = Agent-to-Agent protocol
  = cach agent gui request cho nhau
  = cach agent nhan response tu nhau
```

Thong diep chot:

```text
A2A la goc nhin giao tiep
```

### Slide 5. A2A vs MAS

Tieu de:

```text
A2A vs MAS
```

Noi dung chinh:

```text
MAS = he thong nhieu agent
A2A = giao thuc de agent noi chuyen
```

So sanh ngan:

```text
MAS -> architecture
A2A -> protocol
```

Thong diep chot:

```text
A2A va MAS bo sung cho nhau, khong loai tru nhau
```

### Slide 6. A2A Multi-Agent Workflow

Tieu de:

```text
How does an A2A multi-agent workflow operate?
```

Noi dung chinh:

```text
User
  -> RouterAgent
  -> A2A request
  -> Specialist Agent
  -> response
  -> RouterAgent
  -> final answer
```

Thong diep chot:

```text
Router dieu phoi, A2A ket noi, sub-agent xu ly
```

### Slide 7. Example Workflow

Tieu de:

```text
Example: "LLM la gi?"
```

Noi dung chinh:

```text
User
  -> RouterAgent
  -> chon ResearchAgent
  -> ResearchAgent xu ly
  -> RouterAgent tong hop
  -> User
```

Thong diep chot:

```text
Moi agent giai mot phan nho, router gom lai thanh ket qua cuoi
```

### Slide 8. Mapping to This Project

Tieu de:

```text
How is A2A applied in this demo?
```

Noi dung chinh:

```text
RouterAgent
  -> route
  -> call_a2a_agent(...)

MathAgent / WeatherAgent / ResearchAgent
  -> xu ly task rieng

GemmaAgent
  -> route + synthesize
```

Thong diep chot:

```text
Project nay la mot MAS, trong do cac agent giao tiep voi nhau qua A2A
```

### Slide 9. Conclusion

Tieu de:

```text
Conclusion
```

Noi dung chinh:

```text
MAS = he thong nhieu agent
A2A = giao thuc giao tiep
A2A multi-agent system = nhieu agent + giao tiep A2A
```

Thong diep chot:

```text
Neu MAS la bo khung, thi A2A la mach ket noi giua cac agent
```
