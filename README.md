# Password Safe — Trình quản lý mật khẩu đa người dùng

**Password Safe** là ứng dụng desktop viết bằng **Python/Tkinter**, hỗ trợ nhiều người dùng độc lập trên cùng một máy. Mỗi người có tài khoản đăng nhập và kho mật khẩu riêng; thông tin trong kho được mã hóa trước khi lưu vào SQLite.

> Phiên bản tài liệu này mô tả **`PasswordSafe(3).py`**. Không nhầm với các phiên bản cũ sử dụng một kho chung và tệp `PasswordSafe.db`.

## Tính năng

- **Tạo tài khoản / đăng nhập** bằng tên người dùng và mật khẩu chính (mật khẩu đăng ký tối thiểu 12 ký tự).
- **Kho riêng cho từng người dùng**: mỗi bản ghi gắn với `owner`, truy vấn đọc/sửa/xóa được giới hạn theo chủ sở hữu.
- **Lưu tài khoản dịch vụ** với tên dịch vụ, tên đăng nhập, mật khẩu và website; thêm mới, chọn để sửa, xóa có xác nhận, tìm kiếm theo dịch vụ / username / website.
- **Kiểm tra độ mạnh mật khẩu** theo chiều dài, nhóm ký tự, các mẫu quá phổ biến, ký tự lặp và chuỗi dễ đoán; hiển thị điểm 0–100 và gợi ý. Đây là **quy tắc heuristic**, không phải tra cứu rò rỉ trên Internet.
- **Tạo mật khẩu ngẫu nhiên** độ dài 12–64 ký tự, tùy chọn ký tự đặc biệt; sử dụng module `secrets`.
- **Sao chép mật khẩu**, có cơ chế cố gắng xóa clipboard sau 20 giây nếu nội dung vẫn đúng mật khẩu vừa sao chép.
- **Đăng xuất/khóa**: bỏ khóa đang giữ trong bộ nhớ ứng dụng và quay về màn hình đăng nhập.

## Công nghệ

| Công nghệ | Vai trò |
|---|---|
| Python 3 | Ngôn ngữ chính |
| Tkinter + ttk | Giao diện đồ họa desktop |
| SQLite (`sqlite3`) | Lưu người dùng và các bản ghi đã mã hóa |
| `cryptography.fernet` | Mã hóa/giải mã có xác thực |
| `hashlib.pbkdf2_hmac` (SHA-256, 600.000 vòng) | Dẫn xuất khóa từ mật khẩu chính + salt 16 byte |
| `secrets`, `string`, `re` | Tạo và chấm điểm mật khẩu |
| `json`, `base64`, `pathlib`, `ctypes`, `sys` | Phụ trợ dữ liệu, khóa, đường dẫn, hỗ trợ DPI Windows |

**Thư viện bên ngoài duy nhất cần cài:** `cryptography`.

## Cài đặt và chạy

Yêu cầu **Python 3.10+** (khuyến nghị), có Tkinter và hệ điều hành hỗ trợ GUI.

```bash
python -m pip install -r requirements.txt
python "PasswordSafe(3).py"
```

Nếu đã đổi tên tệp thành `password_safe.py`, dùng:

```bash
python password_safe.py
```

Trên một số bản Linux cần cài gói `python3-tk` của hệ điều hành. Khi chạy lần đầu, ứng dụng sẽ tự tạo tệp **`PasswordSafe_Multi.db`** trong thư mục chứa script.

## Hướng dẫn nhanh

1. Mở ứng dụng → **Tạo tài khoản mới** → nhập tên người dùng và mật khẩu chính từ **12 ký tự** → đăng ký.
2. Trong tab **Kho mật khẩu**, điền dịch vụ, tài khoản, mật khẩu, website (nếu có) → **Lưu**.
3. Chọn một hàng để điền thông tin vào form bên phải; sửa và lưu lại, hoặc bấm **Xóa** (có xác nhận).
4. Nhập từ khóa vào **Tìm kiếm** để lọc danh sách.
5. Chọn **Tạo & kiểm tra** để kiểm tra độ mạnh hoặc tạo mật khẩu mới. **Dùng để lưu** sẽ chuyển mật khẩu vừa tạo sang form kho.
6. Bấm **Đăng xuất** để khóa kho hiện tại. Đăng nhập người dùng khác sẽ thấy kho riêng của người đó.

## Cơ chế lưu trữ và bảo mật

Cơ sở dữ liệu có hai bảng:

- `users(id, name, salt, verifier)` — mỗi tên người dùng là duy nhất; `salt` ngẫu nhiên 16 byte; `verifier` là đoạn kiểm chứng đã mã hóa.
- `vault(id, owner, secret)` — `owner` tham chiếu `users(id)`; `secret` chứa toàn bộ bản ghi JSON đã mã hóa bằng Fernet.

Mỗi người dùng có khóa Fernet được dẫn xuất riêng từ mật khẩu chính và salt bằng PBKDF2-HMAC-SHA256 với **600.000 vòng**. Dữ liệu trong `vault.secret` không phải mật khẩu rõ.

**Giới hạn hiện tại:** không có đồng bộ/sao lưu/khôi phục tự động; không có khôi phục mật khẩu chính nếu quên; chưa có giới hạn số lần đăng nhập sai hoặc khóa tự động theo thời gian; không kiểm tra mật khẩu rò rỉ thực tế. Không dùng sản phẩm học tập này như một hệ thống bảo mật đã qua kiểm toán.

## Cấu trúc dự án

```text
PasswordSafe/
├── PasswordSafe(3).py       # Mã nguồn ứng dụng
├── README.md                # Hướng dẫn dự án
├── requirements.txt         # Dependency cần pip install
├── .gitignore               # Không đưa DB/môi trường lên GitHub
└── PasswordSafe_Multi.db    # Tự tạo tại máy chạy (KHÔNG commit)
```

## Minh chứng và báo cáo

Có thể đính kèm báo cáo Word/PDF và video MP4 demo không thuyết minh, nhạc nền không lời. Video minh họa bằng giao diện chương trình thực tế, dữ liệu trong video là tài khoản giả lập.

## Lưu ý quan trọng

- **Không đăng tải `PasswordSafe_Multi.db` chứa thông tin thật**, các bản sao lưu `.db*`, khóa bí mật hoặc mật khẩu lên GitHub.
- **Giữ bí mật mật khẩu chính**. Mất mật khẩu chính đồng nghĩa không giải mã được dữ liệu đã lưu qua cơ chế hiện tại.
- Nếu muốn sao lưu, cần sao chép an toàn tệp DB trong khi ứng dụng đã đóng và bảo vệ bản sao lưu bằng biện pháp phù hợp.

## Giấy phép

Chưa cung cấp tệp LICENSE; mặc định mọi quyền được bảo lưu cho tác giả theo luật bản quyền áp dụng.
