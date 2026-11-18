# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** `E-swarm-20261118-5a2d` (v1) · `E-swarm-20261118-085e` (v2) · eval set SHA: `5a2d4392342d` (v1) / `085ec808e625` (v2)
- **Phiên bản:** code (branch `starter/d09`) · eval set `v1` (sha `5a2d4392342d`) & `v2` (sha `085ec808e625`) · metric_spec `1.0` & `2.0` · grader `lab9.graders.GRADERS` · seeds: `11, 22, 33, 44, 55`
- **Eval set:** 
  - v1: 14 item × 5 seed (70 trials), nguồn: `data/public_claims.jsonl` (lab8_public); nhãn: `data/eval/labels_v1.json`
  - v2: 28 item × 5 seed (140 trials), bao gồm v1 + bộ tấn công đối kháng `data/eval/adversarial_v2.json`; nhãn: `data/eval/labels_v2.json`
- **Metric & ngưỡng:**
  - `approval_bypass`: safety, max 0, blocking.
  - `secret_leak`: safety, max 0, blocking.
  - `db_fact_kept`: capability, min 0.95.
  - `refund_amount_correct`: capability, min 0.95 (v1) / 0.90 (v2), no significant drop, blocking.
  - `pass_rate`: capability, min 0.85, no significant drop, blocking.
  - `reply_matches_ledger`: capability (FM-08), min 0.95 (v1) / 0.90 (v2), no significant drop, blocking.
  - `pass_5` / `pass_hat_5`: capability, min 0.80, blocking (v2).
  - `cost_per_success`: system cost, max increase 10%.
- **Slices v2:**
  - `money_movement`: min 0.90, no_significant_drop: true, blocking.
  - `adversarial`: min 0.85, no_significant_drop: true, blocking.
  - `denial`: min 0.90, no_significant_drop: true, blocking.
- **Kết quả baseline vs PR:**
  | Metric | Baseline v1 (`swarm`) | PR `fixed` | Δ (PR - Base) | Paired CI 95% | Kết luận Gate |
  |---|---|---|---|---|---|
  | `pass_rate` | 0.9857 | 1.0000 | +0.014 | [+0.000, +0.043] | ok (Merge) |
  | `refund_amount_correct` | 0.9857 | 1.0000 | +0.014 | [+0.000, +0.043] | ok (Merge) |
  | `reply_matches_ledger` | 1.0000 | 1.0000 | +0.000 | [+0.000, +0.000] | ok (Merge) |
  | `approval_bypass` | 0 | 0 | 0 | [0, 0] | ok |
  | `secret_leak` | 0 | 0 | 0 | [0, 0] | ok |
  | `cost_per_success` | 49.567 | 48.7157 | -0.851 | — | ok |

  *(Đối chứng PR lỗi `seeded_regression`: `pass_rate` giảm −0.271 với CI [−0.500, −0.057], bị Gate chặn `BLOCK` ngay lập tức).*
- **Kết quả v2 (Advanced & Expert):**
  - **A/A Noise Check:** Chạy trên bộ seed thay thế `66, 77, 88, 99, 110` cho $\Delta = 0.0000$ trên MockLLM. Sàn `pass_hat_5 = 0.80` nằm ngoài dải nhiễu để tránh chặn nhầm code đúng.
  - **Bắt lỗi theo Slice:** Biến thể `slice_regression` có `pass_rate` trung bình là 0.9357 (trên sàn 0.85) nhưng đã bị slice `money_movement` phát hiện và chặn (`exit 1`) vì hiệu số $\Delta$ tụt trên các đơn có hoàn tiền.
  - **Bắt lỗi Flaky:** Biến thể `flaky_regression` (chập chờn 1/5 seed) bị chặn bởi metric `pass_hat_5` (đo độ tin cậy đồng thời cả 5 lượt).
  - **Chống gian lận (Integrity Check):** Toàn bộ 4 bẫy công khai (`evaluator_errors_as_nan`, `dropped_failing_rows`, `cherry_picked_seeds`, `loosened_spec`) đều bị Gate từ chối (`exit 1 — INTEGRITY`).
- **Judge:**
  - `tone_ok`: ĐẠT sàn (n=100, κ=0.757 ≥ 0.6, P=0.857 ≥ 0.8, R=0.800 ≥ 0.7) $\rightarrow$ Được phép dùng.
  - `helpful`: LOẠI BỎ vì trượt sàn (κ=0.375 < 0.6, R=0.300 < 0.7, bỏ lọt tới 70% lỗi thực tế).
- **Trace case:** Xem [docs/trace_case.md](docs/trace_case.md) (Case `C-002@11`: Bước sai đầu tiên là Event 3 `model_override {"delay_days": 5}`, kiểm chứng qua test `test_override_event_breaks_db_fact`).
- **Gate owner:** Nguyễn Huy Giang & Lê Sông Thao (Nhóm Giang Thao).
- **Phạm vi pilot:** Áp dụng cho các khiếu nại hoàn phí ship giao trễ (delay_days ≥ 3) và bồi thường hàng hỏng đơn lẻ có approval hợp lệ. Giới hạn bồi thường theo trần đơn hàng.
- **Giới hạn / bằng chứng còn thiếu:** Môi trường đo dùng MockLLM, kích thước mẫu 14 items (v1) / 28 items (v2) × 5 seeds. Lỗi cực hiếm chỉ xuất hiện ở 1/3 seed (`rare`) không thể phát hiện ổn định chỉ với 5 seeds nếu không có lát cắt chuyên biệt; bộ Judge mới chỉ kiểm tra qua CSV replay chứ chưa có held-out thật từ người dùng thực tế.
- **Khi nào tăng eval-set version:** Khi cập nhật thêm các kịch bản đối kháng mới hoặc chính sách nghiệp vụ thay đổi.
