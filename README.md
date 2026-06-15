# DataHub Catalog Advisor

**Agent Demo by Clawdata team — GreenNode Claw-a-thon 2026**

---

## Mô tả Agent

### Vấn đề

Trong team data của công ty fintech/ví điện tử, mỗi khái niệm nghiệp vụ (chuyển tiền IBFT, thanh toán QR, nạp ví, KYC...) tồn tại đồng thời ở nhiều bảng có tên gần giống nhau trên DataHub: bản raw log ở data lake (HDFS) và bản đã ETL ở data warehouse (Redshift). Khi search "transfer_ibft" trên DataHub ra 5 bảng — analyst và engineer không biết chọn bảng nào đúng mục đích, dẫn đến mất 15–30 phút hỏi thủ công mỗi lần, hoặc nghiêm trọng hơn là đọc sai bảng (dùng raw log để báo cáo KPI, dùng bảng mart để debug sự cố).

### Người dùng mục tiêu

Data Analysts, Data Engineers và Business Analysts trong team data fintech — những người thường xuyên cần tìm đúng bảng dữ liệu để phân tích metrics, build dashboard, hoặc điều tra sự cố giao dịch.

### Cách agent giải quyết

User mô tả nhu cầu bằng tiếng Việt hoặc tiếng Anh → **DataHub Catalog Advisor** (deploy trên GreenNode AgentBase) tìm kiếm catalog 28 dataset của e-wallet, phân tích intent (metric/dashboard → Redshift warehouse; debug/raw log → HDFS lake), rồi trả về URN chính xác + lý do chọn bảng + bảng thay thế ở layer kia. Lịch sử hội thoại được lưu theo session để xử lý follow-up thông minh. Model cascade Gemma → MiniMax → Qwen đảm bảo phản hồi nhanh và luôn có fallback.

### Giá trị mang lại

Mỗi ngày team data thực hiện hàng chục lần tra cứu bảng. Agent giúp **rút ngắn từ 15–30 phút xuống dưới 30 giây** mỗi lần, loại bỏ bước hỏi thủ công qua Slack/email, và giảm thiểu lỗi sai do dùng nhầm layer. Tích lũy trong 1 tháng, team tiết kiệm được hàng chục giờ làm việc và giảm đáng kể rủi ro báo cáo sai số liệu kinh doanh.

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
