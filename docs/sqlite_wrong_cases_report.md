# Báo cáo phân tích lỗi phổ biến – `SQLite_wrong_cases.json`

## 1) Phạm vi & dữ liệu
- Nguồn dữ liệu: `D:\nlq\SQLite_wrong_cases.json`
- Loại bài toán: báo cáo lỗi cho pipeline agent sinh SQL từ câu hỏi tự nhiên (NLQ -> SQL)
- Mục tiêu: chỉ ra **lỗi sai phổ biến**, **nhóm câu hỏi hay sai**, và **khía cạnh cần ưu tiên cải thiện**

## 2) Tóm tắt nhanh (Executive Summary)
- Tổng số câu đã đánh giá: **200**
- Tổng số câu sai: **85**
- Tỷ lệ sai: **42.5%**

### 2.1 Phân bố câu sai theo độ khó
| Difficulty | Số lỗi |
|---|---:|
| simple | 21 |
| moderate | 43 |
| challenging | 21 |

> Nhóm **moderate** đang là điểm nghẽn lớn nhất.

### 2.2 Phân bố câu sai theo database
| Database | Số lỗi |
|---|---:|
| thrombosis_prediction | 25 |
| european_football_2 | 22 |
| debit_card_specializing | 17 |
| student_club | 16 |
| formula_1 | 5 |

## 3) Nhóm câu hỏi thường mắc lỗi
(đếm theo tín hiệu từ text câu hỏi – một câu có thể thuộc nhiều nhóm)

| Nhóm câu hỏi | Số câu sai có tín hiệu |
|---|---:|
| Join-heavy (which/list/among/from/who...) | 48 |
| Aggregation (count/sum/avg/percentage/ratio/difference) | 40 |
| Temporal (year/month/date/between/oldest/youngest...) | 23 |
| Ranking (highest/lowest/top/most/least/best) | 17 |

## 4) Taxonomy lỗi phổ biến (heuristic, multi-label)
> Lưu ý: các nhãn bên dưới là **multi-label**; tổng có thể vượt 85.

| Nhóm lỗi | Số case |
|---|---:|
| Output shape mismatch (sai cấu trúc kết quả trả về) | 23 |
| Aggregation/grain mismatch | 21 |
| Join path mismatch | 20 |
| Temporal function/logic risk | 17 |
| Filter mismatch (thiếu/thừa điều kiện) | 13 |
| Grouping mismatch | 10 |
| Ranking/order mismatch | 9 |
| Null-handling difference (NULLIF/logic chia) | 7 |

## 5) Dấu hiệu sai phổ biến trong SQL dự đoán
- Dùng `COUNT(DISTINCT ...)` quá nhiều: **25** case (ground truth chỉ có 4 case có DISTINCT tương ứng).
- Dùng hàm theo kiểu MySQL trong tập lỗi SQLite:
  - `YEAR(`: 12
  - `LEFT(`: 5
  - `CONCAT(`: 4
  - `TIMESTAMPDIFF(`: 2
- `NULLIF(` xuất hiện 7 case trong predicted SQL (ground truth hầu như không dùng cùng pattern).

**Hàm ý:** mô hình có xu hướng “an toàn hóa” hoặc “tổng quát hóa” theo thói quen SQL engine khác, gây lệch EX khi so với benchmark.

## 6) Ví dụ lỗi tiêu biểu

### 6.1 Output shape mismatch
- **sql_idx=10, qid=1486**  
  Câu hỏi cần “nếu đúng thì hơn bao nhiêu”, nhưng SQL dự đoán trả về **2 cột** (`boolean` + `count`) trong khi ground truth trả về **1 giá trị chênh lệch**.

### 6.2 Aggregation/grain mismatch
- **sql_idx=12, qid=1493**  
  Predicted dùng `COUNT(DISTINCT CustomerID)` cho tử và mẫu; ground truth đếm theo bản ghi tháng (`COUNT(CustomerID)`), dẫn tới sai grain của bài toán.

### 6.3 Join path mismatch
- **sql_idx=15, qid=1501**  
  Predicted chỉ lọc theo `transactions_1k.Date` và join `gasstations`; ground truth còn cần join `yearmonth` để ràng buộc tháng `201306` theo logic benchmark.

