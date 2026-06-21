# Panduan & Dokumentasi Backend: Premium ToDo List API

Dokumentasi ini menjelaskan arsitektur, skema database, sistem autentikasi, serta integrasi AI Agent pada backend aplikasi ToDo List. Backend dibangun menggunakan **FastAPI**, **SQLModel (SQLAlchemy)**, **PostgreSQL (Supabase)**, serta **LangChain (Groq Llama 3.3)**.

---

## 1. Arsitektur Proyek (Struktur Direktori)

Backend diorganisasi dengan pola modular untuk menjaga kerapian kode:

```
backend/
├── app/
│   ├── api/                  # Modul Router HTTP (Endpoints)
│   │   ├── agentic_ai_api.py # Endpoint `/agentic/chat`
│   │   ├── todo_api.py       # Endpoint CRUD `/todos`
│   │   └── user_api.py       # Endpoint Autentikasi & Profil `/users`
│   ├── controllers/          # Logika Bisnis & Mesin AI Agent
│   │   ├── agentic_ai.py     # Engine Agent (LangChain + Groq + Tool)
│   │   └── todos_controller.py
│   ├── core/                 # Konfigurasi Global & Keamanan
│   │   ├── config.py         # Pemuat `.env` (dotenv)
│   │   ├── hashing.py        # Enkripsi Password (Argon2)
│   │   └── security.py       # Proteksi JWT (OAuth2PasswordBearer)
│   ├── crud/                 # Komunikasi Database Level Rendah
│   │   └── todos_crud.py
│   ├── db/                   # Koneksi & Session Database
│   │   └── session.py        # SQLModel Engine & Dependency Generator
│   ├── models/               # Definisi Model Data & Skema Pydantic
│   │   ├── todo.py
│   │   └── user.py
│   └── main.py               # Berkas Entri Utama (FastAPI App & CORS)
├── requirements.txt          # Daftar Pustaka Dependensi Python
└── .env                      # Konfigurasi Environment (Kunci Rahasia & DB)
```

---

## 2. Skema & Model Database

Database menggunakan relasi **One-to-Many** antara tabel `User` (Pengguna) dan `Todo` (Tugas).

### Diagram ERD (Mermaid)

```mermaid
erDiagram
    USER ||--o{ TODO : "memiliki"
    USER {
        uuid id PK
        string name
        string email UK
        string password
    }
    TODO {
        uuid id PK
        string title
        string description
        timestamp deadline
        boolean completed
        boolean is_daily
        boolean is_weekly
        boolean is_monthly
        boolean is_yearly
        uuid user_id FK
    }
```

### Model SQLModel (`app.models`)

- **`User`**: Menyimpan data akun pengguna. Email bersifat unik (`unique=True`) untuk mencegah registrasi ganda.
- **`Todo`**: Menyimpan detail tugas dengan fitur perulangan (Recurrence) menggunakan flag boolean (`is_daily`, `is_weekly`, dll.) serta Kunci Tamu (`user_id`) yang merujuk pada `User.id`.

---

## 3. Sistem Keamanan & Autentikasi

Backend menggunakan keamanan standar industri berbasis **JWT (JSON Web Token)** dengan skema **OAuth2 Password Bearer**:

1. **Hashing Password**: Menggunakan `Argon2` (via pustaka `pwdlib`) untuk mengenkripsi password secara searah (tidak dapat didekripsi) sebelum disimpan di database.
2. **JWT Token**: Setelah login sukses, backend menghasilkan token berisi payload ID Pengguna (`sub`) yang ditandatangani menggunakan `SECRET_KEY` dengan algoritma `HS256` dan berlaku selama 30 menit.
3. **Dependency Protection**: Endpoint yang memerlukan login menggunakan proteksi dependency `Depends(get_current_user)` dari `app.core.security`. Dependency ini:
   - Membaca Header `Authorization: Bearer <TOKEN>`.
   - Melakukan decode dan verifikasi keabsahan JWT Token.
   - Mengambil data user yang aktif dari database untuk dilemparkan ke handler route.

---

## 4. Mesin AI Agent (`Agentic AI`)

AI Agent di backend dirakit menggunakan **LangChain** dengan model **Llama 3.3 (70B) via Groq**:

- **Groq API**: Kecepatan inference super cepat (Llama 3.3-70b-versatile).
- **LLM Tooling (`manage_todo_list`)**: Agent dibekali satu tool serbaguna yang mampu melakukan operasi database penuh (Create, Read, Update, Delete) berdasarkan instruksi user.
- **Context Awareness**: Saat dijalankan, agent dibekali data **Waktu Sekarang (Tanggal & Jam)** dan **User ID Aktif** sehingga agent dapat menerjemahkan kalimat waktu relatif (seperti *"besok pagi"*, *"dua hari lagi"*, atau *"sore ini"*) menjadi tanggal absolut yang valid.
- **Pembersihan Cerdas (Robust Parsing)**: Mengubah input waktu parsial dari agent (seperti `"06:00"`) menjadi objek `datetime` penuh dengan menggabungkannya dengan tanggal hari ini agar tidak memicu error database PostgreSQL.

