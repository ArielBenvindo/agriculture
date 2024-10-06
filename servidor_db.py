import sqlite3

# Função para criar o banco de dados e a tabela
def init_db():
    conn = sqlite3.connect('risco_seca.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS riscos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            prectotcorr REAL NOT NULL,
            t2m_max REAL NOT NULL,
            qv2m REAL NOT NULL,
            ws10m REAL NOT NULL,
            ps REAL NOT NULL,
            risco TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()  

def salvar_dados(latitude, longitude, start_date, end_date, dados, risco):
    conn = sqlite3.connect('risco_seca.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO riscos (latitude, longitude, start_date, end_date, prectotcorr, t2m_max, qv2m, ws10m, ps, risco)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (latitude, longitude, start_date, end_date,
          dados['PRECTOTCORR'], dados['T2M_MAX'], dados['QV2M'],
          dados['WS10M'], dados['PS'], risco))
    conn.commit()
    conn.close()