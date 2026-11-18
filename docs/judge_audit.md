# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | ĐẠT (0.757 ≥ 0.6, 0.857 ≥ 0.8, 0.8 ≥ 0.7) | dùng |
| helpful | 100 | 0.375 | 1.000 | 0.300 | KHÔNG ĐẠT (κ=0.375 < 0.6, R=0.3 < 0.7) | loại |

## ≥5 case audit thủ công (Từ judge_tone_public và judge_helpful_public)
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú & Hành động sửa Rubric |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người đúng | Reply: "Em đã hoàn tiền cho anh rồi nha, anh check giúp em." -> Xưng hô suồng sã thiếu chuyên nghiệp. **Sửa rubric:** Bổ sung quy tắc cấm xưng hô thân mật quá mức ("anh/em/nha") trong kênh CSKH doanh nghiệp. |
| 2 | H-017 | PASS | FAIL | Người đúng | Reply: "Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha." -> Dùng từ "bạn ơi", "rồi nha" không đạt chuẩn formal. **Sửa rubric:** Đưa ví dụ cụ thể về đại từ xưng hô chuẩn (chỉ dùng "quý khách/anh/chị"). |
| 3 | H-029 | PASS | FAIL | Người đúng | Reply: "Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm." -> Giọng điệu cộc lốc, xua đuổi khách hàng ("không cần nhắn thêm"). **Sửa rubric:** Cấm các cụm từ mang tính tiêu cực hoặc từ chối hỗ trợ tiếp. |
| 4 | H-042 | FAIL | PASS | Người đúng | Reply: "Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." -> Judge quá khắt khe khi phạt vì không có lời xin lỗi, dù câu trả lời ngắn gọn, lịch sự và rõ ràng. **Sửa rubric:** Làm rõ nếu đơn thành công thì không bắt buộc phải có câu xin lỗi. |
| 5 | HL-016 | PASS | FAIL | Người đúng | Reply: "Dạ, LogiX thành thật xin lỗi anh/chị vì sự bất tiện này..." -> Judge bị lừa bởi lời xin lỗi dài dòng trôi chảy, trong khi câu trả lời hoàn toàn không cung cấp giải pháp cho vấn đề khách hỏi. **Sửa rubric:** Đánh trượt các câu trả lời sáo rỗng không giải quyết vấn đề (actionable info). |

## Kết luận
- **Tiêu chí bị loại:** `judge_helpful`.
  - **Lý do (ma trận nhầm lẫn):** `{'tp': 9, 'fp': 0, 'fn': 21, 'tn': 70}`. Độ phủ lỗi (Recall) chỉ đạt **0.30** (bỏ lọt tới 21 trên tổng số 30 ca lỗi, tức lọt 70% lỗi thực tế). Cohen's Kappa chỉ đạt **0.375** (dưới ngưỡng sàn 0.6). Judge bị "ảo giác lịch sự" (fluent bias), dễ dàng cho PASS các câu xin lỗi sáo rỗng không giải quyết được vấn đề của khách hàng. Do đó, **tuyệt đối không được dùng judge_helpful làm CI Gate** vì sẽ tạo ra cảm giác an toàn giả.
- **Tiêu chí được giữ lại:** `judge_tone`.
  - Đạt toàn bộ các sàn tiêu chuẩn ($\kappa = 0.757 \ge 0.6$, $P = 0.857 \ge 0.8$, $R = 0.8 \ge 0.7$).
- **Rủi ro còn lại:** Judge chỉ được kiểm thử trên dữ liệu replay đã công khai (`judge_tone_public.csv`). Để đảm bảo an toàn trong môi trường production, cần thu thập nhãn của chuyên gia người thật trên các ca hội thoại mới (held-out set) định kỳ để tái hiệu chuẩn (re-calibration).