---

## 5. Referensi API Lengkap (Endpoints)

Semua rute API mengembalikan respons JSON. Rute bertanda 🔒 memerlukan Header `Authorization: Bearer <token_jwt>`.

### A. Endpoint Akun & Autentikasi (`/users`)

#### 1. Registrasi User Baru
- **Method & URL**: `POST /users/register`
- **Request Body**:
  ```json
  {
    "name": "Irfan",
    "email": "irfan@example.com",
    "password": "rahasiasuperaman"
  }
  ```
- **Respons (200 OK)**: Mengembalikan profil pengguna yang terdaftar (tanpa menampilkan password asli).

#### 2. Login User (OAuth2 Standard)
- **Method & URL**: `POST /users/login`
- **Request (Form Data)**:
  - `username` (diisi Email)
  - `password`
- **Respons (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer"
  }
  ```

#### 3. Ambil Profil Aktif 🔒
- **Method & URL**: `GET /users/me`
- **Respons (200 OK)**: Mengembalikan data lengkap objek `User` yang sedang login.

#### 4. Update Profil Pengguna 🔒
- **Method & URL**: `PUT /users/me`
- **Request Body**:
  ```json
  {
    "name": "Irfan Baru",
    "email": "irfan.baru@example.com"
  }
  ```
- **Respons (200 OK)**: Mengembalikan profil terupdate.

#### 5. Ubah Password Pengguna 🔒
- **Method & URL**: `PUT /users/me/password`
- **Request Body**:
  ```json
  {
    "current_password": "rahasiasuperaman",
    "new_password": "passwordbarulebihaman"
  }
  ```
- **Respons (200 OK)**: `{"message": "Password berhasil diperbarui"}`

---

### B. Endpoint ToDo List (`/todos`)

#### 1. Buat Task Baru 🔒
- **Method & URL**: `POST /todos/`
- **Request Body**:
  ```json
  {
    "title": "Beli susu coklat",
    "description": "Beli yang ukuran 1 liter di minimarket",
    "deadline": "2026-05-28T09:00:00",
    "is_daily": false,
    "is_weekly": false,
    "is_monthly": false,
    "is_yearly": false
  }
  ```
- **Respons (200 OK)**: Detail objek `Todo` yang berhasil dibuat beserta UUID barunya.

#### 2. Ambil Semua Task User 🔒
- **Method & URL**: `GET /todos/`
- **Respons (200 OK)**: List array seluruh tugas milik user aktif.

#### 3. Cari Task Berdasarkan Judul/Deskripsi 🔒
- **Method & URL**: `GET /todos/search?q=<kata_kunci>`
- **Respons (200 OK)**: Array berisi tugas-tugas milik user yang mengandung kata kunci pencarian.

#### 4. Edit Detail Task 🔒
- **Method & URL**: `PATCH /todos/{todo_id}`
- **Request Body**: (Kirim field yang ingin diubah saja)
  ```json
  {
    "completed": true
  }
  ```
- **Respons (200 OK)**: Objek `Todo` yang diperbarui.

#### 5. Hapus Task
- **Method & URL**: `DELETE /todos/{todo_id}`
- **Respons (200 OK)**: `{"message": "Todo deleted successfully"}`

---

### C. Endpoint AI Agent (`/agentic`)

#### 1. Berkomunikasi dengan AI Agent 🔒
- **Method & URL**: `POST /agentic/chat`
- **Request Body**:
  ```json
  {
    "message": "Buat task meeting besok jam 10 pagi"
  }
  ```
- **Respons (200 OK)**:
  ```json
  {
    "reply": "Saya telah berhasil membuat tugas **meeting** dengan deadline besok tanggal **28 Mei 2026 pukul 10:00:00**."
  }
  ```

---

## 6. Cara Menjalankan Backend

### 1. Prasyarat (Prerequisites)
Pastikan Anda memiliki **Python 3.10+** dan **PostgreSQL** yang aktif (atau Supabase URL).

### 2. Pengaturan Berkas `.env`
Salin dan lengkapi berkas konfigurasi `.env` di direktori utama proyek:
```ini
# PostgreSQL Connection URL
DATABASE_URL=postgresql://user:password@host:port/database

# JWT Configuration
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Groq API Key (Dibutuhkan untuk AI Agent)
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 3. Instalasi Dependensi
Jalankan instalasi pustaka dari berkas `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Menjalankan Server Dev
Jalankan server ASGI FastAPI menggunakan Uvicorn:
```bash
uvicorn backend.app.main:app --reload
```
Server akan menyala pada **`http://localhost:8000`**.

### 5. Akses Dokumentasi Swagger UI
Buka browser dan arahkan ke alamat berikut untuk menguji API secara langsung secara interaktif:
👉 **`http://localhost:8000/docs`**
