====================================================
HƯỚNG DẪN SỬ DỤNG HỆ THỐNG QUẢN LÝ QUÁN CAFE QUA TELEGRAM
====================================================

I. TỔNG QUAN HỆ THỐNG
----------------------------------------------------
Hệ thống quản lý quán cafe qua Telegram là một ứng dụng cho phép:
- Khách hàng: Xem menu, đặt món, đặt bàn và liên hệ với quán
- Quản lý (Admin): Quản lý sản phẩm, đơn hàng, bàn và xem báo cáo

Ứng dụng được xây dựng trên nền tảng Python với API của Telegram và cơ sở dữ liệu SQLite.

II. CẤU TRÚC DỰ ÁN
----------------------------------------------------
1. Các file chính:
   - app.py: File khởi động bot, thiết lập kết nối và quản lý vòng đời ứng dụng
   - bot.py: Chứa logic xử lý các tương tác của bot
   - database.py: Định nghĩa cấu trúc cơ sở dữ liệu và cung cấp các phương thức truy xuất
   - utils.py: Chứa các hàm tiện ích hỗ trợ

2. Cơ sở dữ liệu:
   - Products: Danh sách sản phẩm (món ăn/đồ uống)
   - Orders: Đơn hàng của khách
   - OrderItems: Chi tiết từng món trong đơn hàng
   - Tables: Thông tin các bàn trong quán

III. QUY TRÌNH HOẠT ĐỘNG
----------------------------------------------------
1. KHỞI ĐỘNG HỆ THỐNG
-------------------
1.1. Cài đặt các thư viện cần thiết:
    pip install python-telegram-bot python-dotenv sqlalchemy

1.2. Cấu hình bot:
    - Tạo file .env và thêm TELEGRAM_TOKEN
    - Hoặc sử dụng token trực tiếp trong code

1.3. Khởi động bot:
    python src/app.py

2. PHÂN QUYỀN NGƯỜI DÙNG
------------------------
2.1. Admin:
    - ID được cấu hình trong biến ADMIN_ID
    - Có quyền quản lý sản phẩm, đơn hàng, bàn và xem báo cáo

2.2. Khách hàng:
    - Tất cả người dùng khác
    - Có quyền xem menu, đặt món và đặt bàn

3. QUY TRÌNH HOẠT ĐỘNG CHO KHÁCH HÀNG
------------------------------------
3.1. Xem Menu:
    - Nhấp vào "📋 Xem Menu"
    - Chọn danh mục sản phẩm
    - Xem chi tiết sản phẩm và giá

3.2. Đặt món:
    - Nhấp vào "🛒 Đặt món"
    - Chọn danh mục sản phẩm
    - Chọn sản phẩm và số lượng
    - Xem giỏ hàng
    - Xác nhận đơn hàng

3.3. Đặt bàn:
    - Nhấp vào "🪑 Đặt bàn"
    - Xem danh sách bàn còn trống
    - Chọn bàn và thời gian
    - Xác nhận đặt bàn

3.4. Liên hệ:
    - Nhấp vào "📱 Liên hệ"
    - Xem thông tin liên hệ của quán

4. QUY TRÌNH HOẠT ĐỘNG CHO ADMIN
-------------------------------
4.1. Quản lý Sản phẩm:
    a) Thêm sản phẩm mới:
       - Nhấp vào "📝 Quản lý Sản phẩm"
       - Chọn "➕ Thêm sản phẩm mới"
       - Nhập thông tin theo định dạng:
         Tên sản phẩm | Giá | Danh mục | Mô tả
       - Xác nhận thêm sản phẩm

    b) Chỉnh sửa sản phẩm:
       - Nhấp vào "📋 Xem & Sửa sản phẩm"
       - Chọn sản phẩm cần sửa
       - Nhập thông tin mới theo định dạng
       - Xác nhận cập nhật

4.2. Quản lý Đơn hàng:
    - Xem danh sách đơn hàng theo trạng thái
    - Cập nhật trạng thái đơn hàng
    - Xem chi tiết đơn hàng

4.3. Quản lý Bàn:
    - Xem trạng thái các bàn
    - Thêm bàn mới
    - Chỉnh sửa thông tin bàn
    - Xem lịch đặt bàn

4.4. Báo cáo:
    - Xem doanh thu theo ngày/tuần/tháng
    - Xem sản phẩm bán chạy
    - Thống kê đơn hàng

5. XỬ LÝ LỖI VÀ KHẮC PHỤC
-------------------------
5.1. Lỗi kết nối:
    - Kiểm tra kết nối internet
    - Kiểm tra token bot
    - Khởi động lại bot

5.2. Lỗi dữ liệu:
    - Kiểm tra định dạng nhập liệu
    - Xem log lỗi
    - Khôi phục dữ liệu từ backup

5.3. Lỗi quyền truy cập:
    - Kiểm tra ID admin
    - Xác nhận quyền người dùng
    - Cập nhật cấu hình quyền

6. BẢO MẬT
----------
6.1. Quyền truy cập:
    - Chỉ admin mới có quyền quản lý
    - Mỗi người dùng có ID riêng
    - Kiểm tra quyền trước mỗi thao tác

6.2. Dữ liệu:
    - Lưu trữ an toàn trong SQLite
    - Sao lưu định kỳ
    - Mã hóa thông tin nhạy cảm

7. BẢO TRÌ
----------
7.1. Định kỳ:
    - Kiểm tra log lỗi
    - Cập nhật dữ liệu
    - Sao lưu database

7.2. Khi có sự cố:
    - Khởi động lại bot
    - Kiểm tra kết nối
    - Khôi phục dữ liệu

8. PHÁT TRIỂN TƯƠNG LAI
----------------------
8.1. Tính năng mới:
    - Thanh toán online
    - Đánh giá sản phẩm
    - Chương trình khuyến mãi
    - Tích hợp với các nền tảng khác

8.2. Cải thiện:
    - Giao diện người dùng
    - Hiệu suất hệ thống
    - Bảo mật
    - Báo cáo chi tiết

----------------------------------------------------
Được phát triển bởi: PHOMMASENG EKALAT
Dự án: Chuyên đề 2
Năm: 2025
---------------------------------------------------- 