### 6.4 Temporal logic mismatch
- **sql_idx=13, qid=1498**  
  Predicted dùng `MAX(Consumption)` theo bản ghi; ground truth yêu cầu **tổng theo tháng**, sau đó lấy tháng có tổng cao nhất (`GROUP BY month` + `ORDER BY SUM DESC LIMIT 1`).

### 6.5 Filter mismatch
- **sql_idx=38, qid=1340**  
  Predicted thêm filter `WHERE b.category = 'Student_Club'` không có trong ground truth, làm thay đổi tập dữ liệu cần tính.

### 6.6 Sai nặng kiểu fallback/hallucination
- **sql_idx=23, qid=1524**  
  Predicted: `SELECT NULL AS nationality FROM customers c WHERE FALSE;`  
  Đây là lỗi “collapse” truy vấn (không còn bám câu hỏi), ảnh hưởng nghiêm trọng chất lượng pipeline.

## 7) Nhận định nguyên nhân gốc (theo pipeline stage)

### 7.1 Schema Linking
- Có rủi ro chọn chưa đúng “join path tối thiểu đúng ngữ nghĩa” cho các câu multi-table.
- Khi schema linking không chốt tốt key nối + grain, SQL generation dễ sai dù cú pháp hợp lệ.

### 7.2 SQL Generation
- Prompt hiện tại chưa ép chặt các ràng buộc:
  - output shape phải đúng intent,
  - grain/aggregation chuẩn,
  - quy tắc top-k/ranking,
  - xử lý thời gian theo data format benchmark.
- Mô hình có xu hướng sinh SQL “hợp lý chung” nhưng lệch bài toán benchmark cụ thể.

### 7.3 Reflection
- Reflection có thể phát hiện một phần sai logic, nhưng các lỗi semantic tinh vi (grain, scope filter, output shape) vẫn lọt.
- Cần đầu vào reflection giàu cấu trúc hơn (issue type rõ ràng) để vòng retry sửa đúng trọng tâm.

### 7.4 Prompt contract / Dialect alignment
- File lỗi là **SQLite wrong cases**, trong khi cấu hình/prompt runtime có thể thiên về MySQL style ở nhiều đường chạy.
- Lệch dialect làm tăng lỗi hàm/thời gian/chuẩn biểu thức.

## 8) Các khía cạnh cần tập trung để cải thiện (ưu tiên)

### Ưu tiên 1 – Logic correctness trước syntax correctness
1. Ép “output contract” theo câu hỏi: số cột, ý nghĩa cột, kiểu trả về.
2. Ép checklist aggregation/grain: mẫu số của percentage/ratio, có/không DISTINCT, group-by level.
3. Ràng buộc ranking semantics: highest/lowest/top phải có ORDER BY + LIMIT chuẩn.

### Ưu tiên 2 – Join & filter precision
1. Chuẩn hóa join path theo key thực sự cần thiết (tránh thiếu/thừa join).
2. Chống thêm filter ngoài yêu cầu (filter drift), đặc biệt với câu tính chênh lệch/tỷ lệ.

### Ưu tiên 3 – Temporal & dialect consistency
1. Chuẩn hóa pattern xử lý thời gian theo benchmark dataset.
2. Giảm phụ thuộc vào hàm engine-specific khi không chắc chắn ngữ cảnh dialect.

### Ưu tiên 4 – Chất lượng vòng retry
1. Retry cần bám lỗi semantic cụ thể (không chỉ lỗi execute).
2. Tránh pattern “fallback SQL vô nghĩa” (ví dụ trả NULL/FALSE).

## 9) Kết luận
- Lỗi hiện tại không chủ yếu ở cú pháp SQL, mà nằm ở **semantic alignment** giữa câu hỏi và truy vấn sinh ra: output shape, grain, join path, filter, temporal logic.
- Chỉ cần giảm mạnh 3 nhóm lỗi lớn nhất (**shape + aggregation/grain + join path**) là có thể cải thiện đáng kể hiệu năng toàn pipeline.

