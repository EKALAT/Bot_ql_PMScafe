# Bot quản lý PMScafe

Bot Telegram để quản lý quán cà phê PMScafe, bao gồm:
- Quản lý sản phẩm (thêm, sửa, xóa)
- Quản lý đơn hàng
- Quản lý bàn
- Báo cáo doanh thu

## Cài đặt

1. Cài đặt các thư viện cần thiết:
```
pip install python-telegram-bot sqlalchemy python-dotenv
```

2. Tạo file `.env` và cấu hình:
```
# Thông tin kết nối Telegram Bot
TELEGRAM_TOKEN=your_telegram_token_here

# ID của Admin (Quản lý)
ADMIN_ID=6079753756

# ID của Thu ngân (phân cách bằng dấu phẩy nếu có nhiều người)
CASHIER_IDS=7628252452

# ID của Nhân viên phục vụ (phân cách bằng dấu phẩy nếu có nhiều người)
SERVER_IDS=
```

3. Chạy bot:
```
python src/app.py
```

## Hệ thống phân quyền

Bot PMScafe có 3 vai trò với các quyền khác nhau:

### 1. Admin (Quản lý)
ID cấu hình trong biến `ADMIN_ID` trong file `.env`

**Quyền hạn:**
- Xem menu
- Quản lý sản phẩm (thêm, sửa, xóa)
- Quản lý đơn hàng
- Quản lý bàn
- Xem báo cáo doanh thu
- Đặt món, đặt bàn (nếu cần)

### 2. Thu ngân (Cashier)
ID cấu hình trong biến `CASHIER_IDS` trong file `.env`

**Quyền hạn:**
- Xem menu
- Quản lý đơn hàng
- Quản lý bàn
- Xem báo cáo bán hàng

### 3. Nhân viên phục vụ (Server)
ID cấu hình trong biến `SERVER_IDS` trong file `.env`

**Quyền hạn:**
- Xem menu
- Đặt món
- Đặt bàn
- Xem thông tin liên hệ

## Quản lý nhân viên

Để thêm hoặc xóa nhân viên, bạn cần chỉnh sửa file `.env`:

### Thêm nhân viên mới

1. Lấy ID Telegram của nhân viên (yêu cầu nhân viên sử dụng bot @userinfobot để lấy ID)
2. Mở file `.env`
3. Thêm ID của nhân viên vào biến tương ứng với vai trò của họ:
   
   **Ví dụ:**
   - Thêm Thu ngân mới có ID 987654321:
     ```
     CASHIER_IDS=7628252452,987654321
     ```
   - Thêm Nhân viên phục vụ mới có ID 123456789:
     ```
     SERVER_IDS=123456789
     ```

4. Lưu file và khởi động lại bot

### Xóa nhân viên

1. Mở file `.env`
2. Tìm và xóa ID của nhân viên cần xóa khỏi biến tương ứng
3. Lưu file và khởi động lại bot

**Lưu ý:** Mỗi nhân viên chỉ nên thuộc về một vai trò duy nhất để tránh xung đột quyền hạn.

### Kiểm tra vai trò của người dùng

Khi bot chạy, nó sẽ ghi lại thông tin về ID người dùng và vai trò của họ trong log. Bạn có thể kiểm tra log để xem vai trò của người dùng đang cố gắng sử dụng bot.

## Cách sử dụng

1. Mở Telegram và tìm kiếm bot theo tên
2. Gửi lệnh `/start` để bắt đầu
3. Bot sẽ kiểm tra ID của bạn và hiển thị menu tương ứng với vai trò của bạn
4. Nếu không có quyền truy cập, bot sẽ từ chối và kết thúc cuộc hội thoại

---

## Dành cho nhà phát triển

### Cấu trúc thư mục

- `src/`
  - `app.py`: File chính để khởi động bot
  - `bot.py`: Logic xử lý các lệnh và callbacks
  - `database.py`: Định nghĩa mô hình dữ liệu
  - `setup_products.py`: Script để thiết lập dữ liệu sản phẩm mẫu
  - `utils.py`: Các hàm tiện ích

### Mở rộng chức năng

Để thêm tính năng mới, bạn có thể:
1. Thêm handlers mới vào file `bot.py`
2. Thêm các trạng thái hội thoại mới và cập nhật ConversationHandler trong `app.py`
3. Nếu cần, thêm mô hình dữ liệu mới vào `database.py` 