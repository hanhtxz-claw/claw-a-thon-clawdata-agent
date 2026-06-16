# DataHub Catalog Advisor

**Agent Demo by Clawdata team — GreenNode Claw-a-thon 2026**

---

## Mô tả Agent

### Vấn đề

Trong một công ty fintech/e-wallet, mỗi khái niệm nghiệp vụ (chuyển tiền IBFT, thanh toán QR, nạp ví, KYC...) thường tồn tại song song ở **hai layer dữ liệu với mục đích hoàn toàn khác nhau**:

- **Data Lake (HDFS)** — raw event log, immutable, schema-on-read. Giữ trọn vẹn mọi giao dịch ở mọi trạng thái (success, failed, retry, pending), kèm payload đầy đủ. Là **source of truth** cho debug sự cố, reconcile đối soát, audit/compliance, và feature engineering cho ML.
- **Data Warehouse (Redshift)** — bảng đã ETL, modeled, schema-on-write, đã dedup và apply business rules (chỉ giữ final state, loại test/internal users, gắn dimension chuẩn). Là **single source of truth cho BI** — báo cáo KPI, dashboard điều hành, phân tích cohort.

Hai layer này phục vụ hai bài toán đối lập về độ trễ, độ chi tiết và độ tin cậy của số liệu — nhưng trên DataHub chúng nằm cạnh nhau với tên gọi gần giống. Khi search "transfer_ibft" ra 4 bảng, người dùng không có cách nhanh để biết bảng nào dành cho mình. Hậu quả thực tế:

1. **Lãng phí thời gian** — 15–30 phút mỗi lần đi hỏi DE trên MS Teams/email, blocker cho phân tích.
2. **Sai số liệu báo cáo** — dùng raw lake cho KPI ra số khác với báo cáo chính thức (vì chưa dedup, chưa loại failed/test transactions), khiến leadership ra quyết định trên dữ liệu không nhất quán.
3. **Debug sai gốc rễ** — dùng warehouse mart để truy vết sự cố sẽ bỏ sót retry/failed events và raw payload, dẫn tới kết luận sai về nguyên nhân.

### Người dùng mục tiêu

Product Owner (PO), Business Intelligence (BI), Data Analysts (DA) và Data Engineers (DE) của các phòng ban trong công ty — những người thường xuyên cần tìm đúng bảng dữ liệu để phân tích metrics, build dashboard, hoặc điều tra sự cố giao dịch.

### Cách agent giải quyết

User mô tả nhu cầu bằng tiếng Việt hoặc tiếng Anh → **DataHub Catalog Advisor** (deploy trên GreenNode AgentBase) tìm kiếm catalog 41 dataset của e-wallet, phân tích intent (metric/dashboard → Redshift warehouse; debug/raw log → HDFS lake), rồi trả về URN chính xác + lý do chọn bảng + bảng thay thế ở layer kia. Lịch sử hội thoại được lưu theo session để xử lý follow-up thông minh.

### Giá trị mang lại

Giá trị thật của agent không nằm ở "tìm bảng nhanh hơn", mà ở chỗ **ghép đúng use case với đúng layer**: cần báo cáo KPI → đẩy về warehouse (số liệu đã chuẩn hóa, nhất quán toàn công ty); cần debug/đối soát → đẩy về lake (raw, đủ chi tiết, giữ cả failed/retry để truy vết gốc rễ).

Nhờ vậy, mỗi truy vấn dữ liệu đều khai thác đúng thế mạnh của tầng dữ liệu mình đang đứng — dashboard không bị lệch số, điều tra sự cố không bỏ sót event. Thời gian tra cứu giảm từ 15–30 phút xuống dưới 30 giây, và quan trọng hơn: tổ chức tránh được loại lỗi đắt nhất — *báo cáo sai vì đọc nhầm layer* — vốn rất khó phát hiện và đi thẳng vào quyết định của leadership.

---

## Public Endpoint

```
https://endpoint-b502a02b-73b3-440b-8379-e9376d3584ff.agentbase-runtime.aiplatform.vngcloud.vn
```

## Tech Stack

- **Runtime:** GreenNode AgentBase (Docker, port 8080)
- **Backend:** FastAPI + RAG-lite catalog search (difflib)
- **LLM:** Gemma 4 31B → MiniMax M2.5 → Qwen 3.5 27B (cascade)
- **Catalog:** 28 dummy DataHub datasets (HDFS + Redshift), e-wallet domain
- **UI:** Embedded chat (HTML/JS, dark mode)
