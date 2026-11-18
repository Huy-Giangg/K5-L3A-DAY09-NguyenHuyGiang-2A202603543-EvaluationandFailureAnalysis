# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (Case C-002@11 từ seeded_regression)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID `E-seeded_regression-20261118-5a2d` |
| Triệu chứng | `lab8 grader FAIL (status resolved != denied)`; Reply nói hoàn 20.000đ và ledger ghi `refund_vnd=20000`, trong khi nhãn mong đợi là `0` (`denied`). |
| Bước sai đầu tiên | Bước 3: `model_override` `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Bước 1 `handoff` và Bước 2 `investigator` đã tra cứu đúng đơn O-202 từ Database với `delay_days: 2` (không đủ điều kiện bồi thường trễ ≥ 3 ngày). Nhưng tại bước 3, agent đã tin ticket của khách và ghi đè ngày trễ thành 5 ngày. |
| Failure mode | `FM-03` (`ticket_trust — tin ticket hơn DB`) |
| Đối chứng | Trên shape `fixed` (`C-002@11`), không hề có bước `model_override`. Ngay sau bước `investigator`, agent gọi `quote` trả về `amount_vnd: 0` (`no_entitlement`) và từ chối bồi thường đúng chuẩn. |
| Regression test | Grader `DbFactKept` bắt lỗi `model_override`; metric `db_fact_kept` và `pass_rate`. Đã kiểm chứng FAIL trên `seeded_regression` và PASS trên `fixed`. |
| Chưa chắc chắn | Trace chỉ ghi nhận hành vi đầu ra của sự kiện (`model_override`), không can thiệp được vào suy luận bên trong nếu model thực hiện âm thầm không sinh event (cần thêm bẫy `quiet_override`). |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
