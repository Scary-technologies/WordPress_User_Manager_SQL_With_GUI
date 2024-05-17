import mysql.connector
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog

# تابع برای اتصال به بانک اطلاعاتی
def get_db_connection(host, username, password, database):
    try:
        connection = mysql.connector.connect(
            host=host,
            user=username,
            password=password,
            database=database
        )
        return connection
    except mysql.connector.Error as err:
        messagebox.showerror("خطا", f"اتصال به بانک اطلاعاتی ممکن نیست: {err}")
        return None

# تابع برای نمایش لیست کاربران و دسترسی‌ها
def show_users(connection, tree):
    if connection is None:
        messagebox.showerror("خطا", "اتصال به بانک اطلاعاتی برقرار نشده است.")
        return

    cursor = connection.cursor()
    query = """
    SELECT u.ID, u.user_login, u.user_pass, u.user_nicename, u.user_email, u.user_registered, m.meta_value
    FROM wp_users u
    LEFT JOIN wp_usermeta m ON u.ID = m.user_id AND m.meta_key = 'wp_capabilities'
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in tree.get_children():
            tree.delete(row)
        for row in rows:
            role = row[6]
            if role:
                role = role.split('"')[1]  # استخراج نقش از داده‌های سریال شده
            else:
                role = 'N/A'
            tree.insert("", "end", values=(row[0], row[1], row[2], row[3], row[4], row[5], role))
    except mysql.connector.Error as err:
        messagebox.showerror("خطا", f"خطا در بازیابی کاربران: {err}")
    finally:
        cursor.close()

# تابع برای ویرایش نقش کاربران
def edit_user_role(connection, user_id, column, new_value, tree):
    if connection is None:
        messagebox.showerror("خطا", "اتصال به بانک اطلاعاتی برقرار نشده است.")
        return

    cursor = connection.cursor()
    try:
        if column == 'نقش':
            new_capabilities = f'a:1:{{s:{len(new_value)}:"{new_value}";b:1;}}'
            cursor.execute("UPDATE wp_usermeta SET meta_value = %s WHERE user_id = %s AND meta_key = 'wp_capabilities'", (new_capabilities, user_id))
        else:
            cursor.execute(f"UPDATE wp_users SET {column} = %s WHERE ID = %s", (new_value, user_id))
        connection.commit()
        show_users(connection, tree)  # به‌روزرسانی لیست کاربران
    except mysql.connector.Error as err:
        messagebox.showerror("خطا", f"خطا در به‌روزرسانی نقش کاربر: {err}")
    finally:
        cursor.close()

# تابع برای ساخت اکانت جدید
def create_new_user(connection, tree, role_combobox):
    if connection is None:
        messagebox.showerror("خطا", "اتصال به بانک اطلاعاتی برقرار نشده است.")
        return

    # درخواست ورودی برای نام کاربری، نام مستعار، ایمیل و رمز عبور
    username = simpledialog.askstring("ورودی", "نام کاربری جدید را وارد کنید:")
    nicename = simpledialog.askstring("ورودی", "نام مستعار جدید را وارد کنید:")
    email = simpledialog.askstring("ورودی", "ایمیل جدید را وارد کنید:")
    password = simpledialog.askstring("ورودی", "رمز عبور جدید را وارد کنید:", show='*')
    role = role_combobox.get()

    # بررسی اینکه هیچ فیلدی خالی نباشد
    if not username or not nicename or not email or not password:
        messagebox.showwarning("هشدار", "تمامی فیلدها برای ساخت کاربر جدید الزامی هستند.")
        return

    cursor = connection.cursor()
    try:
        # ساخت کوئری برای درج کاربر جدید
        query = "INSERT INTO wp_users (user_login, user_pass, user_nicename, user_email, user_registered) VALUES (%s, MD5(%s), %s, %s, NOW())"
        cursor.execute(query, (username, password, nicename, email))
        user_id = cursor.lastrowid
        # درج نقش کاربر جدید
        new_capabilities = f'a:1:{{s:{len(role)}:"{role}";b:1;}}'
        cursor.execute("INSERT INTO wp_usermeta (user_id, meta_key, meta_value) VALUES (%s, 'wp_capabilities', %s)", (user_id, new_capabilities))
        connection.commit()
        messagebox.showinfo("موفقیت", "کاربر جدید با موفقیت ایجاد شد")
        show_users(connection, tree)  # به‌روزرسانی لیست کاربران
    except mysql.connector.Error as err:
        messagebox.showerror("خطا", f"خطا در ساخت کاربر جدید: {err}")
    finally:
        cursor.close()

# تابع برای ساخت و نمایش رابط کاربری
def create_gui():
    def fetch_users():
        conn = get_db_connection(host_entry.get(), username_entry.get(), password_entry.get(), database_entry.get())
        show_users(conn, user_tree)

    def on_cell_double_click(event):
        item = user_tree.selection()[0]
        column = user_tree.identify_column(event.x)
        column_index = int(column[1:]) - 1
        column_name = columns[column_index]
        user_id = user_tree.item(item)['values'][0]

        new_value = simpledialog.askstring("ورودی", f"مقدار جدید برای {column_name} را وارد کنید:")
        if new_value is not None:
            conn = get_db_connection(host_entry.get(), username_entry.get(), password_entry.get(), database_entry.get())
            edit_user_role(conn, user_id, column_name, new_value, user_tree)

    root = tk.Tk()
    root.title("مدیریت کاربران")

    # ایجاد فریمی برای ورودی‌های اطلاعات بانک اطلاعاتی
    db_frame = tk.Frame(root)
    db_frame.grid(row=0, column=0, padx=5, pady=5)

    # برچسب و ورودی برای میزبان
    host_label = tk.Label(db_frame, text="میزبان:")
    host_label.pack(side=tk.LEFT, padx=5)
    host_entry = tk.Entry(db_frame)
    host_entry.pack(side=tk.LEFT, padx=5)

    # برچسب و ورودی برای نام کاربری
    username_label = tk.Label(db_frame, text="نام کاربری:")
    username_label.pack(side=tk.LEFT, padx=5)
    username_entry = tk.Entry(db_frame)
    username_entry.pack(side=tk.LEFT, padx=5)

    # برچسب و ورودی برای رمز عبور
    password_label = tk.Label(db_frame, text="رمز عبور:")
    password_label.pack(side=tk.LEFT, padx=5)
    password_entry = tk.Entry(db_frame, show="*")
    password_entry.pack(side=tk.LEFT, padx=5)

    # برچسب و ورودی برای نام بانک اطلاعاتی
    database_label = tk.Label(db_frame, text="نام بانک اطلاعاتی:")
    database_label.pack(side=tk.LEFT, padx=5)
    database_entry = tk.Entry(db_frame)
    database_entry.pack(side=tk.LEFT, padx=5)

    # دکمه برای بازیابی کاربران
    fetch_button = tk.Button(db_frame, text="بازیابی کاربران", command=fetch_users)
    fetch_button.pack(side=tk.LEFT, padx=5)

    # ستون‌های جدول کاربران
    columns = ("ID", "نام کاربری", "رمز عبور", "نام مستعار", "ایمیل", "تاریخ ثبت‌نام", "نقش")
    user_tree = ttk.Treeview(root, columns=columns, show="headings")
    for col in columns:
        user_tree.heading(col, text=col)
    user_tree.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

    # نوار پیمایش برای جدول
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=user_tree.yview)
    user_tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.grid(row=1, column=2, sticky='ns')

    # اتصال رویداد دو بار کلیک به تابع
    user_tree.bind("<Double-1>", on_cell_double_click)

    # برچسب و کومبوباکس برای نقش پیش‌فرض کاربران جدید
    role_label = tk.Label(root, text="نقش پیش‌فرض برای کاربران جدید:")
    role_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
    role_combobox = ttk.Combobox(root, values=["subscriber", "contributor", "author", "editor", "administrator"])
    role_combobox.grid(row=2, column=1, padx=5, pady=5)
    role_combobox.set("subscriber")

    # دکمه برای افزودن کاربر جدید
    add_user_button = tk.Button(root, text="افزودن کاربر", command=lambda: create_new_user(get_db_connection(host_entry.get(), username_entry.get(), password_entry.get(), database_entry.get()), user_tree, role_combobox))
    add_user_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
