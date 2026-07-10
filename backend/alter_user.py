import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('d:\\WEB DEVELOPMENT\\ToDoList\\backend\\.env')
db_url = os.getenv('DATABASE_URL')
if db_url and db_url.startswith('postgres'):
    try:
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text('ALTER TABLE "user" ADD COLUMN whatsapp_number VARCHAR UNIQUE;'))
            conn.execute(text('CREATE INDEX ix_user_whatsapp_number ON "user" (whatsapp_number);'))
        print('Kolom whatsapp_number berhasil ditambahkan!')
    except Exception as e:
        print('Error:', e)
